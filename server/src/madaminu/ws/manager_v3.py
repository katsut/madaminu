"""WS connection manager v3. Stateless except for active connections."""

import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WSManager:
    def __init__(self):
        self._connections: dict[str, dict[str, WebSocket]] = {}  # room_code -> {player_id: ws}

    def connect(self, room_code: str, player_id: str, ws: WebSocket):
        self._connections.setdefault(room_code, {})[player_id] = ws
        logger.info("WS connected: %s in %s", player_id, room_code)

    def disconnect(self, room_code: str, player_id: str):
        conns = self._connections.get(room_code, {})
        conns.pop(player_id, None)
        if not conns:
            self._connections.pop(room_code, None)
        logger.info("WS disconnected: %s from %s", player_id, room_code)

    async def send_to(self, room_code: str, player_id: str, message: dict):
        ws = self._connections.get(room_code, {}).get(player_id)
        if ws:
            await ws.send_json(message)

    async def broadcast(self, room_code: str, message: dict, exclude: str | None = None):
        for pid, ws in self._connections.get(room_code, {}).items():
            if pid != exclude:
                try:
                    await ws.send_json(message)
                except Exception:
                    logger.warning("broadcast failed for %s in %s", pid, room_code)

    async def broadcast_game_state(self, room_code: str, game_id: str, game_service):
        """Send personalized game.state to each connected player."""
        for pid, ws in self._connections.get(room_code, {}).items():
            try:
                state = await game_service.get_state(game_id, pid)
                await ws.send_json({"type": "game.state", "data": state})
            except Exception:
                logger.warning("game.state send failed for %s in %s", pid, room_code)

    async def ping_all(self):
        """Send ping to all connections. Called periodically."""
        for room_code, conns in self._connections.items():
            for pid, ws in list(conns.items()):
                try:
                    await ws.send_json({"type": "ping"})
                except Exception:
                    logger.warning("ping failed for %s in %s, removing", pid, room_code)
                    conns.pop(pid, None)

    def get_room_code_for_game(self, game_id: str) -> str | None:
        """Reverse lookup: find room_code by checking connected games."""
        # This is called from actions that have game_id but need room_code.
        # In practice, the handler passes room_code directly.
        return None  # Not needed if handler always passes room_code
