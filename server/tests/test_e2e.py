"""E2E tests: full game lifecycle through HTTP API + WebSocket.

LLM calls are mocked so tests run without external dependencies.
Uses starlette's sync TestClient for WebSocket support.
"""

import json
import os
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from madaminu.db import get_db
from madaminu.llm.client import LLMUsage
from madaminu.main import app
from madaminu.models import Base, Game, GameStatus, Phase, PhaseType, Player, Vote
from madaminu.models.player import ConnectionStatus, PlayerRole
from madaminu.services.speech_manager import SpeechManager

_ws_skip = pytest.mark.skip(reason="Sync TestClient incompatible with aiosqlite")

MOCK_SCENARIO = {
    "setting": {"location": "洋館", "era": "現代", "situation": "パーティー中に殺人事件が発生"},
    "victim": {"name": "山田太郎", "description": "洋館の主人"},
    "map": {
        "areas": [
            {
                "id": "first_floor",
                "name": "1階",
                "area_type": "indoor",
                "rooms": [
                    {"id": "study", "name": "書斎", "size": 2, "features": ["本棚", "机", "窓", "椅子", "ランプ", "絨毯"]},
                    {"id": "garden", "name": "庭園", "size": 1, "features": ["噴水", "花壇", "ベンチ"]},
                    {"id": "kitchen", "name": "厨房", "size": 1, "features": ["調理台", "冷蔵庫", "食器棚"]},
                    {"id": "dining", "name": "食堂", "size": 2, "features": ["テーブル", "シャンデリア", "窓", "食器棚", "暖炉", "絵画"]},
                ],
            },
            {
                "id": "second_floor",
                "name": "2階",
                "area_type": "indoor",
                "rooms": [
                    {"id": "master_bedroom", "name": "主寝室", "size": 2, "features": ["ベッド", "クローゼット", "鏡台", "窓", "サイドテーブル", "絵画"]},
                    {"id": "guest_room", "name": "客室", "size": 1, "features": ["ベッド", "机", "窓"]},
                    {"id": "library", "name": "図書室", "size": 1, "features": ["本棚", "机", "ソファ"]},
                    {"id": "storage", "name": "物置", "size": 1, "features": ["棚", "箱", "古い家具"]},
                ],
            },
        ],
    },
    "relationships": [
        {"player1": "探偵", "player2": "医者", "relationship": "旧友"},
    ],
    "players": [
        {
            "character_name": "探偵",
            "role": "innocent",
            "secret_info": "実は借金がある",
            "objective": "真犯人を見つける",
            "gm_notes": "借金の証拠を出す",
        },
        {
            "character_name": "医者",
            "role": "criminal",
            "secret_info": "被害者と遺産相続で揉めていた",
            "objective": "自分の犯行を隠し通す",
            "gm_notes": "遺産関連の書類を段階的に公開",
        },
        {
            "character_name": "執事",
            "role": "witness",
            "secret_info": "犯行現場を目撃した",
            "objective": "目撃したことを隠す",
            "gm_notes": "プレッシャーをかけると情報を漏らす",
        },
        {
            "character_name": "令嬢",
            "role": "related",
            "secret_info": "被害者の隠し子",
            "objective": "自分の出生の秘密を守る",
            "gm_notes": "出生証明書を調査可能",
        },
    ],
    "gm_strategy": "序盤は関係性の手がかり、中盤で動機、終盤で決定的証拠を出す",
}

MOCK_VALIDATION = {"is_valid": True, "issues": [], "summary": "問題なし"}

MOCK_INVESTIGATION = {
    "title": "血のついた手紙",
    "content": "書斎の引き出しの奥に、血痕のついた手紙が隠されていた。",
}

MOCK_PHASE_ADJUSTMENT = {
    "evidence_distribution": [],
    "gm_state_update": {"gm_strategy": "更新された戦略"},
}

MOCK_ENDING = {
    "ending_text": "事件の真相が明らかになった。医者が遺産相続を巡り犯行に及んだのだ。",
    "true_criminal_id": "PLACEHOLDER",
    "objective_results": {},
}

MOCK_USAGE = LLMUsage(model="gpt-5.4-mini", input_tokens=2000, output_tokens=1000, duration_ms=3000)
MOCK_USAGE_LIGHT = LLMUsage(model="gpt-5.4-nano", input_tokens=1000, output_tokens=500, duration_ms=1000)


