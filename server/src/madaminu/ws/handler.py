import logging
from datetime import UTC, datetime

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.models import ConnectionStatus, Game, GameStatus, Phase, Player, Vote
from madaminu.ws.messages import PlayerConnectedData, PlayerDisconnectedData, WSMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, dict[str, WebSocket]] = {}

    async def connect(self, room_code: str, player_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_code not in self._connections:
            self._connections[room_code] = {}
        self._connections[room_code][player_id] = websocket

    def disconnect(self, room_code: str, player_id: str):
        if room_code in self._connections:
            self._connections[room_code].pop(player_id, None)
            if not self._connections[room_code]:
                del self._connections[room_code]

    async def send_to_player(self, room_code: str, player_id: str, message: WSMessage):
        conns = self._connections.get(room_code, {})
        ws = conns.get(player_id)
        if ws:
            await ws.send_json(message.model_dump())

    async def broadcast(self, room_code: str, message: WSMessage, exclude_player_id: str | None = None):
        conns = self._connections.get(room_code, {})
        for pid, ws in conns.items():
            if pid != exclude_player_id:
                try:
                    await ws.send_json(message.model_dump())
                except Exception:
                    logger.warning("Failed to send to player %s", pid)

    def get_connection_count(self, room_code: str) -> int:
        return len(self._connections.get(room_code, {}))


manager = ConnectionManager()


async def authenticate_player(db: AsyncSession, room_code: str, token: str) -> Player | None:
    result = await db.execute(
        select(Player)
        .join(Game, Player.game_id == Game.id)
        .where(Game.room_code == room_code, Player.session_token == token)
    )
    return result.scalar_one_or_none()


async def _get_current_phase_dict(db: AsyncSession, current_phase_id: str) -> dict | None:
    result = await db.execute(select(Phase).where(Phase.id == current_phase_id))
    phase = result.scalar_one_or_none()
    if phase is None:
        return None

    remaining = 0
    if phase.started_at:
        started = phase.started_at if phase.started_at.tzinfo else phase.started_at.replace(tzinfo=UTC)
        elapsed = (datetime.now(UTC) - started).total_seconds()
        remaining = max(0, phase.duration_sec - int(elapsed))

    return {
        "phase_id": phase.id,
        "phase_type": phase.phase_type,
        "phase_order": phase.phase_order,
        "duration_sec": phase.duration_sec,
        "remaining_sec": remaining,
        "investigation_locations": phase.investigation_locations,
    }


async def get_game_state_for_player(db: AsyncSession, room_code: str, player_id: str) -> dict:
    result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.room_code == room_code))
    game = result.scalar_one_or_none()
    if game is None:
        return {}

    players_public = [
        {
            "id": p.id,
            "display_name": p.display_name,
            "character_name": p.character_name,
            "character_personality": p.character_personality,
            "character_background": p.character_background,
            "is_host": p.is_host,
            "is_ai": p.is_ai,
            "connection_status": p.connection_status,
        }
        for p in game.players
    ]

    state = {
        "room_code": game.room_code,
        "status": game.status,
        "host_player_id": game.host_player_id,
        "players": players_public,
        "scenario_setting": game.scenario_skeleton.get("setting", {}) if game.scenario_skeleton else None,
        "victim": game.scenario_skeleton.get("victim", {}) if game.scenario_skeleton else None,
    }

    current_player = next((p for p in game.players if p.id == player_id), None)
    if current_player:
        state["my_secret_info"] = current_player.secret_info
        state["my_objective"] = current_player.objective
        state["my_role"] = current_player.role

    if game.current_phase_id:
        phase_info = await _get_current_phase_dict(db, game.current_phase_id)
        if phase_info:
            state["current_phase"] = phase_info

    state["current_speaker_id"] = None

    return state


async def handle_websocket(websocket: WebSocket, room_code: str, db: AsyncSession):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    player = await authenticate_player(db, room_code, token)
    if player is None:
        await websocket.close(code=4001, reason="Invalid token")
        return

    player_id = player.id
    display_name = player.display_name

    await manager.connect(room_code, player_id, websocket)

    player.connection_status = ConnectionStatus.online
    await db.commit()

    await manager.broadcast(
        room_code,
        WSMessage(
            type="player.connected",
            data=PlayerConnectedData(player_id=player_id, display_name=display_name).model_dump(),
        ),
        exclude_player_id=player_id,
    )

    game_state = await get_game_state_for_player(db, room_code, player_id)
    await manager.send_to_player(
        room_code,
        player_id,
        WSMessage(type="game.state", data=game_state),
    )

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            logger.info("WS message from %s: %s", player_id, msg_type)

            if msg_type in ("phase.advance", "phase.extend"):
                await _handle_host_command(db, room_code, player_id, msg_type, websocket)
            elif msg_type == "speech.request":
                await _handle_speech_request(room_code, player_id, websocket)
            elif msg_type == "speech.release":
                await _handle_speech_release(room_code, player_id, data, websocket)
            elif msg_type == "investigate":
                await _handle_investigate(db, room_code, player_id, data, websocket)
            elif msg_type == "vote.submit":
                await _handle_vote(db, room_code, player_id, data, websocket)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(room_code, player_id)

        player_result = await db.execute(select(Player).where(Player.id == player_id))
        player_obj = player_result.scalar_one_or_none()
        if player_obj:
            player_obj.connection_status = ConnectionStatus.offline
            await db.commit()

        await manager.broadcast(
            room_code,
            WSMessage(
                type="player.disconnected",
                data=PlayerDisconnectedData(player_id=player_id, display_name=display_name).model_dump(),
            ),
        )


