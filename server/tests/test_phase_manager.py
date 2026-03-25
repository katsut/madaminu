import uuid

import pytest
from sqlalchemy import select

from madaminu.models import Game, GameStatus, Phase, PhaseType, Player
from madaminu.models.player import ConnectionStatus
from madaminu.services.phase_manager import PhaseManager


async def _create_game_with_phases(session_factory, num_phases=3) -> tuple[str, str, list[str]]:
    phase_configs = [
        (PhaseType.investigation, 300),
        (PhaseType.discussion, 300),
        (PhaseType.voting, 120),
    ]

    async with session_factory() as db:
        game = Game(
            id=str(uuid.uuid4()),
            room_code="P" + str(uuid.uuid4())[:5].upper(),
            status=GameStatus.playing,
        )
        db.add(game)

        player = Player(
            id=str(uuid.uuid4()),
            game_id=game.id,
            session_token=str(uuid.uuid4()),
            display_name="Alice",
            is_host=True,
            connection_status=ConnectionStatus.offline,
        )
        db.add(player)
        await db.flush()
        game.host_player_id = player.id

        phase_ids = []
        for i in range(min(num_phases, len(phase_configs))):
            pt, dur = phase_configs[i]
            phase = Phase(
                id=str(uuid.uuid4()),
                game_id=game.id,
                phase_type=pt,
                phase_order=i,
                duration_sec=dur,
            )
            db.add(phase)
            phase_ids.append(phase.id)

        await db.commit()
        return game.id, game.room_code, phase_ids


@pytest.fixture
def phase_manager(session_factory):
    return PhaseManager(session_factory)


async def test_start_first_phase(session_factory, phase_manager):
    game_id, room_code, phase_ids = await _create_game_with_phases(session_factory)

    phase = await phase_manager.start_first_phase(game_id, room_code)

    assert phase.id == phase_ids[0]
    assert phase.phase_type == PhaseType.investigation
    assert phase.started_at is not None

    async with session_factory() as db:
        result = await db.execute(select(Game).where(Game.id == game_id))
        game = result.scalar_one()
        assert game.current_phase_id == phase_ids[0]

    phase_manager.cleanup_game(game_id)


async def test_advance_phase(session_factory, phase_manager):
    game_id, room_code, phase_ids = await _create_game_with_phases(session_factory)

    await phase_manager.start_first_phase(game_id, room_code)
    next_phase = await phase_manager.advance_phase(game_id, room_code)

    assert next_phase is not None
    assert next_phase.id == phase_ids[1]
    assert next_phase.phase_type == PhaseType.discussion
    assert next_phase.started_at is not None

    async with session_factory() as db:
        result = await db.execute(select(Game).where(Game.id == game_id))
        game = result.scalar_one()
        assert game.current_phase_id == phase_ids[1]

        prev = await db.execute(select(Phase).where(Phase.id == phase_ids[0]))
        prev_phase = prev.scalar_one()
        assert prev_phase.ended_at is not None

    phase_manager.cleanup_game(game_id)


async def test_advance_to_voting_updates_game_status(session_factory, phase_manager):
    game_id, room_code, phase_ids = await _create_game_with_phases(session_factory)

    await phase_manager.start_first_phase(game_id, room_code)
    await phase_manager.advance_phase(game_id, room_code)
    voting_phase = await phase_manager.advance_phase(game_id, room_code)

    assert voting_phase is not None
    assert voting_phase.phase_type == PhaseType.voting

    async with session_factory() as db:
        result = await db.execute(select(Game).where(Game.id == game_id))
        game = result.scalar_one()
        assert game.status == GameStatus.voting

    phase_manager.cleanup_game(game_id)


async def test_advance_past_last_phase_ends_game(session_factory, phase_manager):
    game_id, room_code, phase_ids = await _create_game_with_phases(session_factory)

    await phase_manager.start_first_phase(game_id, room_code)
    await phase_manager.advance_phase(game_id, room_code)
    await phase_manager.advance_phase(game_id, room_code)
    result = await phase_manager.advance_phase(game_id, room_code)

    assert result is None

    async with session_factory() as db:
        game_result = await db.execute(select(Game).where(Game.id == game_id))
        game = game_result.scalar_one()
        assert game.status == GameStatus.ended


async def test_extend_phase(session_factory, phase_manager):
    game_id, room_code, phase_ids = await _create_game_with_phases(session_factory)

    await phase_manager.start_first_phase(game_id, room_code)
    phase = await phase_manager.extend_phase(game_id, room_code, extra_sec=30)

    assert phase.duration_sec == 330

    phase_manager.cleanup_game(game_id)


async def test_get_current_phase_info(session_factory, phase_manager):
    game_id, room_code, phase_ids = await _create_game_with_phases(session_factory)

    await phase_manager.start_first_phase(game_id, room_code)
    info = await phase_manager.get_current_phase_info(game_id)

    assert info is not None
    assert info["phase_id"] == phase_ids[0]
    assert info["phase_type"] == PhaseType.investigation
    assert info["duration_sec"] == 300
    assert info["remaining_sec"] <= 300

    phase_manager.cleanup_game(game_id)


async def test_get_current_phase_info_no_game(session_factory, phase_manager):
    info = await phase_manager.get_current_phase_info("nonexistent")
    assert info is None


async def test_no_phases_raises(session_factory, phase_manager):
    async with session_factory() as db:
        game = Game(
            id=str(uuid.uuid4()),
            room_code="E" + str(uuid.uuid4())[:5].upper(),
            status=GameStatus.playing,
        )
        db.add(game)
        await db.commit()

    with pytest.raises(ValueError, match="No phases found"):
        await phase_manager.start_first_phase(game.id, game.room_code)


async def test_cleanup_cancels_timer(session_factory, phase_manager):
    game_id, room_code, phase_ids = await _create_game_with_phases(session_factory)

    await phase_manager.start_first_phase(game_id, room_code)
    assert game_id in phase_manager._timers
    assert not phase_manager._timers[game_id].done()

    phase_manager.cleanup_game(game_id)
    assert game_id not in phase_manager._timers


async def test_advance_cancels_previous_timer(session_factory, phase_manager):
    game_id, room_code, phase_ids = await _create_game_with_phases(session_factory)

    await phase_manager.start_first_phase(game_id, room_code)
    first_timer = phase_manager._timers[game_id]

    await phase_manager.advance_phase(game_id, room_code)
    assert first_timer.cancelled()
    assert game_id in phase_manager._timers

    phase_manager.cleanup_game(game_id)
