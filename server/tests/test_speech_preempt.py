"""Tests for speech manager preemption behavior."""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, patch

from madaminu.models import Base
from madaminu.services.speech_manager import SpeechManager


@pytest.fixture()
async def speech_manager():
    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    sm = SpeechManager(session_factory)
    yield sm
    await engine.dispose()


async def test_preempt_releases_current_speaker(speech_manager):
    """When player B requests speech while A is speaking, A should be released."""
    with patch.object(speech_manager, "broadcast_speech_released", new_callable=AsyncMock):
        result_a = await speech_manager.request_speech("room1", "playerA")
        assert result_a is True
        assert speech_manager.get_current_speaker("room1") == "playerA"

        result_b = await speech_manager.request_speech("room1", "playerB")
        assert result_b is True
        assert speech_manager.get_current_speaker("room1") == "playerB"

        speech_manager.broadcast_speech_released.assert_called_once_with("room1", "playerA")


async def test_same_player_request_returns_true(speech_manager):
    with patch.object(speech_manager, "broadcast_speech_released", new_callable=AsyncMock):
        await speech_manager.request_speech("room1", "playerA")
        result = await speech_manager.request_speech("room1", "playerA")
        assert result is True
        assert speech_manager.get_current_speaker("room1") == "playerA"
        speech_manager.broadcast_speech_released.assert_not_called()
