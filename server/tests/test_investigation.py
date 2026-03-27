import json
import uuid
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from madaminu.llm.client import LLMUsage
from madaminu.models import Evidence, EvidenceSource, Game, GameStatus, Phase, PhaseType, Player
from madaminu.models.player import ConnectionStatus
from madaminu.services.scenario_engine import investigate_location

MOCK_INVESTIGATION_RESULT = {
    "title": "血のついた手紙",
    "content": "書斎の引き出しの奥に、血痕のついた手紙が隠されていた。宛名は判読できない。",
}

MOCK_USAGE = LLMUsage(model="gpt-5.4-nano", input_tokens=1500, output_tokens=500, duration_ms=1000)

INVESTIGATION_LOCATIONS = [
    {"id": "study", "name": "書斎", "description": "被害者の書斎"},
    {"id": "garden", "name": "庭園", "description": "洋館の庭"},
]


async def _create_investigation_game(session_factory) -> tuple[str, str, str]:
    """Returns (game_id, phase_id, player_id)."""
    async with session_factory() as db:
        game = Game(
            id=str(uuid.uuid4()),
            room_code="I" + str(uuid.uuid4())[:5].upper(),
            status=GameStatus.playing,
            scenario_skeleton={"setting": {"location": "洋館"}, "victim": {"name": "山田太郎"}},
            gm_internal_state={"gm_strategy": "テスト", "player_gm_notes": {}},
        )
        db.add(game)

        p1 = Player(
            id=str(uuid.uuid4()),
            game_id=game.id,
            session_token=str(uuid.uuid4()),
            display_name="Alice",
            character_name="探偵",
            role="innocent",
            secret_info="借金がある",
            objective="真犯人を見つける",
            is_host=True,
            connection_status=ConnectionStatus.online,
        )
        db.add(p1)
        await db.flush()

        game.host_player_id = p1.id

        phase = Phase(
            id=str(uuid.uuid4()),
            game_id=game.id,
            phase_type=PhaseType.investigation,
            phase_order=0,
            duration_sec=300,
            investigation_locations=INVESTIGATION_LOCATIONS,
        )
        db.add(phase)
        await db.flush()

        game.current_phase_id = phase.id
        await db.commit()
        return game.id, phase.id, p1.id


async def test_investigate_location_success(session_factory):
    game_id, phase_id, player_id = await _create_investigation_game(session_factory)

    mock_response = json.dumps(MOCK_INVESTIGATION_RESULT, ensure_ascii=False)
    mock_generate = AsyncMock(return_value=(mock_response, MOCK_USAGE))

    async with session_factory() as db:
        with patch("madaminu.services.scenario_engine.llm_client.generate_json", mock_generate):
            discovery, usage = await investigate_location(db, game_id, player_id, "study")

    assert discovery is not None
    assert discovery["title"] == "血のついた手紙"
    assert usage.model == "gpt-5.4-nano"


async def test_investigate_invalid_location(session_factory):
    game_id, phase_id, player_id = await _create_investigation_game(session_factory)

    async with session_factory() as db:
        evidence, usage = await investigate_location(db, game_id, player_id, "nonexistent")

    assert evidence is None
    assert usage is None


async def test_investigate_multiple_features(session_factory):
    game_id, phase_id, player_id = await _create_investigation_game(session_factory)

    mock_response = json.dumps(MOCK_INVESTIGATION_RESULT, ensure_ascii=False)
    mock_generate = AsyncMock(return_value=(mock_response, MOCK_USAGE))

    async with session_factory() as db:
        with patch("madaminu.services.scenario_engine.llm_client.generate_json", mock_generate):
            d1, _ = await investigate_location(db, game_id, player_id, "study", "本棚")
            d2, _ = await investigate_location(db, game_id, player_id, "study", "机")

    assert d1 is not None
    assert d2 is not None


async def test_investigate_wrong_phase_type(session_factory):
    async with session_factory() as db:
        game = Game(
            id=str(uuid.uuid4()),
            room_code="D" + str(uuid.uuid4())[:5].upper(),
            status=GameStatus.playing,
            scenario_skeleton={},
            gm_internal_state={},
        )
        db.add(game)

        p = Player(
            id=str(uuid.uuid4()),
            game_id=game.id,
            session_token=str(uuid.uuid4()),
            display_name="Alice",
            is_host=True,
            connection_status=ConnectionStatus.online,
        )
        db.add(p)

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
        game.host_player_id = p.id
        await db.commit()

        evidence, usage = await investigate_location(db, game.id, p.id, "study")

    assert evidence is None


async def test_keep_evidence_saves_to_db(session_factory):
    from madaminu.services.scenario_engine import keep_evidence

    game_id, phase_id, player_id = await _create_investigation_game(session_factory)

    discovery = {"id": str(uuid.uuid4()), "title": "血のついた手紙", "content": "手紙の内容"}

    async with session_factory() as db:
        evidence = await keep_evidence(db, game_id, player_id, discovery)

    assert evidence.title == "血のついた手紙"
    assert evidence.source == EvidenceSource.investigation

    async with session_factory() as db:
        result = await db.execute(select(Evidence).where(Evidence.game_id == game_id, Evidence.player_id == player_id))
        evidences = result.scalars().all()
        assert len(evidences) == 1


async def test_investigate_uses_haiku_model(session_factory):
    game_id, phase_id, player_id = await _create_investigation_game(session_factory)

    mock_response = json.dumps(MOCK_INVESTIGATION_RESULT, ensure_ascii=False)
    mock_generate = AsyncMock(return_value=(mock_response, MOCK_USAGE))

    async with session_factory() as db:
        with patch("madaminu.services.scenario_engine.llm_client.generate_json", mock_generate):
            await investigate_location(db, game_id, player_id, "study")

    call_kwargs = mock_generate.call_args
    assert call_kwargs[1]["model"] == "gpt-5.4-nano"
