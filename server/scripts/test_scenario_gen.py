"""Generate 5 test scenarios and validate map quality."""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from madaminu.llm.prompts import format_characters_for_prompt, load_template, render_template
from madaminu.services.map_validator import validate_map

from openai import AsyncOpenAI

API_KEY = os.environ.get("MADAMINU_OPENAI_API_KEY")
MODEL = "gpt-5.4-mini"

TEST_CHARACTERS = [
    {
        "character_name": "明智 小五郎",
        "character_name_kana": "あけち こごろう",
        "character_gender": "男",
        "character_age": "45",
        "character_occupation": "私立探偵",
        "character_appearance": "鋭い目つきでトレンチコートを羽織る",
        "character_personality": "論理的で冷静。観察力に優れる。",
        "character_background": "元警視庁刑事。15年前の未解決事件を追っている。",
    },
    {
        "character_name": "白鳥 麗子",
        "character_name_kana": "しらとり れいこ",
        "character_gender": "女",
        "character_age": "38",
        "character_occupation": "外科医",
        "character_appearance": "知的な美人。常に白衣。",
        "character_personality": "完璧主義者。冷徹だが患者思い。",
        "character_background": "大学病院の心臓外科チーフ。",
    },
    {
        "character_name": "田中 健二",
        "character_name_kana": "たなか けんじ",
        "character_gender": "男",
        "character_age": "63",
        "character_occupation": "喫茶店マスター",
        "character_appearance": "がっしりした体格。白髪のオールバック。",
        "character_personality": "穏やかだが洞察力が鋭い。嘘を見抜く。",
        "character_background": "元刑事。今は喫茶店を営む。",
    },
    {
        "character_name": "佐藤 美咲",
        "character_name_kana": "さとう みさき",
        "character_gender": "女",
        "character_age": "28",
        "character_occupation": "新聞記者",
        "character_appearance": "ショートカット。メモ帳を常備。",
        "character_personality": "正義感が強く行動力がある。",
        "character_background": "社会部エース記者。不正を追う。",
    },
]


async def generate_one(client, idx):
    characters_text = format_characters_for_prompt(TEST_CHARACTERS)
    system_prompt = load_template("scenario_system")
    system_prompt += "\n\nIMPORTANT: Respond with valid JSON only. No markdown, no code blocks."
    user_prompt = render_template("scenario_generate", characters=characters_text)

    print(f"\n{'='*60}")
    print(f"Scenario {idx+1}: Generating...")

    response = await client.chat.completions.create(
        model=MODEL,
        max_completion_tokens=8192,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    text = response.choices[0].message.content or ""
    finish_reason = response.choices[0].finish_reason
    tokens = response.usage.completion_tokens if response.usage else 0

    print(f"  finish_reason: {finish_reason}, tokens: {tokens}, length: {len(text)}")

    if not text.strip():
        print("  ERROR: Empty response")
        return None

    # Parse JSON
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    try:
        scenario = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"  ERROR: JSON parse failed: {e}")
        print(f"  First 200 chars: {cleaned[:200]}")
        return None

    # Check map structure
    map_data = scenario.get("map", {})
    if "areas" in map_data:
        areas = map_data["areas"]
        total_rooms = sum(len(a.get("rooms", [])) for a in areas)
        connections = map_data.get("connections", [])
        print(f"  Setting: {scenario.get('setting', {}).get('location', '?')}")
        print(f"  Areas: {len(areas)} ({', '.join(a['name'] for a in areas)})")
        print(f"  Rooms: {total_rooms}")
        print(f"  Connections: {len(connections)}")

        for conn in connections:
            print(f"    {conn['from']} --{conn.get('type', '?')}--> {conn['to']}")
    elif "locations" in map_data:
        print(f"  WARNING: Old flat format used (locations, not areas)")
        print(f"  Locations: {len(map_data['locations'])}")
    else:
        print(f"  ERROR: No map data")

    # Validate
    errors = validate_map(scenario)
    if errors:
        print(f"  VALIDATION ERRORS ({len(errors)}):")
        for e in errors:
            print(f"    - {e}")
    else:
        print(f"  VALIDATION: OK")

    # Check players
    players = scenario.get("players", [])
    print(f"  Players: {len(players)}")
    for p in players:
        role = p.get("role", "?")
        has_public = bool(p.get("public_info", "").strip())
        print(f"    {p['character_name']}: role={role}, public_info={'YES' if has_public else 'NO'}")

    return scenario


async def main():
    if not API_KEY:
        print("Set MADAMINU_OPENAI_API_KEY")
        return

    client = AsyncOpenAI(api_key=API_KEY)

    results = []
    for i in range(5):
        scenario = await generate_one(client, i)
        results.append(scenario)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    success = sum(1 for r in results if r is not None)
    print(f"Success: {success}/5")

    valid = 0
    for i, r in enumerate(results):
        if r is None:
            print(f"  Scenario {i+1}: FAILED (parse error)")
            continue
        errors = validate_map(r)
        has_areas = "areas" in r.get("map", {})
        if not errors and has_areas:
            valid += 1
            print(f"  Scenario {i+1}: VALID (hierarchical)")
        elif not errors:
            print(f"  Scenario {i+1}: VALID (flat - old format)")
        else:
            print(f"  Scenario {i+1}: INVALID ({len(errors)} errors)")

    print(f"Valid hierarchical maps: {valid}/5")


if __name__ == "__main__":
    asyncio.run(main())
