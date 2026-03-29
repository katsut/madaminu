import logging

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.models import ConnectionStatus, Game, GameStatus, Player, Vote
from madaminu.schemas.game import _get_current_phase_dict as _get_current_phase_dict  # noqa: F401
from madaminu.schemas.game import build_game_state
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


async def get_game_state_for_player(db: AsyncSession, room_code: str, player_id: str) -> dict:
    result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.room_code == room_code))
    game = result.scalar_one_or_none()
    if game is None:
        return {}

    return await build_game_state(db, game, player_id)


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

            if msg_type == "intro.ready":
                await _handle_intro_ready(db, room_code, player_id, websocket)
            elif msg_type == "intro.unready":
                await _handle_intro_unready(room_code, player_id, websocket)
            elif msg_type == "intro.start_game":
                await manager.broadcast(room_code, WSMessage(type="intro.start_game", data={}))
            elif msg_type in ("phase.advance", "phase.extend", "phase.pause", "phase.resume"):
                await _handle_host_command(db, room_code, player_id, msg_type, websocket)
            elif msg_type == "speech.request":
                await _handle_speech_request(room_code, player_id, websocket)
            elif msg_type == "speech.release":
                await _handle_speech_release(room_code, player_id, data, websocket)
            elif msg_type == "investigate":
                await _handle_investigate(db, room_code, player_id, data, websocket)
            elif msg_type == "investigate.select":
                await _handle_investigate_select(db, room_code, player_id, data, websocket)
            elif msg_type == "evidence.reveal":
                await _handle_evidence_reveal(db, room_code, player_id, data, websocket)
            elif msg_type == "investigate.keep":
                await _handle_investigate_keep(db, room_code, player_id, data, websocket)
            elif msg_type == "investigate.tamper":
                await _handle_investigate_tamper(db, room_code, player_id, data, websocket)
            elif msg_type == "room_message.send":
                await _handle_room_message(db, room_code, player_id, data, websocket)
            elif msg_type == "vote.submit":
                await _handle_vote(db, room_code, player_id, data, websocket)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(room_code, player_id)

        pm = getattr(websocket.app.state, "phase_manager", None)
        if pm:
            ready_set = pm._intro_ready.get(room_code, set())
            if player_id in ready_set:
                ready_set.discard(player_id)
                count = pm.get_intro_ready_count(room_code)
                await manager.broadcast(
                    room_code,
                    WSMessage(type="intro.ready.count", data={"count": count}),
                )

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


def _get_phase_manager(websocket: WebSocket):
    return getattr(websocket.app.state, "phase_manager", None)


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
        await sm.broadcast_speech_released(room_code, player_id, transcript)


async def _handle_intro_ready(db: AsyncSession, room_code: str, player_id: str, websocket: WebSocket):
    pm = _get_phase_manager(websocket)
    if pm is None:
        return

    pm.set_intro_ready(room_code, player_id)
    count = pm.get_intro_ready_count(room_code)

    await manager.broadcast(
        room_code,
        WSMessage(type="intro.ready.count", data={"count": count}),
    )

    result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.room_code == room_code))
    game = result.scalar_one_or_none()
    if game:
        human_count = sum(1 for p in game.players if not p.is_ai)
        if count >= human_count:
            pm.clear_intro_ready(room_code)
            await manager.broadcast(
                room_code,
                WSMessage(type="intro.all_ready", data={}),
            )


async def _handle_intro_unready(room_code: str, player_id: str, websocket: WebSocket):
    pm = _get_phase_manager(websocket)
    if pm is None:
        return

    ready_set = pm._intro_ready.get(room_code, set())
    ready_set.discard(player_id)
    count = pm.get_intro_ready_count(room_code)

    await manager.broadcast(
        room_code,
        WSMessage(type="intro.ready.count", data={"count": count}),
    )


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
    elif msg_type == "phase.pause":
        await pm.pause_phase(game.id, room_code)
    elif msg_type == "phase.resume":
        await pm.resume_phase(game.id, room_code)


async def _handle_investigate_select(
    db: AsyncSession, room_code: str, player_id: str, data: dict, websocket: WebSocket
):
    from madaminu.models import Phase, PhaseType
    from madaminu.services.scenario_engine import investigate_location

    pm = _get_phase_manager(websocket)
    if pm is None:
        return
    payload = data.get("data", {})
    location_id = payload.get("location_id", "")
    feature = payload.get("feature")
    pm.set_investigation_selection(room_code, player_id, location_id if location_id else None, feature)
    logger.info("Player %s selected: location=%s feature=%s", player_id, location_id or "(none)", feature or "(none)")

    if location_id:
        await _broadcast_colocated_players(db, room_code, location_id, pm)

    if feature and location_id:
        result = await db.execute(select(Game).where(Game.room_code == room_code))
        game = result.scalar_one_or_none()
        if game and game.current_phase_id:
            phase_result = await db.execute(select(Phase).where(Phase.id == game.current_phase_id))
            phase = phase_result.scalar_one_or_none()
            if phase and phase.phase_type == PhaseType.investigation:
                try:
                    discovery, usage = await investigate_location(db, game.id, player_id, location_id, feature)
                    if discovery:
                        pm.add_discovery(room_code, player_id, discovery)
                        is_alone = _is_alone_at_location(pm, room_code, player_id, location_id)
                        await manager.send_to_player(
                            room_code,
                            player_id,
                            WSMessage(
                                type="investigate.discovery",
                                data={
                                    "id": discovery["id"],
                                    "title": discovery["title"],
                                    "content": discovery["content"],
                                    "can_tamper": is_alone,
                                },
                            ),
                        )
                except Exception:
                    logger.exception("Immediate investigation failed for %s", player_id)