async def _activate_first_phase(session_factory):
    """Set current_phase_id to the first phase (since _NoOpPhaseManager skips this)."""
    from datetime import UTC, datetime

    async with session_factory() as db:
        result = await db.execute(
            select(Game).where(Game.status == GameStatus.playing, Game.current_phase_id.is_(None))
        )
        games = result.scalars().all()
        for game in games:
            phase_result = await db.execute(
                select(Phase).where(Phase.game_id == game.id).order_by(Phase.phase_order).limit(1)
            )
            first_phase = phase_result.scalar_one_or_none()
            if first_phase:
                first_phase.started_at = datetime.now(UTC)
                game.current_phase_id = first_phase.id
        await db.commit()


async def _activate_phase_by_type(session_factory, phase_type: PhaseType):
    """Set current_phase_id to the first phase of the given type."""
    from datetime import UTC, datetime

    async with session_factory() as db:
        result = await db.execute(select(Game).where(Game.status == GameStatus.playing))
        games = result.scalars().all()
        for game in games:
            phase_result = await db.execute(
                select(Phase)
                .where(Phase.game_id == game.id, Phase.phase_type == phase_type)
                .order_by(Phase.phase_order)
                .limit(1)
            )
            phase = phase_result.scalar_one_or_none()
            if phase:
                phase.started_at = datetime.now(UTC)
                game.current_phase_id = phase.id
        await db.commit()


@pytest.fixture()
async def e2e_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture()
def e2e_session_factory(e2e_engine):
    return async_sessionmaker(e2e_engine, class_=AsyncSession, expire_on_commit=False)


