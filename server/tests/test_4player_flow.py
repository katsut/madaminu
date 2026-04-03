"""Full 4-player game flow test via HTTP API.

Tests the complete lifecycle:
  room creation → join → character creation → ready → game start →
  game state → phase advance → investigation → discussion → voting → ending
"""

import json
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from madaminu.db import get_db
from madaminu.llm.client import LLMUsage
from madaminu.main import app
from madaminu.models import (
    Base,
    Evidence,
    Game,
    GameStatus,
    Phase,
    PhaseType,
    Player,
)
from madaminu.services.phase_manager import PhaseManager
from madaminu.services.speech_manager import SpeechManager

MOCK_USAGE = LLMUsage(model="gpt-5.4-mini", input_tokens=100, output_tokens=50, duration_ms=500)

MOCK_SCENARIO = {
    "setting": {"location": "洋館", "era": "現代", "situation": "夕食会で殺人事件が発生"},
    "victim": {"name": "山田太郎", "description": "洋館の主人", "crime_scene_room_id": "study"},
    "map": {
        "areas": [
            {
                "id": "first_floor",
                "name": "1階",
                "area_type": "indoor",
                "floor_order": 0,
                "rooms": [
                    {
                        "id": "study",
                        "name": "書斎",
                        "size": 2,
                        "features": ["本棚", "机", "窓", "椅子", "ランプ", "絨毯"],
                    },
                    {"id": "kitchen", "name": "厨房", "size": 1, "features": ["調理台", "冷蔵庫", "食器棚"]},
                    {
                        "id": "dining",
                        "name": "食堂",
                        "size": 2,
                        "features": ["テーブル", "シャンデリア", "窓", "食器棚", "暖炉", "絵画"],
                    },
                    {
                        "id": "living",
                        "name": "リビング",
                        "size": 2,
                        "features": ["ソファ", "暖炉", "棚", "窓", "テレビ", "絵画"],
                    },
                ],
            },
        ],
    },
    "relationships": [{"player1": "探偵", "player2": "医者", "relationship": "旧友"}],
    "players": [
        {
            "character_name": "探偵",
            "role": "innocent",
            "public_info": "被害者に招待された探偵。",
            "secret_info": "実は借金がある",
            "objective": "真犯人を見つける",
            "alibi_room_id": "living",
            "personal_room_id": None,
            "initial_evidence": {"title": "破れたメモ", "content": "食堂で破れたメモを拾った"},
            "initial_alibi": {
                "title": "リビングにいた",
                "content": "事件当時リビングで医者と話していた",
                "partner": "医者",
                "room_id": "living",
            },
            "gm_notes": "序盤に動機のヒントを出す",
        },
        {
            "character_name": "医者",
            "role": "criminal",
            "public_info": "被害者のかかりつけ医。",
            "secret_info": "被害者と遺産相続で揉めていた",
            "objective": "自分の犯行を隠し通す",
            "alibi_room_id": "living",
            "personal_room_id": None,
            "initial_evidence": {"title": "薬瓶", "content": "ポケットに小さな薬瓶がある"},
            "initial_alibi": {
                "title": "リビングにいた",
                "content": "事件当時リビングで探偵と話していた",
                "partner": "探偵",
                "room_id": "living",
            },
            "gm_notes": "遺産関連の書類を出す",
        },
        {
            "character_name": "執事",
            "role": "witness",
            "public_info": "長年仕えた執事。",
            "secret_info": "犯行現場を目撃した",
            "objective": "目撃したことを隠す",
            "alibi_room_id": "kitchen",
            "personal_room_id": None,
            "initial_evidence": {"title": "汚れた手袋", "content": "厨房で血のついた手袋を見つけた"},
            "initial_alibi": {
                "title": "厨房にいた",
                "content": "事件当時厨房で令嬢と食器を洗っていた",
                "partner": "令嬢",
                "room_id": "kitchen",
            },
            "gm_notes": "プレッシャーをかけると漏らす",
        },
        {
            "character_name": "令嬢",
            "role": "related",
            "public_info": "被害者の姪。",
            "secret_info": "被害者の隠し子",
            "objective": "自分の出生の秘密を守る",
            "alibi_room_id": "kitchen",
            "personal_room_id": None,
            "initial_evidence": {"title": "古い写真", "content": "自分の幼い頃と被害者が写った写真"},
            "initial_alibi": {
                "title": "厨房にいた",
                "content": "事件当時厨房で執事と食器を洗っていた",
                "partner": "執事",
                "room_id": "kitchen",
            },
            "gm_notes": "出生証明書が調査可能",
        },
    ],
    "gm_strategy": "序盤は関係性、中盤で動機、終盤で決定的証拠",
}

