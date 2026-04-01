import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.llm.client import LIGHT_MODEL, LLMUsage, llm_client
from madaminu.llm.prompts import format_characters_for_prompt, load_template, render_template
from madaminu.models import (
    Evidence,
    EvidenceSource,
    Game,
    GameEnding,
    GameStatus,
    Phase,
    PhaseType,
    PlayerRole,
    SpeechLog,
    Vote,
)

logger = logging.getLogger(__name__)

MAX_DISCOVERIES_PER_PHASE = 5

ROLE_MAP = {
    "criminal": PlayerRole.criminal,
    "witness": PlayerRole.witness,
    "related": PlayerRole.related,
    "innocent": PlayerRole.innocent,
}


async def generate_scenario(db: AsyncSession, game_id: str) -> tuple[dict, list[LLMUsage]]:
    usages: list[LLMUsage] = []

    db.expire_all()
    result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.id == game_id))
    game = result.scalar_one()

    characters = [
        {
            "character_name": p.character_name,
            "character_gender": p.character_gender or "不明",
            "character_age": p.character_age or "不明",
            "character_occupation": p.character_occupation or "",
            "character_appearance": p.character_appearance or "",
            "character_personality": p.character_personality or "",
            "character_background": p.character_background or "",
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

    logger.info("LLM response length: %d chars", len(raw_response))
    logger.info("LLM response (first 500): %s", raw_response[:500])
    logger.info("LLM response (last 500): %s", raw_response[-500:])
    if not raw_response.strip():
        raise ValueError("LLM returned empty response")

    scenario = _parse_scenario_json(raw_response)
    logger.info("Scenario keys: %s", list(scenario.keys()))

    from madaminu.services.map_builder import build_map_structure, generate_route_text

    raw_map = scenario.get("map", {})
    complete_map = build_map_structure(raw_map, victim=scenario.get("victim"), setting=scenario.get("setting"))
    route_text = generate_route_text(complete_map, players=scenario.get("players"))

    game.scenario_skeleton = {
        "setting": scenario["setting"],
        "victim": scenario["victim"],
        "map": complete_map,
        "route_text": route_text,
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
        player.public_info = sp.get("public_info", "")
        player.secret_info = sp["secret_info"]
        player.objective = sp["objective"]
        player.role = ROLE_MAP.get(sp["role"], PlayerRole.innocent)

    map_locations = {}
    skip_types = {"corridor", "entrance", "stairs"}
    for area in complete_map.get("areas", []):
        for room in area.get("rooms", []):
            if room.get("room_type") not in skip_types and room.get("features"):
                map_locations[room["id"]] = room

    all_locations = _resolve_investigation_locations(list(map_locations.keys()), map_locations)
    _create_cycle_phases(db, game, all_locations)

    await db.flush()

    initial_phase_result = await db.execute(
        select(Phase).where(Phase.game_id == game.id).order_by(Phase.phase_order).limit(1)
    )
    initial_phase = initial_phase_result.scalar_one()

    for sp in scenario["players"]:
        player = name_to_player.get(sp["character_name"])
        if player is None:
            continue

        for ev in sp.get("initial_evidences", []):
            db.add(
                Evidence(
                    id=str(uuid.uuid4()),
                    game_id=game.id,
                    player_id=player.id,
                    phase_id=initial_phase.id,
                    title=ev.get("title", "証拠"),
                    content=ev.get("content", ""),
                    source=EvidenceSource.gm_push,
                )
            )

        for alibi in sp.get("initial_alibis", []):
            db.add(
                Evidence(
                    id=str(uuid.uuid4()),
                    game_id=game.id,
                    player_id=player.id,
                    phase_id=initial_phase.id,
                    title=alibi.get("title", "アリバイ"),
                    content=alibi.get("content", ""),
                    source=EvidenceSource.gm_push,
                )
            )

        # Backward compat: single initial_evidence/initial_alibi
        if "initial_evidence" in sp and "initial_evidences" not in sp:
            ev = sp["initial_evidence"]
            db.add(
                Evidence(
                    id=str(uuid.uuid4()),
                    game_id=game.id,
                    player_id=player.id,
                    phase_id=initial_phase.id,
                    title=ev.get("title", "証拠"),
                    content=ev.get("content", ""),
                    source=EvidenceSource.gm_push,
                )
            )
        if "initial_alibi" in sp and "initial_alibis" not in sp:
            alibi = sp["initial_alibi"]
            db.add(
                Evidence(
                    id=str(uuid.uuid4()),
                    game_id=game.id,
                    player_id=player.id,
                    phase_id=initial_phase.id,
                    title=alibi.get("title", "アリバイ"),
                    content=alibi.get("content", ""),
                    source=EvidenceSource.gm_push,
                )
            )

    game.total_llm_cost_usd += sum(u.estimated_cost_usd for u in usages)
    await db.commit()
    await db.refresh(game)

    return scenario, usages


async def validate_scenario(scenario: dict) -> tuple[dict, LLMUsage]:
    system_prompt = load_template("scenario_system")
    user_prompt = render_template("scenario_validate", scenario=json.dumps(scenario, ensure_ascii=False, indent=2))

    raw_response, usage = await llm_client.generate_json(system_prompt, user_prompt, model=LIGHT_MODEL)
    validation = _parse_scenario_json(raw_response)
    return validation, usage


async def generate_initial_evidence(db: AsyncSession, game_id: str) -> tuple[list[dict], LLMUsage]:
    game_result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.id == game_id))
    game = game_result.scalar_one()

    players_info = _format_players_for_adjustment(game.players)
    first_phase = None
    phase_result = await db.execute(select(Phase).where(Phase.game_id == game_id).order_by(Phase.phase_order).limit(1))
    first_phase = phase_result.scalar_one_or_none()
    phase_id = first_phase.id if first_phase else ""

    system_prompt = load_template("scenario_system")
    user_prompt = render_template(
        "initial_evidence",
        scenario_skeleton=json.dumps(game.scenario_skeleton or {}, ensure_ascii=False, indent=2),
        gm_internal_state=json.dumps(game.gm_internal_state or {}, ensure_ascii=False, indent=2),
        players_info=players_info,
    )

    raw_response, usage = await llm_client.generate_json(system_prompt, user_prompt, model=LIGHT_MODEL)
    result = _parse_scenario_json(raw_response)

    distributed = []
    for item in result.get("items", []):
        owner_ids = item.get("owner_ids", [])
        title = item.get("title", "")
        content = item.get("content", "")
        for owner_id in owner_ids:
            player = next((p for p in game.players if p.id == owner_id), None)
            if player is None:
                continue
            evidence = Evidence(
                id=str(uuid.uuid4()),
                game_id=game_id,
                player_id=owner_id,
                phase_id=phase_id,
                title=title,
                content=content,
                source=EvidenceSource.gm_push,
            )
            db.add(evidence)
            distributed.append({"player_id": owner_id, "evidence_id": evidence.id, "title": title, "content": content})

    game.total_llm_cost_usd += usage.estimated_cost_usd
    await db.commit()
    return distributed, usage


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

    game.total_llm_cost_usd += usage.estimated_cost_usd

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
    feature: str | None = None,
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
        map_data = (game.scenario_skeleton or {}).get("map", {})
        for area in map_data.get("areas", []):
            for room in area.get("rooms", []):
                if room.get("id") == location_id:
                    location = room
                    break
            if location:
                break
    if location is None:
        return None, None

    player = next((p for p in game.players if p.id == player_id), None)
    if player is None:
        return None, None

    existing_result = await db.execute(
        select(Evidence).where(Evidence.game_id == game_id, Evidence.player_id == player_id)
    )
    existing = existing_result.scalars().all()
    existing_text = "\n".join(f"- {e.title}: {e.content}" for e in existing) if existing else "(なし)"

    feature_name = feature or location.get("name", location_id)
    location_features = location.get("features", [])

    system_prompt = load_template("scenario_system")
    route_text = (game.scenario_skeleton or {}).get("route_text", "")
    user_prompt = render_template(
        "investigation",
        scenario_skeleton=json.dumps(game.scenario_skeleton or {}, ensure_ascii=False, indent=2),
        route_text=route_text,
        gm_internal_state=json.dumps(game.gm_internal_state or {}, ensure_ascii=False, indent=2),
        player_id=player_id,
        player_name=player.character_name or player.display_name,
        player_role=player.role or "unknown",
        player_secret=player.secret_info or "N/A",
        player_objective=player.objective or "N/A",
        location_name=location.get("name", location_id),
        location_description=location.get("description", ""),
        feature_name=feature_name,
        location_features=", ".join(location_features) if location_features else "(なし)",
        existing_evidence=existing_text,
    )

    raw_response, usage = await llm_client.generate_json(system_prompt, user_prompt, model=LIGHT_MODEL)
    result = _parse_scenario_json(raw_response)

    hint = result.get("hint", "")
    content = result.get("content", "")
    if hint:
        content += f"\n\n💡 {hint}"

    game.total_llm_cost_usd += usage.estimated_cost_usd
    await db.commit()

    return {
        "id": str(uuid.uuid4()),
        "title": result.get("title", "調査結果"),
        "content": content,
        "location_name": location.get("name", location_id),
    }, usage


async def investigate_location_batch(
    db: AsyncSession,
    game_id: str,
    player_id: str,
    location_id: str,
) -> tuple[list[dict], LLMUsage | None]:
    """Generate all discoveries for a location in a single LLM call."""
    game_result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.id == game_id))
    game = game_result.scalar_one()

    if game.current_phase_id is None:
        return [], None

    # Find location in map or phase locations
    location = None
    map_data = (game.scenario_skeleton or {}).get("map", {})
    for area in map_data.get("areas", []):
        for room in area.get("rooms", []):
            if room.get("id") == location_id:
                location = room
                break
        if location:
            break

    if location is None:
        return [], None

    player = next((p for p in game.players if p.id == player_id), None)
    if player is None:
        return [], None

    features = location.get("features", [])
    if not features:
        return [], None

    existing_result = await db.execute(
        select(Evidence).where(Evidence.game_id == game_id, Evidence.player_id == player_id)
    )
    existing = existing_result.scalars().all()
    existing_text = "\n".join(f"- {e.title}: {e.content}" for e in existing) if existing else "(なし)"

    route_text = (game.scenario_skeleton or {}).get("route_text", "")
    system_prompt = load_template("scenario_system")
    user_prompt = render_template(
        "investigation_batch",
        scenario_skeleton=json.dumps(game.scenario_skeleton or {}, ensure_ascii=False, indent=2),
        route_text=route_text,
        gm_internal_state=json.dumps(game.gm_internal_state or {}, ensure_ascii=False, indent=2),
        player_id=player_id,
        player_name=player.character_name or player.display_name,
        player_role=player.role or "unknown",
        player_secret=player.secret_info or "N/A",
        player_objective=player.objective or "N/A",
        location_name=location.get("name", location_id),
        location_features=", ".join(features),
        existing_evidence=existing_text,
    )

    raw_response, usage = await llm_client.generate_json(system_prompt, user_prompt, model=LIGHT_MODEL)
    result = _parse_scenario_json(raw_response)

    # Save discoveries to DB as temporary evidence (source="discovery")
    discoveries = []
    for item in result.get("discoveries", []):
        ev_id = str(uuid.uuid4())
        ev = Evidence(
            id=ev_id,
            game_id=game_id,
            player_id=player_id,
            phase_id=game.current_phase_id or "",
            title=item.get("title", "調査結果"),
            content=item.get("content", ""),
            source="discovery",
        )
        db.add(ev)
        discoveries.append({
            "id": ev_id,
            "title": ev.title,
            "content": ev.content,
            "location_name": location.get("name", location_id),
            "feature": item.get("feature", ""),
        })

    game.total_llm_cost_usd += usage.estimated_cost_usd
    await db.commit()

    return discoveries, usage


