"""Tests for timer resilience - timer should continue even if broadcast fails."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from madaminu.models import Base, Game, GameStatus, Phase, PhaseType, Player
from madaminu.services.phase_manager import PhaseManager


@pytest.fixture()
async def pm_env():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        game = Game(id="g1", room_code="TEST01", status=GameStatus.playing, turn_count=1)
        db.add(game)
        await db.flush()

        player = Player(
            id="p1",
            game_id="g1",
            session_token="tok",
            display_name="Alice",
            character_name="探偵",
            is_host=True,
        )
        db.add(player)
        await db.flush()

        phase1 = Phase(
            id="ph1",
            game_id="g1",
            phase_type=PhaseType.planning,
            phase_order=0,
            duration_sec=2,
            started_at=datetime.utcnow(),
            deadline_at=datetime.utcnow() + timedelta(seconds=2),
        )
        phase2 = Phase(
            id="ph2",
            game_id="g1",
            phase_type=PhaseType.investigation,
            phase_order=1,
            duration_sec=120,
        )
        db.add(phase1)
        db.add(phase2)

        game.current_phase_id = "ph1"
        await db.commit()

    pm = PhaseManager(session_factory)
    yield pm, session_factory, engine
    await engine.dispose()


async def test_timer_advances_after_broadcast_failure(pm_env):
    """Timer should call advance_phase even if broadcast throws exceptions."""
    pm, session_factory, _ = pm_env

    broadcast_mock = AsyncMock(side_effect=Exception("WS broadcast failed"))
    advance_called = asyncio.Event()

    async def mock_advance(*args, **kwargs):
        advance_called.set()
        return None

    with (
        patch("madaminu.ws.handler_old.manager.broadcast", broadcast_mock),
        patch.object(pm, "advance_phase", mock_advance),
    ):
        pm._start_timer(
            "g1",
            "TEST01",
            Phase(
                id="ph1",
                game_id="g1",
                phase_type=PhaseType.planning,
                phase_order=0,
                duration_sec=1,
                started_at=datetime.utcnow(),
            ),
        )

        try:
            await asyncio.wait_for(advance_called.wait(), timeout=5)
        except TimeoutError:
            pytest.fail("advance_phase was never called - timer died after broadcast failure")

    assert advance_called.is_set()


async def test_voting_timer_auto_advances(pm_env):
    """Voting phase timer SHOULD auto-advance when it expires (time limit or all votes)."""
    pm, session_factory, _ = pm_env

    async with session_factory() as db:
        game_result = await db.execute(select(Game).where(Game.id == "g1"))
        game = game_result.scalar_one()

        voting = Phase(
            id="ph_vote",
            game_id="g1",
            phase_type=PhaseType.voting,
            phase_order=2,
            duration_sec=1,
            started_at=datetime.utcnow(),
            deadline_at=datetime.utcnow() + timedelta(seconds=1),
        )
        db.add(voting)
        game.current_phase_id = "ph_vote"
        await db.commit()

    advance_called = asyncio.Event()

    async def mock_advance(*args, **kwargs):
        advance_called.set()

    with (
        patch("madaminu.ws.handler_old.manager.broadcast", AsyncMock()),
        patch.object(pm, "advance_phase", mock_advance),
    ):
        pm._start_timer("g1", "TEST01", voting)
        try:
            await asyncio.wait_for(advance_called.wait(), timeout=5)
        except TimeoutError:
            pytest.fail("advance_phase was never called for voting phase")

    assert advance_called.is_set()
