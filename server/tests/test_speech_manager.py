import uuid

import pytest
from sqlalchemy import select

from madaminu.models import Game, GameStatus, Phase, PhaseType, Player, SpeechLog
from madaminu.models.player import ConnectionStatus
from madaminu.services.speech_manager import SpeechManager


async def _create_playing_game(session_factory) -> tuple[str, str, str, str]:
    """Returns (game_id, room_code, player1_id, player2_id)."""
    async with session_factory() as db:
        game = Game(
            id=str(uuid.uuid4()),
            room_code="S" + str(uuid.uuid4())[:5].upper(),
            status=GameStatus.playing,
        )
        db.add(game)

        p1 = Player(
            id=str(uuid.uuid4()),
            game_id=game.id,
            session_token=str(uuid.uuid4()),
            display_name="Alice",
            is_host=True,
            connection_status=ConnectionStatus.online,
        )
        p2 = Player(
            id=str(uuid.uuid4()),
            game_id=game.id,
            session_token=str(uuid.uuid4()),
            display_name="Bob",
            is_host=False,
            connection_status=ConnectionStatus.online,
        )
        db.add(p1)
        db.add(p2)
        await db.flush()

        game.host_player_id = p1.id

        phase = Phase(
            id=str(uuid.uuid4()),
            game_id=game.id,
            phase_type=PhaseType.discussion,
            phase_order=0,
            duration_sec=300,
        )
        db.add(phase)
        await db.flush()

        game.current_phase_id = phase.id
        await db.commit()
        return game.id, game.room_code, p1.id, p2.id


@pytest.fixture
def speech_manager(session_factory):
    return SpeechManager(session_factory)


async def test_request_speech_granted(session_factory, speech_manager):
    _, room_code, p1_id, _ = await _create_playing_game(session_factory)

    result = await speech_manager.request_speech(room_code, p1_id)
    assert result is True
    assert speech_manager.get_current_speaker(room_code) == p1_id

    speech_manager.cleanup_room(room_code)


async def test_request_speech_preempts_current_speaker(session_factory, speech_manager):
    _, room_code, p1_id, p2_id = await _create_playing_game(session_factory)

    await speech_manager.request_speech(room_code, p1_id)
    result = await speech_manager.request_speech(room_code, p2_id)

    assert result is True
    assert speech_manager.get_current_speaker(room_code) == p2_id

    speech_manager.cleanup_room(room_code)


async def test_release_speech(session_factory, speech_manager):
    _, room_code, p1_id, _ = await _create_playing_game(session_factory)

    await speech_manager.request_speech(room_code, p1_id)
    released = await speech_manager.release_speech(room_code, p1_id, "Hello everyone")

    assert released is True
    assert speech_manager.get_current_speaker(room_code) is None

    speech_manager.cleanup_room(room_code)


async def test_release_by_wrong_player_fails(session_factory, speech_manager):
    _, room_code, p1_id, p2_id = await _create_playing_game(session_factory)

    await speech_manager.request_speech(room_code, p1_id)
    released = await speech_manager.release_speech(room_code, p2_id, "I shouldn't speak")

    assert released is False
    assert speech_manager.get_current_speaker(room_code) == p1_id

    speech_manager.cleanup_room(room_code)


async def test_release_saves_transcript(session_factory, speech_manager):
    _, room_code, p1_id, _ = await _create_playing_game(session_factory)

    await speech_manager.request_speech(room_code, p1_id)
    await speech_manager.release_speech(room_code, p1_id, "I saw something suspicious")

    async with session_factory() as db:
        result = await db.execute(select(SpeechLog).where(SpeechLog.player_id == p1_id))
        log = result.scalar_one()
        assert log.transcript == "I saw something suspicious"

    speech_manager.cleanup_room(room_code)


async def test_release_empty_transcript_skips_save(session_factory, speech_manager):
    _, room_code, p1_id, _ = await _create_playing_game(session_factory)

    await speech_manager.request_speech(room_code, p1_id)
    await speech_manager.release_speech(room_code, p1_id, "")

    async with session_factory() as db:
        result = await db.execute(select(SpeechLog).where(SpeechLog.player_id == p1_id))
        logs = result.scalars().all()
        assert len(logs) == 0

    speech_manager.cleanup_room(room_code)


async def test_second_player_can_speak_after_release(session_factory, speech_manager):
    _, room_code, p1_id, p2_id = await _create_playing_game(session_factory)

    await speech_manager.request_speech(room_code, p1_id)
    await speech_manager.release_speech(room_code, p1_id, "Done talking")

    result = await speech_manager.request_speech(room_code, p2_id)
    assert result is True
    assert speech_manager.get_current_speaker(room_code) == p2_id

    speech_manager.cleanup_room(room_code)


async def test_force_release(session_factory, speech_manager):
    _, room_code, p1_id, _ = await _create_playing_game(session_factory)

    await speech_manager.request_speech(room_code, p1_id)
    speech_manager.force_release(room_code)

    assert speech_manager.get_current_speaker(room_code) is None

    speech_manager.cleanup_room(room_code)


async def test_cleanup_room(session_factory, speech_manager):
    _, room_code, p1_id, _ = await _create_playing_game(session_factory)

    await speech_manager.request_speech(room_code, p1_id)
    speech_manager.cleanup_room(room_code)

    assert speech_manager.get_current_speaker(room_code) is None
    assert room_code not in speech_manager._speakers


async def test_get_current_speaker_no_room(speech_manager):
    assert speech_manager.get_current_speaker("NOROOM") is None
