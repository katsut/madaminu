import json
import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.llm.client import HAIKU_MODEL, LLMUsage, llm_client
from madaminu.llm.prompts import format_characters_for_prompt, load_template, render_template
from madaminu.models import Evidence, EvidenceSource, Game, GameStatus, Phase, PhaseType, PlayerRole, SpeechLog

logger = logging.getLogger(__name__)

MAX_INVESTIGATIONS_PER_PHASE = 3

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


async def adjust_phase(db: AsyncSession, game_id: str, ended_phase_id: str) -> tuple[dict, LLMUsage]:
    game_result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.id == game_id))
    game = game_result.scalar_one()

    phase_result = await db.execute(select(Phase).where(Phase.id == ended_phase_id))
    ended_phase = phase_result.scalar_one()

    logs_result = await db.execute(
        select(SpeechLog)
        .where(SpeechLog.game_id == game_id, SpeechLog.phase_id == ended_phase_id)
        .order_by(SpeechLog.created_at)
    )
    speech_logs = logs_result.scalars().all()

    players_info = _format_players_for_adjustment(game.players)
    speech_text = _format_speech_logs(speech_logs, {p.id: p.character_name or p.display_name for p in game.players})

    system_prompt = load_template("scenario_system")
    user_prompt = render_template(
        "phase_adjustment",
        scenario_skeleton=json.dumps(game.scenario_skeleton or {}, ensure_ascii=False, indent=2),
        gm_internal_state=json.dumps(game.gm_internal_state or {}, ensure_ascii=False, indent=2),
        phase_type=ended_phase.phase_type,
        phase_order=str(ended_phase.phase_order),
        players_info=players_info,
        speech_logs=speech_text if speech_text else "(発言なし)",
    )

    raw_response, usage = await llm_client.generate_json(system_prompt, user_prompt)
    adjustment = _parse_scenario_json(raw_response)

    if adjustment.get("gm_state_update"):
        gm_state = dict(game.gm_internal_state or {})
        update = adjustment["gm_state_update"]
        if update.get("gm_strategy"):
            gm_state["gm_strategy"] = update["gm_strategy"]
        if update.get("player_gm_notes"):
            existing_notes = dict(gm_state.get("player_gm_notes", {}))
            existing_notes.update(update["player_gm_notes"])
            gm_state["player_gm_notes"] = existing_notes
        game.gm_internal_state = gm_state

    distributed_evidence = []
    player_id_map = {p.id: p for p in game.players}
    next_phase_id = game.current_phase_id or ended_phase_id

    for ev in adjustment.get("evidence_distribution", []):
        target_id = ev.get("target_player_id", "")
        if target_id not in player_id_map:
            continue
        evidence = Evidence(
            id=str(uuid.uuid4()),
            game_id=game_id,
            player_id=target_id,
            phase_id=next_phase_id,
            title=ev.get("title", "新たな手がかり"),
            content=ev.get("content", ""),
            source=EvidenceSource.gm_push,
        )
        db.add(evidence)
        distributed_evidence.append({"player_id": target_id, "title": evidence.title, "content": evidence.content})

    await db.commit()
    return adjustment, usage


async def investigate_location(
    db: AsyncSession,
    game_id: str,
    player_id: str,
    location_id: str,
) -> tuple[Evidence | None, LLMUsage | None]:
    game_result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.id == game_id))
    game = game_result.scalar_one()

    if game.current_phase_id is None:
        return None, None

    phase_result = await db.execute(select(Phase).where(Phase.id == game.current_phase_id))
    phase = phase_result.scalar_one()

    if phase.phase_type != PhaseType.investigation:
        return None, None

    locations = phase.investigation_locations or []
    location = next((loc for loc in locations if loc.get("id") == location_id), None)
    if location is None:
        return None, None

    count_result = await db.execute(
        select(func.count())
        .select_from(Evidence)
        .where(
            Evidence.game_id == game_id,
            Evidence.player_id == player_id,
            Evidence.phase_id == phase.id,
            Evidence.source == EvidenceSource.investigation,
        )
    )
    investigation_count = count_result.scalar_one()
    if investigation_count >= MAX_INVESTIGATIONS_PER_PHASE:
        return None, None

    player = next((p for p in game.players if p.id == player_id), None)
    if player is None:
        return None, None

    existing_result = await db.execute(
        select(Evidence).where(Evidence.game_id == game_id, Evidence.player_id == player_id)
    )
    existing = existing_result.scalars().all()
    existing_text = "\n".join(f"- {e.title}: {e.content}" for e in existing) if existing else "(なし)"

    system_prompt = load_template("scenario_system")
    user_prompt = render_template(
        "investigation",
        scenario_skeleton=json.dumps(game.scenario_skeleton or {}, ensure_ascii=False, indent=2),
        gm_internal_state=json.dumps(game.gm_internal_state or {}, ensure_ascii=False, indent=2),
        player_id=player_id,
        player_name=player.character_name or player.display_name,
        player_role=player.role or "unknown",
        player_secret=player.secret_info or "N/A",
        player_objective=player.objective or "N/A",
        location_name=location.get("name", location_id),
        location_description=location.get("description", ""),
        existing_evidence=existing_text,
    )

    raw_response, usage = await llm_client.generate_json(system_prompt, user_prompt, model=HAIKU_MODEL)
    result = _parse_scenario_json(raw_response)

    evidence = Evidence(
        id=str(uuid.uuid4()),
        game_id=game_id,
        player_id=player_id,
        phase_id=phase.id,
        title=result.get("title", "調査結果"),
        content=result.get("content", ""),
        source=EvidenceSource.investigation,
    )
    db.add(evidence)
    await db.commit()

    return evidence, usage


def _format_players_for_adjustment(players) -> str:
    lines = []
    for p in players:
        name = p.character_name or p.display_name
        lines.append(
            f"- ID: {p.id}\n"
            f"  Name: {name}\n"
            f"  Role: {p.role or 'unknown'}\n"
            f"  Secret: {p.secret_info or 'N/A'}\n"
            f"  Objective: {p.objective or 'N/A'}"
        )
    return "\n".join(lines)


def _format_speech_logs(logs, id_to_name: dict[str, str]) -> str:
    lines = []
    for log in logs:
        name = id_to_name.get(log.player_id, "Unknown")
        lines.append(f"[{name}]: {log.transcript}")
    return "\n".join(lines)


def _parse_scenario_json(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    return json.loads(cleaned)
