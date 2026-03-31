"""WS endpoint v3. Stateless handler — all state in DB."""

import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from madaminu.models import ConnectionStatus, Game, Player
from madaminu.services.discovery_service import DiscoveryService
from madaminu.services.game_service import GameService
from madaminu.services.speech_service import SpeechService
from madaminu.ws.actions import (
    handle_advance,
    handle_keep_evidence,
    handle_reveal_evidence,
    handle_room_message,
    handle_select_location,
    handle_speech_release,
    handle_speech_request,
    handle_vote,
)
from madaminu.ws.manager_v3 import WSManager

logger = logging.getLogger(__name__)

ws_manager = WSManager()

# Ping interval (seconds) — keeps Railway proxy alive
PING_INTERVAL = 20


async def start_ping_task():
    while True:
        await asyncio.sleep(PING_INTERVAL)
        await ws_manager.ping_all()


async def handle_websocket_v3(
    websocket: WebSocket,
    room_code: str,
    session_factory: async_sessionmaker[AsyncSession],
):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    # Authenticate
    async with session_factory() as db:
        result = await db.execute(
            select(Player)
            .join(Game, Player.game_id == Game.id)
            .options(selectinload(Player.game))
            .where(Game.room_code == room_code, Player.session_token == token)
        )
        player = result.scalar_one_or_none()
        if player is None:
            await websocket.close(code=4001, reason="Invalid token")
            return

        player_id = player.id
        game_id = player.game_id
        display_name = player.display_name

        player.connection_status = ConnectionStatus.online
        await db.commit()

    await websocket.accept()
    ws_manager.connect(room_code, player_id, websocket)

    # Build services
    game_service = GameService(session_factory)
    speech_service = SpeechService(session_factory)
    discovery_service = DiscoveryService(session_factory)

    # Send initial game.state
    state = await game_service.get_state(game_id, player_id)
    await websocket.send_json({"type": "game.state", "data": state})

    # Broadcast connection
    await ws_manager.broadcast(room_code, {
        "type": "player.connected",
        "data": {"player_id": player_id, "display_name": display_name},
    }, exclude=player_id)

    # Build players lookup (player_id -> character_name) for speech/evidence
    async with session_factory() as db:
        game_result = await db.execute(
            select(Game).options(selectinload(Game.players)).where(Game.id == game_id)
        )
        game = game_result.scalar_one()
        players = {p.id: p.character_name or p.display_name for p in game.players}

    try:
        while True:
            raw = await websocket.receive_json()
            msg_type = raw.get("type", "")
            data = raw.get("data", {})
            logger.info("WS %s from %s in %s", msg_type, player_id, room_code)

            # v3 type + legacy iOS type aliases
            if msg_type in ("advance", "phase.advance", "phase.timer_expired"):
                await handle_advance(
                    game_id, room_code, player_id, data,
                    game_service, discovery_service, ws_manager,
                )

            elif msg_type in ("select_location", "investigate.select"):
                await handle_select_location(
                    game_id, room_code, player_id, data,
                    game_service, ws_manager,
                )

            elif msg_type in ("keep_evidence", "investigate.keep"):
                await handle_keep_evidence(
                    game_id, room_code, player_id, data,
                    game_service, ws_manager,
                )

            elif msg_type == "speech.request":
                await handle_speech_request(
                    game_id, room_code, player_id,
                    speech_service, ws_manager,
                )

            elif msg_type == "speech.release":
                await handle_speech_release(
                    game_id, room_code, player_id, data,
                    speech_service, ws_manager, players,
                )

            elif msg_type in ("reveal_evidence", "evidence.reveal"):
                await handle_reveal_evidence(
                    game_id, room_code, player_id, data,
                    game_service, ws_manager, players,
                )

            elif msg_type in ("vote", "vote.submit"):
                await handle_vote(
                    game_id, room_code, player_id, data,
                    game_service, discovery_service, ws_manager,
                )

            elif msg_type in ("room_message", "room_message.send"):
                await handle_room_message(
                    room_code, player_id, data,
                    ws_manager, players,
                )

            elif msg_type == "intro.ready":
                await _handle_intro_ready(
                    game_id, room_code, player_id,
                    session_factory, ws_manager,
                )

            elif msg_type == "intro.unready":
                await _handle_intro_unready(
                    game_id, room_code, player_id,
                    session_factory, ws_manager,
                )

            elif msg_type in ("pong", "phase.timer", "phase.extend", "phase.pause", "phase.resume"):
                pass

            else:
                logger.warning("Unknown message type: %s", msg_type)

    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(room_code, player_id)

        async with session_factory() as db:
            result = await db.execute(select(Player).where(Player.id == player_id))
            p = result.scalar_one_or_none()
            if p:
                p.connection_status = ConnectionStatus.offline
                await db.commit()

        await ws_manager.broadcast(room_code, {
            "type": "player.disconnected",
            "data": {"player_id": player_id},
        })


async def _handle_intro_ready(
    game_id: str,
    room_code: str,
    player_id: str,
    session_factory: async_sessionmaker[AsyncSession],
    ws: WSManager,
):
    async with session_factory() as db:
        result = await db.execute(select(Player).where(Player.id == player_id))
        player = result.scalar_one()
        player.is_intro_ready = True
        await db.commit()

        game_result = await db.execute(
            select(Game).options(selectinload(Game.players)).where(Game.id == game_id)
        )
        game = game_result.scalar_one()
        ready_count = sum(1 for p in game.players if p.is_intro_ready and not p.is_ai)
        human_count = sum(1 for p in game.players if not p.is_ai)

    await ws.broadcast(room_code, {
        "type": "intro.ready.count",
        "data": {"count": ready_count},
    })

    if ready_count >= human_count:
        await ws.broadcast(room_code, {"type": "intro.all_ready", "data": {}})


async def _handle_intro_unready(
    game_id: str,
    room_code: str,
    player_id: str,
    session_factory: async_sessionmaker[AsyncSession],
    ws: WSManager,
):
    async with session_factory() as db:
        result = await db.execute(select(Player).where(Player.id == player_id))
        player = result.scalar_one()
        player.is_intro_ready = False
        await db.commit()

        game_result = await db.execute(
            select(Game).options(selectinload(Game.players)).where(Game.id == game_id)
        )
        game = game_result.scalar_one()
        ready_count = sum(1 for p in game.players if p.is_intro_ready and not p.is_ai)

    await ws.broadcast(room_code, {
        "type": "intro.ready.count",
        "data": {"count": ready_count},
    })