MOCK_INVESTIGATION = {"title": "血痕のついた手紙", "content": "机の引き出しから血痕のついた手紙が見つかった。"}
MOCK_ADJUSTMENT = {"evidence_distribution": [], "gm_state_update": {"gm_strategy": "更新"}}
MOCK_ENDING = {
    "ending_text": "医者が犯人だった。遺産相続を巡り犯行に及んだ。",
    "true_criminal_id": "PLACEHOLDER",
    "objective_results": {},
}


def _mock_generate_json():
    """Create a mock that returns different responses based on prompt content."""
    call_count = {"n": 0}

    async def mock_fn(system_prompt, user_prompt, model=None, max_tokens=None):
        call_count["n"] += 1
        if "エンディング" in user_prompt or "ending" in user_prompt.lower():
            return json.dumps(MOCK_ENDING, ensure_ascii=False), MOCK_USAGE
        if "調査リクエスト" in user_prompt or "investigation" in user_prompt.lower():
            return json.dumps(MOCK_INVESTIGATION, ensure_ascii=False), MOCK_USAGE
        if "フェーズ調整" in user_prompt or "adjustment" in user_prompt.lower():
            return json.dumps(MOCK_ADJUSTMENT, ensure_ascii=False), MOCK_USAGE
        # Default: scenario generation
        return json.dumps(MOCK_SCENARIO, ensure_ascii=False), MOCK_USAGE

    return mock_fn


@pytest.fixture()
async def client():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with sf() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.phase_manager = PhaseManager(sf)
    app.state.speech_manager = SpeechManager(sf)
    app.state._session_factory = sf

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, sf

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.skip(reason="Requires v3 test rewrite (uses old PhaseManager)")
async def test_full_4player_game(client):
    """Complete 4-player game: create → join → characters → ready → start → state → advance through all phases → vote → ending."""
    ac, sf = client

    # === 1. Create room ===
    resp = await ac.post("/api/v1/rooms", json={"display_name": "Alice", "room_name": "テストルーム"})
    assert resp.status_code == 200
    room_code = resp.json()["room_code"]
    tokens = {"Alice": resp.json()["session_token"]}
    player_ids = {"Alice": resp.json()["player_id"]}

    # === 2. Join 3 players ===
    for name in ["Bob", "Charlie", "Dave"]:
        r = await ac.post(f"/api/v1/rooms/{room_code}/join", json={"display_name": name})
        assert r.status_code == 200
        tokens[name] = r.json()["session_token"]
        player_ids[name] = r.json()["player_id"]

    # === 3. Verify room ===
    room = await ac.get(f"/api/v1/rooms/{room_code}")
    assert room.status_code == 200
    assert room.json()["room_name"] == "テストルーム"
    assert len(room.json()["players"]) == 4

    # === 4. Create characters ===
    char_map = {"Alice": "探偵", "Bob": "医者", "Charlie": "執事", "Dave": "令嬢"}
    for name, char_name in char_map.items():
        r = await ac.post(
            f"/api/v1/rooms/{room_code}/characters",
            json={
                "character_name": char_name,
                "character_personality": "テスト性格",
                "character_background": "テスト背景",
            },
            headers={"x-session-token": tokens[name]},
        )
        assert r.status_code == 200

    # === 5. Ready ===
    for name in ["Bob", "Charlie", "Dave"]:
        r = await ac.post(f"/api/v1/rooms/{room_code}/ready", headers={"x-session-token": tokens[name]})
        assert r.status_code == 200
        assert r.json()["is_ready"] is True

    # === 6. Start game ===
    # Patch background task to run synchronously within the test session
    from madaminu.services.scenario_engine import generate_scenario

    mock = _mock_generate_json()
    with patch("madaminu.llm.client.llm_client.generate_json", mock):
        # Run scenario generation synchronously
        async with sf() as db:
            game_result = await db.execute(select(Game).where(Game.room_code == room_code))
            game_obj = game_result.scalar_one()
            # Mark as generating first
            game_obj.status = GameStatus.generating
            await db.commit()

            scenario, usages = await generate_scenario(db, game_obj.id)

            # Start first phase
            pm = app.state.phase_manager
            await pm.start_first_phase(game_obj.id, room_code)

    # === 7. Verify game state ===
    state = await ac.get(f"/api/v1/rooms/{room_code}/state", headers={"x-session-token": tokens["Alice"]})
    assert state.status_code == 200
    state_data = state.json()
    assert state_data["status"] == "playing"
    assert state_data["my_role"] is not None
    assert state_data["my_secret_info"] is not None

    # Each player gets their own state
    for name in ["Bob", "Charlie", "Dave"]:
        s = await ac.get(f"/api/v1/rooms/{room_code}/state", headers={"x-session-token": tokens[name]})
        assert s.status_code == 200
        assert s.json()["status"] == "playing"

    # === 8. Verify phases were created ===
    async with sf() as db:
        game_result = await db.execute(select(Game).where(Game.room_code == room_code))
        game = game_result.scalar_one()
        phase_result = await db.execute(select(Phase).where(Phase.game_id == game.id).order_by(Phase.phase_order))
        phases = phase_result.scalars().all()

    phase_types = [p.phase_type for p in phases]
    assert PhaseType.initial in phase_types
    assert PhaseType.opening in phase_types
    assert PhaseType.planning in phase_types
    assert PhaseType.investigation in phase_types
    assert PhaseType.discussion in phase_types
    assert PhaseType.voting in phase_types

    # opening should have duration > 0
    opening = next(p for p in phases if p.phase_type == PhaseType.opening)
    assert opening.duration_sec > 0

    # === 9. Verify map was built with backbone ===
    map_data = game.scenario_skeleton.get("map", {})
    connections = map_data.get("connections", [])
    assert len(connections) > 0, "Map should have auto-generated connections"

    areas = map_data.get("areas", [])
    for area in areas:
        if area.get("area_type") == "indoor":
            room_types = {r.get("room_type") for r in area.get("rooms", [])}
            assert "entrance" in room_types, f"Indoor area {area['name']} should have entrance"
            assert "corridor" in room_types, f"Indoor area {area['name']} should have corridor"

    # === 10. Verify route_text was generated ===
    route_text = game.scenario_skeleton.get("route_text", "")
    assert "動線" in route_text or "1階" in route_text

    # === 11. Verify initial evidence was distributed ===
    async with sf() as db:
        ev_result = await db.execute(select(Evidence).where(Evidence.game_id == game.id))
        evidences = ev_result.scalars().all()

    assert len(evidences) >= 4, f"Expected >= 4 initial evidence/alibis, got {len(evidences)}"

    # === 12. Verify each player has secret_info and objective ===
    async with sf() as db:
        players_result = await db.execute(select(Player).where(Player.game_id == game.id))
        players = players_result.scalars().all()

    for p in players:
        if p.character_name:
            assert p.secret_info is not None, f"{p.character_name} has no secret_info"
            assert p.objective is not None, f"{p.character_name} has no objective"
            assert p.role is not None, f"{p.character_name} has no role"

    # Exactly one criminal
    criminals = [p for p in players if p.role and p.role.value == "criminal"]
    assert len(criminals) == 1, f"Expected 1 criminal, got {len(criminals)}"

    # === 13. Verify debug endpoint (host only) ===
    debug = await ac.get(f"/api/v1/rooms/{room_code}/debug", headers={"x-session-token": tokens["Alice"]})
    assert debug.status_code == 200
    assert len(debug.json()["players"]) >= 4

    # Non-host cannot access debug
    debug2 = await ac.get(f"/api/v1/rooms/{room_code}/debug", headers={"x-session-token": tokens["Bob"]})
    assert debug2.status_code == 403

    # === 14. Verify map SVG endpoint ===
    map_resp = await ac.get(f"/api/v1/images/game/{room_code}/map")
    assert map_resp.status_code == 200
    assert "<svg" in map_resp.text

    # Map with highlight
    map_hl = await ac.get(f"/api/v1/images/game/{room_code}/map?highlight=study")
    assert map_hl.status_code == 200
    assert "glow" in map_hl.text