async def keep_evidence(
    db: AsyncSession,
    game_id: str,
    player_id: str,
    discovery: dict,
) -> Evidence:
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one()

    evidence = Evidence(
        id=discovery["id"],
        game_id=game_id,
        player_id=player_id,
        phase_id=game.current_phase_id or "",
        title=discovery["title"],
        content=discovery["content"],
        source=EvidenceSource.investigation,
    )
    db.add(evidence)
    await db.commit()
    return evidence


async def tamper_evidence(
    db: AsyncSession,
    game_id: str,
    player_id: str,
    discovery: dict,
) -> dict:
    result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.id == game_id))
    game = result.scalar_one()

    player = next((p for p in game.players if p.id == player_id), None)
    if player is None:
        return discovery

    system_prompt = load_template("scenario_system")
    user_prompt = render_template(
        "tamper_evidence",
        original_title=discovery["title"],
        original_content=discovery["content"],
        player_name=player.character_name or player.display_name,
        location_name=discovery.get("location_name", ""),
    )

    raw_response, usage = await llm_client.generate_json(system_prompt, user_prompt, model=LIGHT_MODEL)
    result_data = _parse_scenario_json(raw_response)

    game.total_llm_cost_usd += usage.estimated_cost_usd
    await db.commit()

    return {
        "id": discovery["id"],
        "title": result_data.get("title", discovery["title"]),
        "content": result_data.get("content", discovery["content"]),
    }


