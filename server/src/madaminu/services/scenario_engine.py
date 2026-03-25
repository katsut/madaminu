import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.llm.client import HAIKU_MODEL, LLMUsage, llm_client
from madaminu.llm.prompts import format_characters_for_prompt, load_template, render_template
from madaminu.models import Game, GameStatus, Phase, PhaseType, PlayerRole

logger = logging.getLogger(__name__)

ROLE_MAP = {
    "criminal": PlayerRole.criminal,
    "witness": PlayerRole.witness,
    "related": PlayerRole.related,
    "innocent": PlayerRole.innocent,
}


async def generate_scenario(db: AsyncSession, game_id: str) -> tuple[dict, list[LLMUsage]]:
    usages: list[LLMUsage] = []

    result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.id == game_id))
    game = result.scalar_one()

    characters = [
        {
            "character_name": p.character_name,
            "character_personality": p.character_personality,
            "character_background": p.character_background,
        }
        for p in game.players
        if p.character_name
    ]

    if len(characters) < 4:
        raise ValueError("Not enough characters created")

    characters_text = format_characters_for_prompt(characters)
    system_prompt = load_template("scenario_system")
    user_prompt = render_template("scenario_generate", characters=characters_text)

    raw_response, usage = await llm_client.generate_json(system_prompt, user_prompt)
    usages.append(usage)

    scenario = _parse_scenario_json(raw_response)

    game.scenario_skeleton = {
        "setting": scenario["setting"],
        "victim": scenario["victim"],
        "relationships": scenario["relationships"],
    }
    game.gm_internal_state = {
        "gm_strategy": scenario.get("gm_strategy", ""),
        "player_gm_notes": {p["character_name"]: p.get("gm_notes", "") for p in scenario["players"]},
    }
    game.status = GameStatus.playing

    name_to_player = {p.character_name: p for p in game.players if p.character_name}

    for sp in scenario["players"]:
        player = name_to_player.get(sp["character_name"])
        if player is None:
            continue
        player.secret_info = sp["secret_info"]
        player.objective = sp["objective"]
        player.role = ROLE_MAP.get(sp["role"], PlayerRole.innocent)

    for i, phase_data in enumerate(scenario.get("phases", [])):
        phase_type_str = phase_data.get("phase_type", "investigation")
        phase_type = PhaseType(phase_type_str) if phase_type_str in PhaseType.__members__ else PhaseType.investigation

        phase = Phase(
            game_id=game.id,
            phase_type=phase_type,
            phase_order=i,
            duration_sec=phase_data.get("duration_sec", 300),
            investigation_locations=phase_data.get("investigation_locations"),
        )
        db.add(phase)

    await db.commit()
    await db.refresh(game)

    return scenario, usages


async def validate_scenario(scenario: dict) -> tuple[dict, LLMUsage]:
    system_prompt = load_template("scenario_system")
    user_prompt = render_template("scenario_validate", scenario=json.dumps(scenario, ensure_ascii=False, indent=2))

    raw_response, usage = await llm_client.generate_json(system_prompt, user_prompt, model=HAIKU_MODEL)
    validation = _parse_scenario_json(raw_response)
    return validation, usage


def _parse_scenario_json(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    return json.loads(cleaned)
