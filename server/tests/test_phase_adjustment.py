import json
import uuid
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from madaminu.llm.client import LLMUsage
from madaminu.models import (
    Evidence,
    EvidenceSource,
    Game,
    GameStatus,
    Phase,
    PhaseType,
    Player,
    SpeechLog,
)
from madaminu.models.player import ConnectionStatus
from madaminu.services.scenario_engine import adjust_phase

MOCK_ADJUSTMENT = {
    "analysis": {
        "key_developments": "探偵が書斎の手がかりについて言及。医者は沈黙を保っている。",
        "truth_proximity": "low",
        "stagnation_detected": False,
    },
    "evidence_distribution": [
        {
            "target_player_id": "PLAYER_1_ID",
            "title": "血痕のついたハンカチ",
            "content": "書斎の引き出しから見つかった。イニシャルが刺繍されている。",
            "reason": "真相への手がかりを提供",
        }
    ],
    "gm_state_update": {
        "gm_strategy": "次フェーズでは医者へのプレッシャーを強める",
        "player_gm_notes": {"探偵": "真相に近づいている。ミスリードの手がかりを検討"},
    },
    "next_phase_guidance": "医者の沈黙を他プレイヤーに気づかせる情報を投入",
}

MOCK_USAGE = LLMUsage(model="claude-sonnet-4-20250514", input_tokens=3000, output_tokens=2000, duration_ms=5000)


async def _create_game_for_adjustment(session_factory) -> tuple[str, str, str]:
    """Returns (game_id, phase_id, player1_id)."""
    async with session_factory() as db:
        game = Game(
            id=str(uuid.uuid4()),
            room_code="A" + str(uuid.uuid4())[:5].upper(),
            status=GameStatus.playing,
            scenario_skeleton={"setting": {"location": "洋館"}, "victim": {"name": "山田太郎"}},
            gm_internal_state={"gm_strategy": "序盤は関係性の手がかりを出す", "player_gm_notes": {}},
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
        p2 = Player(
            id=str(uuid.uuid4()),
            game_id=game.id,
            session_token=str(uuid.uuid4()),
            display_name="Bob",
            character_name="医者",
            role="criminal",
            secret_info="遺産相続で揉めていた",
            objective="犯行を隠す",
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
            phase_type=PhaseType.investigation,
            phase_order=0,
            duration_sec=300,
        )
        db.add(phase)
        await db.flush()

        game.current_phase_id = phase.id

        log1 = SpeechLog(
            id=str(uuid.uuid4()),
            game_id=game.id,
            player_id=p1.id,
            phase_id=phase.id,
            transcript="書斎で何か見つけました",
        )
        log2 = SpeechLog(
            id=str(uuid.uuid4()),
            game_id=game.id,
            player_id=p2.id,
            phase_id=phase.id,
            transcript="私は何も知りません",
        )
        db.add(log1)
        db.add(log2)

        await db.commit()
        return game.id, phase.id, p1.id


async def test_adjust_phase_updates_gm_state(session_factory):
    game_id, phase_id, p1_id = await _create_game_for_adjustment(session_factory)

    mock_response = json.dumps(MOCK_ADJUSTMENT, ensure_ascii=False)
    mock_generate = AsyncMock(return_value=(mock_response, MOCK_USAGE))

    async with session_factory() as db:
        with patch("madaminu.services.scenario_engine.llm_client.generate_json", mock_generate):
            adjustment, usage = await adjust_phase(db, game_id, phase_id)

    assert adjustment["analysis"]["truth_proximity"] == "low"
    assert usage.model == "claude-sonnet-4-20250514"

    async with session_factory() as db:
        result = await db.execute(select(Game).where(Game.id == game_id))
        game = result.scalar_one()
        assert game.gm_internal_state["gm_strategy"] == "次フェーズでは医者へのプレッシャーを強める"
        assert "探偵" in game.gm_internal_state["player_gm_notes"]


async def test_adjust_phase_distributes_evidence(session_factory):
    game_id, phase_id, p1_id = await _create_game_for_adjustment(session_factory)

    adj = dict(MOCK_ADJUSTMENT)
    adj["evidence_distribution"] = [
        {
            "target_player_id": p1_id,
            "title": "血痕のついたハンカチ",
            "content": "イニシャルが刺繍されている",
            "reason": "手がかり",
        }
    ]

    mock_response = json.dumps(adj, ensure_ascii=False)
    mock_generate = AsyncMock(return_value=(mock_response, MOCK_USAGE))

    async with session_factory() as db:
        with patch("madaminu.services.scenario_engine.llm_client.generate_json", mock_generate):
            await adjust_phase(db, game_id, phase_id)

    async with session_factory() as db:
        result = await db.execute(select(Evidence).where(Evidence.player_id == p1_id))
        evidence = result.scalar_one()
        assert evidence.title == "血痕のついたハンカチ"
        assert evidence.source == EvidenceSource.gm_push


async def test_adjust_phase_no_evidence(session_factory):
    game_id, phase_id, p1_id = await _create_game_for_adjustment(session_factory)

    adj = dict(MOCK_ADJUSTMENT)
    adj["evidence_distribution"] = []

    mock_response = json.dumps(adj, ensure_ascii=False)
    mock_generate = AsyncMock(return_value=(mock_response, MOCK_USAGE))

    async with session_factory() as db:
        with patch("madaminu.services.scenario_engine.llm_client.generate_json", mock_generate):
            adjustment, _ = await adjust_phase(db, game_id, phase_id)

    assert adjustment["evidence_distribution"] == []

    async with session_factory() as db:
        result = await db.execute(select(Evidence).where(Evidence.game_id == game_id))
        evidences = result.scalars().all()
        assert len(evidences) == 0


async def test_adjust_phase_invalid_player_id_skipped(session_factory):
    game_id, phase_id, _ = await _create_game_for_adjustment(session_factory)

    adj = dict(MOCK_ADJUSTMENT)
    adj["evidence_distribution"] = [
        {
            "target_player_id": "nonexistent-player-id",
            "title": "テスト",
            "content": "テスト内容",
            "reason": "テスト",
        }
    ]

    mock_response = json.dumps(adj, ensure_ascii=False)
    mock_generate = AsyncMock(return_value=(mock_response, MOCK_USAGE))

    async with session_factory() as db:
        with patch("madaminu.services.scenario_engine.llm_client.generate_json", mock_generate):
            await adjust_phase(db, game_id, phase_id)

    async with session_factory() as db:
        result = await db.execute(select(Evidence).where(Evidence.game_id == game_id))
        evidences = result.scalars().all()
        assert len(evidences) == 0


async def test_adjust_phase_speech_logs_included(session_factory):
    game_id, phase_id, _ = await _create_game_for_adjustment(session_factory)

    mock_response = json.dumps(MOCK_ADJUSTMENT, ensure_ascii=False)
    mock_generate = AsyncMock(return_value=(mock_response, MOCK_USAGE))

    async with session_factory() as db:
        with patch("madaminu.services.scenario_engine.llm_client.generate_json", mock_generate):
            await adjust_phase(db, game_id, phase_id)

    call_args = mock_generate.call_args
    user_prompt = call_args[0][1]
    assert "書斎で何か見つけました" in user_prompt
    assert "私は何も知りません" in user_prompt