async def generate_ending(db: AsyncSession, game_id: str) -> tuple[GameEnding, LLMUsage]:
    game_result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.id == game_id))
    game = game_result.scalar_one()

    votes_result = await db.execute(select(Vote).where(Vote.game_id == game_id))
    votes = votes_result.scalars().all()

    logs_result = await db.execute(select(SpeechLog).where(SpeechLog.game_id == game_id).order_by(SpeechLog.created_at))
    all_logs = logs_result.scalars().all()

    id_to_name = {p.id: p.character_name or p.display_name for p in game.players}
    players_info = _format_players_for_adjustment(game.players)
    vote_results = _format_votes(votes, id_to_name)
    speech_summary = _summarize_speech_logs(all_logs, id_to_name)

    system_prompt = load_template("scenario_system")
    user_prompt = render_template(
        "ending_generation",
        scenario_skeleton=json.dumps(game.scenario_skeleton or {}, ensure_ascii=False, indent=2),
        route_text=(game.scenario_skeleton or {}).get("route_text", ""),
        gm_internal_state=json.dumps(game.gm_internal_state or {}, ensure_ascii=False, indent=2),
        players_info=players_info,
        vote_results=vote_results,
        speech_summary=speech_summary if speech_summary else "(発言なし)",
    )

    raw_response, usage = await llm_client.generate_json(system_prompt, user_prompt)
    result = _parse_scenario_json(raw_response)

    ending = GameEnding(
        id=str(uuid.uuid4()),
        game_id=game_id,
        ending_text=result.get("ending_text", ""),
        criminal_epilogue=result.get("criminal_epilogue", ""),
        true_criminal_id=result.get("true_criminal_id", ""),
        objective_results=result.get("objective_results"),
    )
    db.add(ending)

    game.total_llm_cost_usd += usage.estimated_cost_usd
    game.status = GameStatus.ended
    await db.commit()

    return ending, usage


