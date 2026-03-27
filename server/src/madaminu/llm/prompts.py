import json
from pathlib import Path
from string import Template

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def load_template(name: str) -> str:
    path = TEMPLATES_DIR / f"{name}.txt"
    return path.read_text(encoding="utf-8")


def render_template(name: str, **variables: str) -> str:
    raw = load_template(name)
    return Template(raw).safe_substitute(variables)


def format_characters_for_prompt(characters: list[dict]) -> str:
    lines = []
    for i, char in enumerate(characters, 1):
        lines.append(
            f"Player {i}:\n"
            f"  Name: {char['character_name']}\n"
            f"  Name (kana): {char.get('character_name_kana', '')}\n"
            f"  Gender: {char.get('character_gender', '不明')}\n"
            f"  Age: {char.get('character_age', '不明')}\n"
            f"  Occupation: {char.get('character_occupation', '')}\n"
            f"  Appearance: {char.get('character_appearance', '')}\n"
            f"  Personality: {char.get('character_personality', '')}\n"
            f"  Background: {char.get('character_background', '')}"
        )
    return "\n\n".join(lines)


def format_json_schema_hint(schema: dict) -> str:
    return json.dumps(schema, ensure_ascii=False, indent=2)
