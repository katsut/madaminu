import json
from unittest.mock import AsyncMock, patch

from madaminu.llm.client import LLMUsage
from madaminu.services.scenario_engine import _parse_scenario_json

MOCK_SCENARIO = {
    "setting": {"location": "洋館", "era": "現代", "situation": "パーティー中に殺人事件が発生"},
    "victim": {"name": "山田太郎", "description": "洋館の主人"},
    "relationships": [
        {"player1": "探偵", "player2": "医者", "relationship": "旧友"},
    ],
    "players": [
        {
            "character_name": "探偵",
            "role": "innocent",
            "secret_info": "実は借金がある",
            "objective": "真犯人を見つける",
            "gm_notes": "借金の証拠を調査フェーズで出す",
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
            "gm_notes": "出生証明書を調査可能な場所に配置",
        },
    ],
    "phases": [
        {
            "phase_type": "investigation",
            "duration_sec": 300,
            "description": "調査フェーズ",
            "investigation_locations": [
                {"id": "study", "name": "書斎", "description": "被害者の書斎"},
                {"id": "garden", "name": "庭園", "description": "洋館の庭"},
            ],
        },
        {"phase_type": "discussion", "duration_sec": 300, "description": "議論フェーズ"},
        {"phase_type": "voting", "duration_sec": 120, "description": "投票フェーズ"},
    ],
    "gm_strategy": "序盤は関係性の手がかり、中盤で動機、終盤で決定的証拠を出す",
}

MOCK_VALIDATION = {"is_valid": True, "issues": [], "summary": "問題なし"}

MOCK_USAGE = LLMUsage(model="claude-sonnet-4-20250514", input_tokens=2000, output_tokens=1500, duration_ms=3000)


def test_parse_scenario_json():
    raw = json.dumps(MOCK_SCENARIO, ensure_ascii=False)
    result = _parse_scenario_json(raw)
    assert result["setting"]["location"] == "洋館"
    assert len(result["players"]) == 4


def test_parse_scenario_json_with_markdown():
    raw = "```json\n" + json.dumps(MOCK_SCENARIO, ensure_ascii=False) + "\n```"
    result = _parse_scenario_json(raw)
    assert result["setting"]["location"] == "洋館"


async def test_start_game_endpoint(client, test_session):
    room_resp = await client.post("/api/v1/rooms", json={"display_name": "Alice"})
    room_code = room_resp.json()["room_code"]
    host_token = room_resp.json()["session_token"]

    names = ["Bob", "Charlie", "Dave"]
    tokens = [host_token]
    for name in names:
        join_resp = await client.post(f"/api/v1/rooms/{room_code}/join", json={"display_name": name})
        tokens.append(join_resp.json()["session_token"])

    char_names = ["探偵", "医者", "執事", "令嬢"]
    for token, char_name in zip(tokens, char_names, strict=True):
        await client.post(
            f"/api/v1/rooms/{room_code}/characters",
            json={
                "character_name": char_name,
                "character_personality": "テスト性格",
                "character_background": "テスト背景",
            },
            headers={"x-session-token": token},
        )

    mock_generate = AsyncMock(return_value=(json.dumps(MOCK_SCENARIO, ensure_ascii=False), MOCK_USAGE))

    with patch("madaminu.llm.client.llm_client.generate_json", mock_generate):
        resp = await client.post(
            f"/api/v1/rooms/{room_code}/start",
            headers={"x-session-token": host_token},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "playing"
    assert "scenario_setting" in data
    assert data["total_cost_usd"] >= 0


async def test_start_game_not_host(client, test_session):
    room_resp = await client.post("/api/v1/rooms", json={"display_name": "Alice"})
    room_code = room_resp.json()["room_code"]

    join_resp = await client.post(f"/api/v1/rooms/{room_code}/join", json={"display_name": "Bob"})
    bob_token = join_resp.json()["session_token"]

    resp = await client.post(f"/api/v1/rooms/{room_code}/start", headers={"x-session-token": bob_token})
    assert resp.status_code == 403


async def test_start_game_not_enough_characters(client, test_session):
    room_resp = await client.post("/api/v1/rooms", json={"display_name": "Alice"})
    room_code = room_resp.json()["room_code"]
    host_token = room_resp.json()["session_token"]

    resp = await client.post(f"/api/v1/rooms/{room_code}/start", headers={"x-session-token": host_token})
    assert resp.status_code == 400
    assert "4" in resp.json()["detail"]
