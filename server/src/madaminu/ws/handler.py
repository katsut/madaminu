import logging

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.models import ConnectionStatus, Game, Player
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

    players_public = [
        {
            "id": p.id,
            "display_name": p.display_name,
            "character_name": p.character_name,
            "is_host": p.is_host,
            "connection_status": p.connection_status,
        }
        for p in game.players
    ]

    state = {
        "room_code": game.room_code,
        "status": game.status,
        "host_player_id": game.host_player_id,
        "players": players_public,
    }

    current_player = next((p for p in game.players if p.id == player_id), None)
    if current_player:
        state["my_secret_info"] = current_player.secret_info
        state["my_objective"] = current_player.objective
        state["my_role"] = current_player.role

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
