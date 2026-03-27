from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from madaminu.models import Game, Phase


async def _get_current_phase_dict(db: AsyncSession, current_phase_id: str) -> dict | None:
    result = await db.execute(select(Phase).where(Phase.id == current_phase_id))
    phase = result.scalar_one_or_none()
    if phase is None:
        return None

    remaining = 0
    if phase.started_at:
        started = phase.started_at
        elapsed = (datetime.utcnow() - started).total_seconds()
        remaining = max(0, phase.duration_sec - int(elapsed))

    return {
        "phase_id": phase.id,
        "phase_type": phase.phase_type,
        "phase_order": phase.phase_order,
        "duration_sec": phase.duration_sec,
        "remaining_sec": remaining,
        "investigation_locations": phase.investigation_locations,
    }


async def build_game_state(db: AsyncSession, game: Game, player_id: str) -> dict:
    players_public = [
        {
            "id": p.id,
            "display_name": p.display_name,
            "character_name": p.character_name,
            "character_name_kana": p.character_name_kana,
            "character_gender": p.character_gender,
            "character_age": p.character_age,
            "character_occupation": p.character_occupation,
            "character_appearance": p.character_appearance,
            "character_personality": p.character_personality,
            "character_background": p.character_background,
            "public_info": p.public_info,
            "is_host": p.is_host,
            "is_ai": p.is_ai,
            "connection_status": p.connection_status,
            "portrait_url": f"/api/v1/images/player/{p.id}" if p.portrait_image else None,
        }
        for p in game.players
    ]

    state = {
        "room_code": game.room_code,
        "status": game.status,
        "host_player_id": game.host_player_id,
        "players": players_public,
        "scenario_setting": game.scenario_skeleton.get("setting", {}) if game.scenario_skeleton else None,
        "victim": game.scenario_skeleton.get("victim", {}) if game.scenario_skeleton else None,
        "scene_image_url": f"/api/v1/images/game/{game.room_code}/scene" if game.scene_image else None,
        "victim_image_url": f"/api/v1/images/game/{game.room_code}/victim" if game.victim_image else None,
        "map_url": f"/api/v1/images/game/{game.room_code}/map" if game.scenario_skeleton and "map" in game.scenario_skeleton else None,
    }

    from madaminu.models import Evidence

    current_player = next((p for p in game.players if p.id == player_id), None)
    if current_player:
        state["my_secret_info"] = current_player.secret_info
        state["my_objective"] = current_player.objective
        state["my_role"] = current_player.role

    ev_result = await db.execute(
        select(Evidence)
        .where(Evidence.game_id == game.id, Evidence.player_id == player_id)
        .order_by(Evidence.revealed_at)
    )
    my_evidences = ev_result.scalars().all()
    state["my_evidences"] = [
        {"evidence_id": e.id, "title": e.title, "content": e.content, "source": e.source}
        for e in my_evidences
    ]

    if game.current_phase_id:
        phase_info = await _get_current_phase_dict(db, game.current_phase_id)
        if phase_info:
            total_result = await db.execute(
                select(func.count()).select_from(Phase).where(Phase.game_id == game.id)
            )
            phase_info["total_phases"] = total_result.scalar_one()
            phase_info["turn_number"] = phase_info["phase_order"] // 3 + 1
            phase_info["total_turns"] = game.turn_count or 3
            state["current_phase"] = phase_info

    state["current_speaker_id"] = None

    return state
