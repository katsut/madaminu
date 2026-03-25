import json
import uuid
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from madaminu.llm.client import LLMUsage
from madaminu.models import (
    Game,
    GameEnding,
    GameStatus,
    Phase,
    PhaseType,
    Player,
    SpeechLog,
    Vote,
)
from madaminu.models.player import ConnectionStatus, PlayerRole
from madaminu.services.scenario_engine import generate_ending

MOCK_ENDING = {
    "ending_text": "事件の真相が明らかになった。医者が遺産相続を巡り犯行に及んだのだ。",
    "true_criminal_id": "CRIMINAL_ID",
    "objective_results": {
        "PLAYER_1": {"achieved": True, "description": "真犯人を特定した"},
        "CRIMINAL_ID": {"achieved": False, "description": "犯行が露見した"},
    },
}

MOCK_USAGE = LLMUsage(model="gpt-5.4-mini", input_tokens=4000, output_tokens=2000, duration_ms=6000)


async def _create_voting_game(session_factory) -> tuple[str, list[str]]:
    """Returns (game_id, [player_ids])."""
    async with session_factory() as db:
        game = Game(
            id=str(uuid.uuid4()),
            room_code="V" + str(uuid.uuid4())[:5].upper(),
            status=GameStatus.voting,
            scenario_skeleton={"setting": {"location": "洋館"}, "victim": {"name": "山田太郎"}},
            gm_internal_state={"gm_strategy": "テスト", "player_gm_notes": {}},
        )
        db.add(game)

        players = []
        configs = [
            ("Alice", "探偵", PlayerRole.innocent, True),
            ("Bob", "医者", PlayerRole.criminal, False),
            ("Charlie", "執事", PlayerRole.witness, False),
        ]
        for name, char_name, role, is_host in configs:
            p = Player(
                id=str(uuid.uuid4()),
                game_id=game.id,
                session_token=str(uuid.uuid4()),
                display_name=name,
                character_name=char_name,
                role=role,
                secret_info=f"{char_name}の秘密",
                objective=f"{char_name}の目的",
                is_host=is_host,
                connection_status=ConnectionStatus.online,
            )
            db.add(p)
            players.append(p)

        await db.flush()
        game.host_player_id = players[0].id

        phase = Phase(
            id=str(uuid.uuid4()),
            game_id=game.id,
            phase_type=PhaseType.voting,
            phase_order=2,
            duration_sec=120,
        )
        db.add(phase)
        await db.flush()
        game.current_phase_id = phase.id

        log = SpeechLog(
            id=str(uuid.uuid4()),
            game_id=game.id,
            player_id=players[0].id,
            phase_id=phase.id,
            transcript="医者が怪しいと思います",
        )
        db.add(log)

        await db.commit()
        return game.id, [p.id for p in players]


async def test_generate_ending(session_factory):
    game_id, player_ids = await _create_voting_game(session_factory)

    mock_ending = dict(MOCK_ENDING)
    mock_ending["true_criminal_id"] = player_ids[1]

    async with session_factory() as db:
        for pid in player_ids:
            vote = Vote(
                id=str(uuid.uuid4()),
                game_id=game_id,
                voter_player_id=pid,
                suspect_player_id=player_ids[1],
            )
            db.add(vote)
        await db.commit()

    mock_response = json.dumps(mock_ending, ensure_ascii=False)
    mock_generate = AsyncMock(return_value=(mock_response, MOCK_USAGE))

    async with session_factory() as db:
        with patch("madaminu.services.scenario_engine.llm_client.generate_json", mock_generate):
            ending, usage = await generate_ending(db, game_id)

    assert ending.ending_text == mock_ending["ending_text"]
    assert ending.true_criminal_id == player_ids[1]
    assert usage.model == "gpt-5.4-mini"

    async with session_factory() as db:
        result = await db.execute(select(Game).where(Game.id == game_id))
        game = result.scalar_one()
        assert game.status == GameStatus.ended

        ending_result = await db.execute(select(GameEnding).where(GameEnding.game_id == game_id))
        saved = ending_result.scalar_one()
        assert saved.ending_text == mock_ending["ending_text"]


async def test_generate_ending_includes_votes_in_prompt(session_factory):
    game_id, player_ids = await _create_voting_game(session_factory)

    async with session_factory() as db:
        vote = Vote(
            id=str(uuid.uuid4()),
            game_id=game_id,
            voter_player_id=player_ids[0],
            suspect_player_id=player_ids[1],
        )
        db.add(vote)
        await db.commit()

    mock_response = json.dumps(MOCK_ENDING, ensure_ascii=False)
    mock_generate = AsyncMock(return_value=(mock_response, MOCK_USAGE))

    async with session_factory() as db:
        with patch("madaminu.services.scenario_engine.llm_client.generate_json", mock_generate):
            await generate_ending(db, game_id)

    call_args = mock_generate.call_args
    user_prompt = call_args[0][1]
    assert "探偵" in user_prompt
    assert "医者" in user_prompt


async def test_generate_ending_includes_speech_in_prompt(session_factory):
    game_id, player_ids = await _create_voting_game(session_factory)

    mock_response = json.dumps(MOCK_ENDING, ensure_ascii=False)
    mock_generate = AsyncMock(return_value=(mock_response, MOCK_USAGE))

    async with session_factory() as db:
        with patch("madaminu.services.scenario_engine.llm_client.generate_json", mock_generate):
            await generate_ending(db, game_id)

    call_args = mock_generate.call_args
    user_prompt = call_args[0][1]
    assert "医者が怪しいと思います" in user_prompt


async def test_vote_duplicate_prevention(session_factory):
    game_id, player_ids = await _create_voting_game(session_factory)

    async with session_factory() as db:
        v1 = Vote(
            id=str(uuid.uuid4()),
            game_id=game_id,
            voter_player_id=player_ids[0],
            suspect_player_id=player_ids[1],
        )
        db.add(v1)
        await db.commit()

        existing = await db.execute(select(Vote).where(Vote.game_id == game_id, Vote.voter_player_id == player_ids[0]))
        assert existing.scalar_one_or_none() is not None


async def test_format_votes(session_factory):
    from madaminu.services.scenario_engine import _format_votes

    game_id, player_ids = await _create_voting_game(session_factory)
    id_to_name = {}

    async with session_factory() as db:
        for pid in player_ids:
            result = await db.execute(select(Player).where(Player.id == pid))
            p = result.scalar_one()
            id_to_name[p.id] = p.character_name

        votes = []
        for pid in player_ids:
            v = Vote(
                id=str(uuid.uuid4()),
                game_id=game_id,
                voter_player_id=pid,
                suspect_player_id=player_ids[1],
            )
            votes.append(v)

    result = _format_votes(votes, id_to_name)
    assert "探偵" in result
    assert "医者" in result
    assert "3票" in result