def _format_votes(votes, id_to_name: dict[str, str]) -> str:
    if not votes:
        return "(投票なし)"
    lines = []
    vote_counts: dict[str, int] = {}
    for v in votes:
        voter = id_to_name.get(v.voter_player_id, "Unknown")
        suspect = id_to_name.get(v.suspect_player_id, "Unknown")
        lines.append(f"- {voter} → {suspect}")
        vote_counts[suspect] = vote_counts.get(suspect, 0) + 1

    lines.append("\n集計:")
    for name, count in sorted(vote_counts.items(), key=lambda x: -x[1]):
        lines.append(f"- {name}: {count}票")
    return "\n".join(lines)


def _summarize_speech_logs(logs, id_to_name: dict[str, str]) -> str:
    if not logs:
        return ""
    lines = []
    for log in logs[-20:]:
        name = id_to_name.get(log.player_id, "Unknown")
        lines.append(f"[{name}]: {log.transcript}")
    return "\n".join(lines)


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


PHASE_DURATIONS = {
    PhaseType.opening: 300,
    PhaseType.planning: 120,
    PhaseType.investigation: 120,
    PhaseType.discussion: 180,
    PhaseType.voting: 300,
}


def _create_cycle_phases(db, game: Game, all_locations: list[dict]):
    turn_count = game.turn_count or 3
    phase_order = 0

    human_count = sum(1 for p in game.players if not p.is_ai)
    opening_duration = max(60, human_count * 60)

    storytelling_phase = Phase(
        game_id=game.id,
        phase_type=PhaseType.storytelling,
        phase_order=phase_order,
        duration_sec=180,
    )
    db.add(storytelling_phase)
    phase_order += 1

    opening_phase = Phase(
        game_id=game.id,
        phase_type=PhaseType.opening,
        phase_order=phase_order,
        duration_sec=opening_duration,
    )
    db.add(opening_phase)
    phase_order += 1

    # Turn = discussion → planning → investigation
    for _turn in range(turn_count):
        for phase_type in (PhaseType.discussion, PhaseType.planning, PhaseType.investigation):
            locations = all_locations if phase_type in (PhaseType.planning, PhaseType.investigation) else None
            phase = Phase(
                game_id=game.id,
                phase_type=phase_type,
                phase_order=phase_order,
                duration_sec=PHASE_DURATIONS[phase_type],
                investigation_locations=locations,
            )
            db.add(phase)
            phase_order += 1

    # Final discussion & voting
    voting_phase = Phase(
        game_id=game.id,
        phase_type=PhaseType.voting,
        phase_order=phase_order,
        duration_sec=PHASE_DURATIONS[PhaseType.voting],
    )
    db.add(voting_phase)


def _resolve_investigation_locations(raw_locations: list, map_locations: dict) -> list[dict]:
    """Resolve investigation locations from either ID strings or dicts."""
    resolved = []
    for loc in raw_locations:
        if isinstance(loc, str):
            map_loc = map_locations.get(loc)
            if map_loc:
                resolved.append(
                    {
                        "id": map_loc["id"],
                        "name": map_loc["name"],
                        "description": map_loc.get("description", ""),
                        "features": map_loc.get("features", []),
                    }
                )
        elif isinstance(loc, dict) and "id" in loc:
            resolved.append(
                {
                    "id": loc["id"],
                    "name": loc.get("name", loc["id"]),
                    "description": loc.get("description", ""),
                }
            )
    return resolved


def _parse_scenario_json(raw: str) -> dict:
    from json_repair import repair_json

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        repaired = repair_json(cleaned, return_objects=True)
        if isinstance(repaired, dict):
            return repaired
        raise
