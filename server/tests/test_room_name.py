"""Tests for room name feature."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from madaminu.db import get_db
from madaminu.main import app
from madaminu.models import Base
from madaminu.services.speech_manager import SpeechManager


@pytest.fixture()
async def client():
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


async def test_create_room_with_name(client):
    resp = await client.post("/api/v1/rooms", json={"display_name": "Alice", "room_name": "テスト部屋"})
    assert resp.status_code == 200
    room_code = resp.json()["room_code"]

    room_resp = await client.get(f"/api/v1/rooms/{room_code}")
    assert room_resp.json()["room_name"] == "テスト部屋"


async def test_create_room_without_name(client):
    resp = await client.post("/api/v1/rooms", json={"display_name": "Alice"})
    assert resp.status_code == 200
    room_code = resp.json()["room_code"]

    room_resp = await client.get(f"/api/v1/rooms/{room_code}")
    assert room_resp.json()["room_name"] is None


async def test_room_name_in_list(client):
    await client.post("/api/v1/rooms", json={"display_name": "Alice", "room_name": "週末ミステリー"})
    resp = await client.get("/api/v1/rooms")
    assert resp.status_code == 200
    rooms = resp.json()
    assert any(r["room_name"] == "週末ミステリー" for r in rooms)
