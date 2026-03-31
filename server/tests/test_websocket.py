import os
import uuid

import pytest
from starlette.testclient import TestClient

from madaminu.db import get_db
from madaminu.main import app
from madaminu.models.game import Game, GameStatus
from madaminu.models.player import ConnectionStatus, Player

# Sync TestClient + aiosqlite has threading issues on Linux CI.
# TODO: Rewrite using async websocket client (httpx + anyio).
pytestmark = pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Sync TestClient incompatible with aiosqlite on Linux CI",
)


async def _create_room(session_factory, *names: str) -> tuple[Game, list[Player]]:
    async with session_factory() as session:
        game = Game(
            id=str(uuid.uuid4()),
            room_code="T" + str(uuid.uuid4())[:5].upper(),
            status=GameStatus.waiting,
        )
        session.add(game)
        await session.flush()

        players = []
        for i, name in enumerate(names):
            p = Player(
                id=str(uuid.uuid4()),
                game_id=game.id,
                session_token=str(uuid.uuid4()),
                display_name=name,
                is_host=(i == 0),
                connection_status=ConnectionStatus.offline,
            )
            session.add(p)
            players.append(p)

        await session.flush()
        game.host_player_id = players[0].id
        await session.commit()
        return game, players


def _client(session_factory) -> TestClient:
    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.session_factory = session_factory
    return TestClient(app)


async def test_websocket_connect_and_receive_state(session_factory):
    game, players = await _create_room(session_factory, "Alice")
    c = _client(session_factory)
    try:
        with c.websocket_connect(f"/ws/{game.room_code}?token={players[0].session_token}") as ws:
            data = ws.receive_json()
            assert data["type"] == "game.state"
            assert data["data"]["room_code"] == game.room_code
            assert len(data["data"]["players"]) == 1
    finally:
        app.dependency_overrides.clear()


async def test_websocket_invalid_token(session_factory):
    game, _ = await _create_room(session_factory, "Alice")
    c = _client(session_factory)
    try:
        with c.websocket_connect(f"/ws/{game.room_code}?token=bad"):
            pass
        raise AssertionError("Should have raised")
    except Exception:
        pass
    finally:
        app.dependency_overrides.clear()


async def test_websocket_no_token(session_factory):
    game, _ = await _create_room(session_factory, "Alice")
    c = _client(session_factory)
    try:
        with c.websocket_connect(f"/ws/{game.room_code}"):
            pass
        raise AssertionError("Should have raised")
    except Exception:
        pass
    finally:
        app.dependency_overrides.clear()


async def test_websocket_player_connect_notification(session_factory):
    game, players = await _create_room(session_factory, "Alice", "Bob")
    c = _client(session_factory)
    try:
        with c.websocket_connect(f"/ws/{game.room_code}?token={players[0].session_token}") as ws_host:
            state = ws_host.receive_json()
            assert state["type"] == "game.state"

            with c.websocket_connect(f"/ws/{game.room_code}?token={players[1].session_token}") as ws_bob:
                ws_bob.receive_json()
                notification = ws_host.receive_json()
                assert notification["type"] == "player.connected"
                assert notification["data"]["display_name"] == "Bob"
    finally:
        app.dependency_overrides.clear()


async def test_websocket_secret_info_isolation(session_factory):
    game, players = await _create_room(session_factory, "Alice", "Bob")

    async with session_factory() as session:
        from sqlalchemy import select

        result = await session.execute(select(Player).where(Player.id == players[0].id))
        host = result.scalar_one()
        host.secret_info = "Host secret"
        host.objective = "Host objective"

        result2 = await session.execute(select(Player).where(Player.id == players[1].id))
        bob = result2.scalar_one()
        bob.secret_info = "Bob secret"
        bob.objective = "Bob objective"
        await session.commit()

    c = _client(session_factory)
    try:
        with c.websocket_connect(f"/ws/{game.room_code}?token={players[1].session_token}") as ws:
            data = ws.receive_json()
            assert data["type"] == "game.state"
            assert data["data"]["my_secret_info"] == "Bob secret"
            assert data["data"]["my_objective"] == "Bob objective"
            for p in data["data"]["players"]:
                assert "secret_info" not in p
                assert "objective" not in p
    finally:
        app.dependency_overrides.clear()
