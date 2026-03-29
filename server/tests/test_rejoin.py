"""Tests for room rejoin by device_id."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from madaminu.db import get_db
from madaminu.main import app
from madaminu.models import Base
from madaminu.services.speech_manager import SpeechManager


@pytest.fixture()
async def rejoin_client():
    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.speech_manager = SpeechManager(session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


async def test_rejoin_same_device_returns_existing_player(rejoin_client):
    # Create room
    resp = await rejoin_client.post(
        "/api/v1/rooms",
        json={"display_name": "Alice"},
        headers={"x-device-id": "device-123"},
    )
    assert resp.status_code == 200
    room_code = resp.json()["room_code"]
    original_player_id = resp.json()["player_id"]
    original_token = resp.json()["session_token"]

    # Rejoin with same device_id
    resp2 = await rejoin_client.post(
        f"/api/v1/rooms/{room_code}/join",
        json={"display_name": "Alice Again"},
        headers={"x-device-id": "device-123"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["player_id"] == original_player_id
    assert resp2.json()["session_token"] != original_token  # New token


async def test_rejoin_different_device_creates_new_player(rejoin_client):
    resp = await rejoin_client.post(
        "/api/v1/rooms",
        json={"display_name": "Alice"},
        headers={"x-device-id": "device-A"},
    )
    room_code = resp.json()["room_code"]
    original_player_id = resp.json()["player_id"]

    resp2 = await rejoin_client.post(
        f"/api/v1/rooms/{room_code}/join",
        json={"display_name": "Bob"},
        headers={"x-device-id": "device-B"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["player_id"] != original_player_id


async def test_rejoin_preserves_host(rejoin_client):
    resp = await rejoin_client.post(
        "/api/v1/rooms",
        json={"display_name": "Host"},
        headers={"x-device-id": "device-host"},
    )
    room_code = resp.json()["room_code"]

    resp2 = await rejoin_client.post(
        f"/api/v1/rooms/{room_code}/join",
        json={"display_name": "Host Rejoined"},
        headers={"x-device-id": "device-host"},
    )
    player_id = resp2.json()["player_id"]

    room_resp = await rejoin_client.get(f"/api/v1/rooms/{room_code}")
    host = next(p for p in room_resp.json()["players"] if p["id"] == player_id)
    assert host["is_host"] is True