class _NoOpPhaseManager:
    """No-op PhaseManager for E2E tests. Avoids session conflicts and background tasks."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory
        self._intro_ready: dict[str, set[str]] = {}

    async def start_first_phase(self, game_id, room_code):
        pass

    async def advance_phase(self, game_id, room_code):
        pass

    async def extend_phase(self, game_id, room_code, extra_sec=60):
        pass

    def cleanup_game(self, game_id):
        pass

    def set_intro_ready(self, room_code, player_id):
        if room_code not in self._intro_ready:
            self._intro_ready[room_code] = set()
        self._intro_ready[room_code].add(player_id)

    def get_intro_ready_count(self, room_code):
        return len(self._intro_ready.get(room_code, set()))

    def clear_intro_ready(self, room_code):
        self._intro_ready.pop(room_code, None)

    async def _generate_and_broadcast_ending(self, game_id, room_code):
        from madaminu.services.scenario_engine import generate_ending
        from madaminu.ws.handler import manager
        from madaminu.ws.messages import WSMessage

        async with self._session_factory() as db:
            ending, _ = await generate_ending(db, game_id)

        await manager.broadcast(
            room_code,
            WSMessage(
                type="game.ending",
                data={
                    "ending_text": ending.ending_text,
                    "true_criminal_id": ending.true_criminal_id,
                    "objective_results": ending.objective_results,
                },
            ),
        )


@pytest.fixture()
def e2e_client(e2e_session_factory):
    """TestClient with PhaseManager and SpeechManager wired up."""
    from madaminu.ws.handler import manager as ws_manager

    # Ensure clean state before setup
    app.dependency_overrides.clear()
    ws_manager._connections.clear()

    async def override_get_db():
        async with e2e_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    pm = _NoOpPhaseManager(e2e_session_factory)
    sm = SpeechManager(e2e_session_factory)
    app.state.phase_manager = pm
    app.state.speech_manager = sm
    app.state._session_factory = e2e_session_factory

    client = TestClient(app, raise_server_exceptions=False)
    yield client

    for room_code in list(sm._speakers.keys()):
        sm.cleanup_room(room_code)
    ws_manager._connections.clear()

    app.dependency_overrides.clear()
    if hasattr(app.state, "phase_manager"):
        del app.state.phase_manager
    if hasattr(app.state, "speech_manager"):
        del app.state.speech_manager
    if hasattr(app.state, "_session_factory"):
        del app.state._session_factory


@pytest.fixture()
async def async_client(e2e_session_factory):
    """Async client for HTTP-only tests."""
    from madaminu.ws.handler import manager as ws_manager

    async def override_get_db():
        async with e2e_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    pm = _NoOpPhaseManager(e2e_session_factory)
    sm = SpeechManager(e2e_session_factory)
    app.state.phase_manager = pm
    app.state.speech_manager = sm
    app.state._session_factory = e2e_session_factory

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    for room_code in list(sm._speakers.keys()):
        sm.cleanup_room(room_code)
    ws_manager._connections.clear()

    app.dependency_overrides.clear()
    if hasattr(app.state, "phase_manager"):
        del app.state.phase_manager
    if hasattr(app.state, "speech_manager"):
        del app.state.speech_manager
    if hasattr(app.state, "_session_factory"):
        del app.state._session_factory


def _mock_llm_generate(responses: list[tuple[str, LLMUsage]]):
    """Create a mock that returns different responses on successive calls."""
    mock = AsyncMock(side_effect=responses)
    return mock


async def _noop_generate_background(game_id, room_code, session_factory, phase_manager):
    """No-op replacement for _generate_scenario_background in E2E tests.

    Runs generate_scenario synchronously so DB state is set up,
    but skips image generation and WS broadcasts.
    """
    from madaminu.services.scenario_engine import generate_scenario

    async with session_factory() as db:
        await generate_scenario(db, game_id)


def _scenario_and_validation_mock():
    """Mock that handles generate_scenario + validate_scenario calls."""
    return _mock_llm_generate(
        [
            (json.dumps(MOCK_SCENARIO, ensure_ascii=False), MOCK_USAGE),
            (json.dumps(MOCK_VALIDATION, ensure_ascii=False), MOCK_USAGE_LIGHT),
        ]
    )


# ---------------------------------------------------------------------------
# Test: Full game lifecycle via HTTP API
# ---------------------------------------------------------------------------


async def test_full_game_lifecycle_http(async_client):
    """Room creation → join → characters → start game via HTTP API."""
    # 1. Create room
    resp = await async_client.post("/api/v1/rooms", json={"display_name": "Alice"})
    assert resp.status_code == 200
    room_code = resp.json()["room_code"]
    host_token = resp.json()["session_token"]
    host_id = resp.json()["player_id"]

    # 2. Join 3 more players
    tokens = {"Alice": host_token}
    player_ids = {"Alice": host_id}
    for name in ["Bob", "Charlie", "Dave"]:
        join_resp = await async_client.post(f"/api/v1/rooms/{room_code}/join", json={"display_name": name})
        assert join_resp.status_code == 200
        tokens[name] = join_resp.json()["session_token"]
        player_ids[name] = join_resp.json()["player_id"]

    # 3. Set characters
    char_map = {"Alice": "探偵", "Bob": "医者", "Charlie": "執事", "Dave": "令嬢"}
    for name, char_name in char_map.items():
        resp = await async_client.post(
            f"/api/v1/rooms/{room_code}/characters",
            json={
                "character_name": char_name,
                "character_personality": "テスト性格",
                "character_background": "テスト背景",
            },
            headers={"x-session-token": tokens[name]},
        )
        assert resp.status_code == 200

    # 4. Set all players ready
    for name in ["Bob", "Charlie", "Dave"]:
        ready_resp = await async_client.post(
            f"/api/v1/rooms/{room_code}/ready",
            headers={"x-session-token": tokens[name]},
        )
        assert ready_resp.status_code == 200

    # 5. Verify room state
    room_resp = await async_client.get(f"/api/v1/rooms/{room_code}")
    assert room_resp.status_code == 200
    room_data = room_resp.json()
    assert room_data["status"] == "waiting"
    assert len(room_data["players"]) == 4

    # 6. Start game
    mock_generate = _scenario_and_validation_mock()

    with patch("madaminu.llm.client.llm_client.generate_json", mock_generate):
        start_resp = await async_client.post(
            f"/api/v1/rooms/{room_code}/start",
            headers={"x-session-token": host_token},
        )

    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data["status"] == "generating"
    assert start_data["total_cost_usd"] >= 0


# ---------------------------------------------------------------------------
# Test: Full game flow with WebSocket (room → game → phases → vote → ending)
# ---------------------------------------------------------------------------


@_ws_skip
async def test_full_game_flow_with_websocket(e2e_client, e2e_session_factory):
    """Complete E2E: create room, start game, connect WS, advance phases, vote, get ending."""
    # --- Setup: create room + players + characters via HTTP ---
    resp = e2e_client.post("/api/v1/rooms", json={"display_name": "Alice"})
    assert resp.status_code == 200
    room_code = resp.json()["room_code"]
    host_token = resp.json()["session_token"]

    tokens = {"Alice": host_token}
    for name in ["Bob", "Charlie", "Dave"]:
        join_resp = e2e_client.post(f"/api/v1/rooms/{room_code}/join", json={"display_name": name})
        tokens[name] = join_resp.json()["session_token"]

    char_map = {"Alice": "探偵", "Bob": "医者", "Charlie": "執事", "Dave": "令嬢"}
    for name, char_name in char_map.items():
        e2e_client.post(
            f"/api/v1/rooms/{room_code}/characters",
            json={
                "character_name": char_name,
                "character_personality": "テスト性格",
                "character_background": "テスト背景",
            },
            headers={"x-session-token": tokens[name]},
        )

    for name in ["Bob", "Charlie", "Dave"]:
        e2e_client.post(f"/api/v1/rooms/{room_code}/ready", headers={"x-session-token": tokens[name]})

    # --- Start game with mocked LLM ---
    mock_generate = _scenario_and_validation_mock()
    with (
        patch("madaminu.llm.client.llm_client.generate_json", mock_generate),
        patch("madaminu.routers.game._generate_scenario_background", _noop_generate_background),
    ):
        start_resp = e2e_client.post(
            f"/api/v1/rooms/{room_code}/start",
            headers={"x-session-token": host_token},
        )
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "generating"

    await _activate_first_phase(e2e_session_factory)

    # --- Connect host via WebSocket ---
    with e2e_client.websocket_connect(f"/ws/{room_code}?token={host_token}") as ws_host:
        state = ws_host.receive_json()
        assert state["type"] == "game.state"
        assert state["data"]["status"] == "playing"
        assert state["data"]["my_secret_info"] is not None
        assert state["data"]["my_role"] is not None
        assert "current_phase" in state["data"]
        assert state["data"]["current_phase"]["phase_type"] == "planning"

        # Verify secret isolation
        for p in state["data"]["players"]:
            assert "secret_info" not in p
            assert "objective" not in p


@_ws_skip
async def test_websocket_investigation_flow(e2e_client, e2e_session_factory):
    """E2E: player investigates a location during investigation phase."""
    resp = e2e_client.post("/api/v1/rooms", json={"display_name": "Alice"})
    room_code = resp.json()["room_code"]
    host_token = resp.json()["session_token"]

    player_tokens = {"Alice": host_token}
    for name in ["Bob", "Charlie", "Dave"]:
        join_resp = e2e_client.post(f"/api/v1/rooms/{room_code}/join", json={"display_name": name})
        player_tokens[name] = join_resp.json()["session_token"]

    char_map = {"Alice": "探偵", "Bob": "医者", "Charlie": "執事", "Dave": "令嬢"}
    for name, char_name in char_map.items():
        e2e_client.post(
            f"/api/v1/rooms/{room_code}/characters",
            json={
                "character_name": char_name,
                "character_personality": "テスト性格",
                "character_background": "テスト背景",
            },
            headers={"x-session-token": player_tokens[name]},
        )

    for name in ["Bob", "Charlie", "Dave"]:
        e2e_client.post(f"/api/v1/rooms/{room_code}/ready", headers={"x-session-token": player_tokens[name]})

    mock_generate = _scenario_and_validation_mock()
    with (
        patch("madaminu.llm.client.llm_client.generate_json", mock_generate),
        patch("madaminu.routers.game._generate_scenario_background", _noop_generate_background),
    ):
        e2e_client.post(f"/api/v1/rooms/{room_code}/start", headers={"x-session-token": host_token})

    await _activate_phase_by_type(e2e_session_factory, PhaseType.investigation)

    with e2e_client.websocket_connect(f"/ws/{room_code}?token={host_token}") as ws:
        state = ws.receive_json()
        assert state["type"] == "game.state"
        assert state["data"]["current_phase"]["phase_type"] == "investigation"

        investigation_mock = AsyncMock(
            return_value=(json.dumps(MOCK_INVESTIGATION, ensure_ascii=False), MOCK_USAGE_LIGHT)
        )
        with patch("madaminu.services.scenario_engine.llm_client.generate_json", investigation_mock):
            ws.send_json({"type": "investigate", "data": {"location_id": "study"}})
            messages = _collect_messages(ws, until_type="investigate.result", max_messages=10)

        result = next((m for m in messages if m["type"] == "investigate.result"), None)
        assert result is not None
        assert result["data"]["title"] == "血のついた手紙"
        assert result["data"]["location_id"] == "study"


@_ws_skip
async def test_websocket_speech_flow(e2e_client, e2e_session_factory):
    """E2E: speech request → grant → release through WebSocket."""
    resp = e2e_client.post("/api/v1/rooms", json={"display_name": "Alice"})
    room_code = resp.json()["room_code"]
    host_token = resp.json()["session_token"]

    player_tokens = {"Alice": host_token}
    for name in ["Bob", "Charlie", "Dave"]:
        join_resp = e2e_client.post(f"/api/v1/rooms/{room_code}/join", json={"display_name": name})
        player_tokens[name] = join_resp.json()["session_token"]

    char_map = {"Alice": "探偵", "Bob": "医者", "Charlie": "執事", "Dave": "令嬢"}
    for name, char_name in char_map.items():
        e2e_client.post(
            f"/api/v1/rooms/{room_code}/characters",
            json={
                "character_name": char_name,
                "character_personality": "テスト性格",
                "character_background": "テスト背景",
            },
            headers={"x-session-token": player_tokens[name]},
        )

    for name in ["Bob", "Charlie", "Dave"]:
        e2e_client.post(f"/api/v1/rooms/{room_code}/ready", headers={"x-session-token": player_tokens[name]})

    mock_generate = _scenario_and_validation_mock()
    with (
        patch("madaminu.llm.client.llm_client.generate_json", mock_generate),
        patch("madaminu.routers.game._generate_scenario_background", _noop_generate_background),
    ):
        e2e_client.post(f"/api/v1/rooms/{room_code}/start", headers={"x-session-token": host_token})

    await _activate_first_phase(e2e_session_factory)

    with e2e_client.websocket_connect(f"/ws/{room_code}?token={host_token}") as ws:
        state = ws.receive_json()
        assert state["type"] == "game.state"

        # Request speech
        ws.send_json({"type": "speech.request"})
        messages = _collect_messages(ws, until_type="speech.granted", max_messages=10)
        assert any(m["type"] == "speech.granted" for m in messages)

        # Release speech with transcript
        ws.send_json({"type": "speech.release", "data": {"transcript": "医者が怪しいと思います"}})
        messages = _collect_messages(ws, until_type="speech.released", max_messages=10)
        assert any(m["type"] == "speech.released" for m in messages)


@_ws_skip
async def test_multiplayer_websocket_interaction(e2e_client, e2e_session_factory):
    """E2E: two players connect, one gets notified of the other."""
    resp = e2e_client.post("/api/v1/rooms", json={"display_name": "Alice"})
    room_code = resp.json()["room_code"]
    host_token = resp.json()["session_token"]

    join_resp = e2e_client.post(f"/api/v1/rooms/{room_code}/join", json={"display_name": "Bob"})
    bob_token = join_resp.json()["session_token"]

    with e2e_client.websocket_connect(f"/ws/{room_code}?token={host_token}") as ws_host:
        state = ws_host.receive_json()
        assert state["type"] == "game.state"

        with e2e_client.websocket_connect(f"/ws/{room_code}?token={bob_token}") as ws_bob:
            bob_state = ws_bob.receive_json()
            assert bob_state["type"] == "game.state"

            # Host should receive player.connected
            notification = ws_host.receive_json()
            assert notification["type"] == "player.connected"
            assert notification["data"]["display_name"] == "Bob"


@_ws_skip
async def test_voting_and_ending_flow(e2e_client, e2e_session_factory):
    """E2E: last vote triggers ending generation via WS.

    Pre-insert 2 votes in DB, then the 3rd player votes via WS to trigger ending.
    This avoids nested WS connections which cause deadlocks with sync TestClient.
    """
    async with e2e_session_factory() as db:
        game = Game(
            id=str(uuid.uuid4()),
            room_code="E" + str(uuid.uuid4())[:5].upper(),
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
                connection_status=ConnectionStatus.offline,
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

        criminal_id = players[1].id

        # Pre-insert votes from Alice and Bob
        for voter in players[:2]:
            v = Vote(
                id=str(uuid.uuid4()),
                game_id=game.id,
                voter_player_id=voter.id,
                suspect_player_id=criminal_id,
            )
            db.add(v)

        await db.commit()

        room_code = game.room_code
        charlie_token = players[2].session_token
        player_ids = [p.id for p in players]

    mock_ending = dict(MOCK_ENDING)
    mock_ending["true_criminal_id"] = criminal_id
    mock_ending["objective_results"] = {
        player_ids[0]: {"achieved": True, "description": "真犯人を特定した"},
        player_ids[1]: {"achieved": False, "description": "犯行が露見した"},
        player_ids[2]: {"achieved": True, "description": "目撃情報を守った"},
    }

    ending_mock = AsyncMock(return_value=(json.dumps(mock_ending, ensure_ascii=False), MOCK_USAGE))

    # Charlie casts the final vote via WS, triggering ending generation
    with (
        patch("madaminu.services.scenario_engine.llm_client.generate_json", ending_mock),
        e2e_client.websocket_connect(f"/ws/{room_code}?token={charlie_token}") as ws,
    ):
        state = ws.receive_json()
        assert state["type"] == "game.state"
        assert state["data"]["status"] == "voting"

        ws.send_json({"type": "vote.submit", "data": {"suspect_player_id": criminal_id}})
        messages = _collect_messages(ws, until_type="game.ending")

    assert any(m["type"] == "vote.cast" for m in messages)
    assert any(m["type"] == "vote.results" for m in messages)

    ending_msg = next(m for m in messages if m["type"] == "game.ending")
    assert ending_msg["data"]["true_criminal_id"] == criminal_id
    assert "事件の真相" in ending_msg["data"]["ending_text"]


@_ws_skip
async def test_duplicate_vote_rejected(e2e_client, e2e_session_factory):
    """E2E: duplicate vote is rejected via WebSocket."""
    async with e2e_session_factory() as db:
        game = Game(
            id=str(uuid.uuid4()),
            room_code="D" + str(uuid.uuid4())[:5].upper(),
            status=GameStatus.voting,
            scenario_skeleton={},
            gm_internal_state={},
        )
        db.add(game)

        p = Player(
            id=str(uuid.uuid4()),
            game_id=game.id,
            session_token=str(uuid.uuid4()),
            display_name="Alice",
            character_name="探偵",
            role=PlayerRole.innocent,
            is_host=True,
            connection_status=ConnectionStatus.offline,
        )
        db.add(p)

        p2 = Player(
            id=str(uuid.uuid4()),
            game_id=game.id,
            session_token=str(uuid.uuid4()),
            display_name="Bob",
            character_name="医者",
            role=PlayerRole.criminal,
            is_host=False,
            connection_status=ConnectionStatus.offline,
        )
        db.add(p2)

        await db.flush()
        game.host_player_id = p.id

        phase = Phase(
            id=str(uuid.uuid4()),
            game_id=game.id,
            phase_type=PhaseType.voting,
            phase_order=0,
            duration_sec=120,
        )
        db.add(phase)
        await db.flush()
        game.current_phase_id = phase.id
        await db.commit()

        room_code = game.room_code
        token = p.session_token
        suspect_id = p2.id

    with e2e_client.websocket_connect(f"/ws/{room_code}?token={token}") as ws:
        ws.receive_json()  # game.state

        ws.send_json({"type": "vote.submit", "data": {"suspect_player_id": suspect_id}})
        msg = ws.receive_json()
        assert msg["type"] == "vote.cast"

        ws.send_json({"type": "vote.submit", "data": {"suspect_player_id": suspect_id}})
        error_msg = ws.receive_json()
        assert error_msg["type"] == "error"
        assert "Already voted" in error_msg["data"]["message"]


@_ws_skip
async def test_non_host_cannot_advance_phase(e2e_client, e2e_session_factory):
    """E2E: non-host cannot send phase.advance."""
    resp = e2e_client.post("/api/v1/rooms", json={"display_name": "Alice"})
    room_code = resp.json()["room_code"]
    host_token = resp.json()["session_token"]

    player_tokens = {"Alice": host_token}
    for name in ["Bob", "Charlie", "Dave"]:
        join_resp = e2e_client.post(f"/api/v1/rooms/{room_code}/join", json={"display_name": name})
        player_tokens[name] = join_resp.json()["session_token"]

    char_map = {"Alice": "探偵", "Bob": "医者", "Charlie": "執事", "Dave": "令嬢"}
    for name, char_name in char_map.items():
        e2e_client.post(
            f"/api/v1/rooms/{room_code}/characters",
            json={
                "character_name": char_name,
                "character_personality": "テスト性格",
                "character_background": "テスト背景",
            },
            headers={"x-session-token": player_tokens[name]},
        )

    for name in ["Bob", "Charlie", "Dave"]:
        e2e_client.post(f"/api/v1/rooms/{room_code}/ready", headers={"x-session-token": player_tokens[name]})

    mock_generate = _scenario_and_validation_mock()
    with (
        patch("madaminu.llm.client.llm_client.generate_json", mock_generate),
        patch("madaminu.routers.game._generate_scenario_background", _noop_generate_background),
    ):
        start_resp = e2e_client.post(
            f"/api/v1/rooms/{room_code}/start",
            headers={"x-session-token": host_token},
        )
    assert start_resp.status_code == 200

    await _activate_first_phase(e2e_session_factory)

    # Bob (non-host) tries to advance phase
    with e2e_client.websocket_connect(f"/ws/{room_code}?token={player_tokens['Bob']}") as ws:
        ws.receive_json()  # game.state

        ws.send_json({"type": "phase.advance"})
        messages = _collect_messages(ws, until_type="error", max_messages=10)
        error_msg = next((m for m in messages if m["type"] == "error"), None)
        assert error_msg is not None
        assert "host" in error_msg["data"]["message"].lower()


async def test_room_state_after_game_start(async_client, e2e_session_factory):
    """E2E: after game starts, room status changes and players have roles assigned."""
    resp = await async_client.post("/api/v1/rooms", json={"display_name": "Alice"})
    room_code = resp.json()["room_code"]
    host_token = resp.json()["session_token"]

    player_tokens = {"Alice": host_token}
    for name in ["Bob", "Charlie", "Dave"]:
        join_resp = await async_client.post(f"/api/v1/rooms/{room_code}/join", json={"display_name": name})
        player_tokens[name] = join_resp.json()["session_token"]

    char_map = {"Alice": "探偵", "Bob": "医者", "Charlie": "執事", "Dave": "令嬢"}
    for name, char_name in char_map.items():
        await async_client.post(
            f"/api/v1/rooms/{room_code}/characters",
            json={
                "character_name": char_name,
                "character_personality": "テスト性格",
                "character_background": "テスト背景",
            },
            headers={"x-session-token": player_tokens[name]},
        )

    for name in ["Bob", "Charlie", "Dave"]:
        await async_client.post(f"/api/v1/rooms/{room_code}/ready", headers={"x-session-token": player_tokens[name]})

    import asyncio

    mock_generate = _scenario_and_validation_mock()
    mock_images = AsyncMock()

    with (
        patch("madaminu.llm.client.llm_client.generate_json", mock_generate),
        patch("madaminu.routers.game._generate_images", mock_images),
    ):
        start_resp = await async_client.post(
            f"/api/v1/rooms/{room_code}/start",
            headers={"x-session-token": host_token},
        )
        assert start_resp.status_code == 200

        # Give background task time to complete
        await asyncio.sleep(0.5)

    await _activate_first_phase(e2e_session_factory)

    # Verify DB state: game is playing, phases exist, players have roles
    async with e2e_session_factory() as db:
        result = await db.execute(select(Game).where(Game.room_code == room_code))
        game = result.scalar_one()
        assert game.status == GameStatus.playing
        assert game.scenario_skeleton is not None
        assert game.current_phase_id is not None

        phases_result = await db.execute(select(Phase).where(Phase.game_id == game.id).order_by(Phase.phase_order))
        phases = phases_result.scalars().all()
        # initial + opening + 3 turns * (discussion + planning + investigation) + voting = 12
        assert len(phases) == 12
        assert phases[0].phase_type == PhaseType.initial
        assert phases[1].phase_type == PhaseType.opening
        assert phases[2].phase_type == PhaseType.discussion
        assert phases[3].phase_type == PhaseType.planning
        assert phases[4].phase_type == PhaseType.investigation
        assert phases[11].phase_type == PhaseType.voting

        players_result = await db.execute(select(Player).where(Player.game_id == game.id))
        players = players_result.scalars().all()
        roles = {p.character_name: p.role for p in players}
        assert roles["医者"] == PlayerRole.criminal
        assert roles["執事"] == PlayerRole.witness
        assert all(p.secret_info is not None for p in players)
        assert all(p.objective is not None for p in players)


def _collect_messages(ws, until_type: str, max_messages: int = 30) -> list[dict]:
    """Collect WebSocket messages until a specific type is received."""
    messages = []
    for _ in range(max_messages):
        try:
            msg = ws.receive_json()
            messages.append(msg)
            if msg["type"] == until_type:
                break
        except Exception:
            break
    return messages