async def test_rejoin_during_game(client):
    """Player can rejoin a running game via device_id."""
    ac, sf = client

    resp = await ac.post(
        "/api/v1/rooms",
        json={"display_name": "Host"},
        headers={"x-device-id": "device-host"},
    )
    room_code = resp.json()["room_code"]
    host_token = resp.json()["session_token"]
    host_id = resp.json()["player_id"]

    for name, device in [("P2", "dev-2"), ("P3", "dev-3"), ("P4", "dev-4")]:
        await ac.post(f"/api/v1/rooms/{room_code}/join", json={"display_name": name}, headers={"x-device-id": device})

    # Create characters and ready
    room = await ac.get(f"/api/v1/rooms/{room_code}")
    for _p in room.json()["players"]:
        # Need session token - get from join response or mine/list
        pass

    # Just test rejoin returns same player
    rejoin = await ac.post(
        f"/api/v1/rooms/{room_code}/join",
        json={"display_name": "Host Rejoined"},
        headers={"x-device-id": "device-host"},
    )
    assert rejoin.status_code == 200
    assert rejoin.json()["player_id"] == host_id
    assert rejoin.json()["session_token"] != host_token


async def test_room_list_with_names(client):
    """Room names appear in room list."""
    ac, sf = client

    await ac.post("/api/v1/rooms", json={"display_name": "A", "room_name": "金曜ミステリー"})
    await ac.post("/api/v1/rooms", json={"display_name": "B", "room_name": None})
    await ac.post("/api/v1/rooms", json={"display_name": "C"})

    rooms = await ac.get("/api/v1/rooms")
    assert rooms.status_code == 200
    names = [r.get("room_name") for r in rooms.json()]
    assert "金曜ミステリー" in names
    assert None in names