def _is_alone_at_location(pm, room_code: str, player_id: str, location_id: str) -> bool:
    selections = pm.get_investigation_selections(room_code)
    others = [pid for pid, sel in selections.items() if sel.get("location_id") == location_id and pid != player_id]
    return len(others) == 0


async def _broadcast_colocated_players(db: AsyncSession, room_code: str, location_id: str, pm):
    selections = pm.get_investigation_selections(room_code)
    colocated_ids = [pid for pid, sel in selections.items() if sel.get("location_id") == location_id]
    if len(colocated_ids) < 2:
        return

    result = await db.execute(select(Player).where(Player.id.in_(colocated_ids)))
    players = result.scalars().all()
    player_list = [
        {
            "player_id": p.id,
            "character_name": p.character_name or p.display_name,
            "portrait_url": f"/api/v1/images/player/{p.id}" if p.portrait_image else None,
        }
        for p in players
    ]

    for pid in colocated_ids:
        others = [p for p in player_list if p["player_id"] != pid]
        await manager.send_to_player(
            room_code,
            pid,
            WSMessage(type="location.colocated", data={"players": others}),
        )


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


async def _handle_evidence_reveal(db: AsyncSession, room_code: str, player_id: str, data: dict, websocket: WebSocket):
    from madaminu.models import Evidence

    evidence_id = data.get("data", {}).get("evidence_id", "")
    if not evidence_id:
        return

    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id, Evidence.player_id == player_id))
    evidence = result.scalar_one_or_none()
    if evidence is None:
        return

    player_result = await db.execute(select(Player).where(Player.id == player_id))
    player = player_result.scalar_one_or_none()
    player_name = player.character_name or player.display_name if player else "不明"

    await manager.broadcast(
        room_code,
        WSMessage(
            type="evidence.revealed",
            data={
                "player_id": player_id,
                "player_name": player_name,
                "title": evidence.title,
                "content": evidence.content,
            },
        ),
    )


async def _handle_investigate_keep(db: AsyncSession, room_code: str, player_id: str, data: dict, websocket: WebSocket):
    from madaminu.services.scenario_engine import keep_evidence

    pm = _get_phase_manager(websocket)
    if pm is None:
        return

    discovery_id = data.get("data", {}).get("discovery_id", "")
    discoveries = pm.get_discoveries(room_code, player_id)
    discovery = next((d for d in discoveries if d["id"] == discovery_id), None)
    if discovery is None:
        return

    result = await db.execute(select(Game).where(Game.room_code == room_code))
    game = result.scalar_one_or_none()
    if game is None:
        return

    evidence = await keep_evidence(db, game.id, player_id, discovery)
    await manager.send_to_player(
        room_code,
        player_id,
        WSMessage(
            type="investigate.kept",
            data={"id": evidence.id, "title": evidence.title, "content": evidence.content},
        ),
    )


async def _handle_investigate_tamper(
    db: AsyncSession, room_code: str, player_id: str, data: dict, websocket: WebSocket
):
    from madaminu.services.scenario_engine import tamper_evidence

    pm = _get_phase_manager(websocket)
    if pm is None:
        return

    discovery_id = data.get("data", {}).get("discovery_id", "")
    discoveries = pm.get_discoveries(room_code, player_id)
    discovery = next((d for d in discoveries if d["id"] == discovery_id), None)
    if discovery is None:
        return

    selections = pm.get_investigation_selections(room_code)
    sel = selections.get(player_id, {})
    location_id = sel.get("location_id")
    if not location_id or not _is_alone_at_location(pm, room_code, player_id, location_id):
        await websocket.send_json(
            WSMessage(type="error", data={"message": "同室に他のプレイヤーがいます"}).model_dump()
        )
        return

    result = await db.execute(select(Game).where(Game.room_code == room_code))
    game = result.scalar_one_or_none()
    if game is None:
        return

    tampered = await tamper_evidence(db, game.id, player_id, discovery)
    pm.replace_discovery(room_code, player_id, discovery_id, tampered)
    await manager.send_to_player(
        room_code,
        player_id,
        WSMessage(
            type="investigate.tampered",
            data={"id": tampered["id"], "title": tampered["title"], "content": tampered["content"]},
        ),
    )


async def _handle_room_message(db: AsyncSession, room_code: str, player_id: str, data: dict, websocket: WebSocket):
    from madaminu.ws.messages import RoomMessageData

    pm = _get_phase_manager(websocket)
    if pm is None:
        return

    text = data.get("data", {}).get("text", "").strip()
    if not text:
        return

    selections = pm.get_investigation_selections(room_code)
    sender_selection = selections.get(player_id, {})
    sender_location = sender_selection.get("location_id")
    if not sender_location:
        return

    result = await db.execute(select(Player).where(Player.id == player_id))
    sender = result.scalar_one_or_none()
    if sender is None:
        return

    sender_name = sender.character_name or sender.display_name

    for other_id, other_sel in selections.items():
        if other_id == player_id:
            continue
        if other_sel.get("location_id") == sender_location:
            await manager.send_to_player(
                room_code,
                other_id,
                WSMessage(
                    type="room_message.received",
                    data=RoomMessageData(
                        sender_id=player_id,
                        sender_name=sender_name,
                        text=text,
                    ).model_dump(),
                ),
            )


async def _handle_vote(db: AsyncSession, room_code: str, player_id: str, data: dict, websocket: WebSocket):
    import uuid

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

    pm = _get_phase_manager(websocket)
    if pm:
        await pm._generate_and_broadcast_ending(game.id, room_code)