def _get_speech_manager(websocket: WebSocket):
    return getattr(websocket.app.state, "speech_manager", None)


async def _handle_speech_request(room_code: str, player_id: str, websocket: WebSocket):
    sm = _get_speech_manager(websocket)
    if sm is None:
        return

    granted = await sm.request_speech(room_code, player_id)
    if granted:
        await manager.send_to_player(
            room_code,
            player_id,
            WSMessage(type="speech.granted", data={"player_id": player_id}),
        )
        await sm.broadcast_speech_granted(room_code, player_id)
    else:
        current = sm.get_current_speaker(room_code)
        await manager.send_to_player(
            room_code,
            player_id,
            WSMessage(type="speech.denied", data={"current_speaker_id": current}),
        )


async def _handle_speech_release(room_code: str, player_id: str, data: dict, websocket: WebSocket):
    sm = _get_speech_manager(websocket)
    if sm is None:
        return

    transcript = data.get("data", {}).get("transcript", "")
    released = await sm.release_speech(room_code, player_id, transcript)
    if released:
        await sm.broadcast_speech_released(room_code, player_id)


async def _handle_host_command(db: AsyncSession, room_code: str, player_id: str, msg_type: str, websocket: WebSocket):
    result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.room_code == room_code))
    game = result.scalar_one_or_none()
    if game is None:
        return

    player = next((p for p in game.players if p.id == player_id), None)
    if player is None or not player.is_host:
        await websocket.send_json(
            WSMessage(type="error", data={"message": "Only the host can control phases"}).model_dump()
        )
        return

    if game.status not in (GameStatus.playing, GameStatus.voting):
        await websocket.send_json(WSMessage(type="error", data={"message": "Game is not in progress"}).model_dump())
        return

    pm = getattr(websocket.app.state, "phase_manager", None)
    if pm is None:
        return

    if msg_type == "phase.advance":
        await pm.advance_phase(game.id, room_code)
    elif msg_type == "phase.extend":
        await pm.extend_phase(game.id, room_code)


async def _handle_investigate(db: AsyncSession, room_code: str, player_id: str, data: dict, websocket: WebSocket):
    from madaminu.services.scenario_engine import investigate_location

    location_id = data.get("data", {}).get("location_id", "")
    if not location_id:
        await websocket.send_json(WSMessage(type="error", data={"message": "Missing location_id"}).model_dump())
        return

    result = await db.execute(select(Game).where(Game.room_code == room_code))
    game = result.scalar_one_or_none()
    if game is None or game.status != GameStatus.playing:
        return

    try:
        evidence, usage = await investigate_location(db, game.id, player_id, location_id)
    except Exception:
        logger.exception("Investigation failed for player %s", player_id)
        await websocket.send_json(WSMessage(type="error", data={"message": "Investigation failed"}).model_dump())
        return

    if evidence is None:
        await websocket.send_json(
            WSMessage(type="investigate.denied", data={"reason": "Investigation not available"}).model_dump()
        )
        return

    await manager.send_to_player(
        room_code,
        player_id,
        WSMessage(
            type="investigate.result",
            data={"title": evidence.title, "content": evidence.content, "location_id": location_id},
        ),
    )


async def _handle_vote(db: AsyncSession, room_code: str, player_id: str, data: dict, websocket: WebSocket):
    import uuid

    from madaminu.services.scenario_engine import generate_ending

    suspect_id = data.get("data", {}).get("suspect_player_id", "")
    if not suspect_id:
        await websocket.send_json(WSMessage(type="error", data={"message": "Missing suspect_player_id"}).model_dump())
        return

    result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.room_code == room_code))
    game = result.scalar_one_or_none()
    if game is None or game.status != GameStatus.voting:
        await websocket.send_json(WSMessage(type="error", data={"message": "Not in voting phase"}).model_dump())
        return

    existing = await db.execute(select(Vote).where(Vote.game_id == game.id, Vote.voter_player_id == player_id))
    if existing.scalar_one_or_none() is not None:
        await websocket.send_json(WSMessage(type="error", data={"message": "Already voted"}).model_dump())
        return

    vote = Vote(
        id=str(uuid.uuid4()),
        game_id=game.id,
        voter_player_id=player_id,
        suspect_player_id=suspect_id,
    )
    db.add(vote)
    await db.commit()

    await manager.broadcast(
        room_code,
        WSMessage(type="vote.cast", data={"voter_id": player_id}),
    )

    votes_result = await db.execute(select(Vote).where(Vote.game_id == game.id))
    all_votes = votes_result.scalars().all()

    if len(all_votes) < len(game.players):
        return

    vote_summary = {}
    for v in all_votes:
        vote_summary[v.voter_player_id] = v.suspect_player_id

    await manager.broadcast(
        room_code,
        WSMessage(type="vote.results", data={"votes": vote_summary}),
    )

    try:
        ending, usage = await generate_ending(db, game.id)
        logger.info("Ending generated: %s", usage)

        await manager.broadcast(
            room_code,
            WSMessage(
                type="game.ending",
                data={
                    "ending_text": ending.ending_text,
                    "true_criminal_id": ending.true_criminal_id,
                    "objective_results": ending.objective_results,
                },
            ),
        )
    except Exception:
        logger.exception("Ending generation failed for game %s", game.id)
        await manager.broadcast(
            room_code,
            WSMessage(type="error", data={"message": "Ending generation failed"}),
        )
