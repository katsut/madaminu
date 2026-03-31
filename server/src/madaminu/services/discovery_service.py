"""Discovery generation service. LLM calls don't hold DB sessions."""

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from madaminu.models import Evidence, Game, Phase, Player
from madaminu.models.investigation_selection import InvestigationSelection

logger = logging.getLogger(__name__)


class DiscoveryService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._sf = session_factory

    async def generate_all(self, game_id: str, phase_id: str):
        """Generate discoveries for all players. Runs as background job.

        DB sessions are NOT held during LLM calls.
        """
        # 1. Load context from DB → close session
        async with self._sf() as db:
            game = await db.execute(
                select(Game).options(selectinload(Game.players)).where(Game.id == game_id)
            )
            g = game.scalar_one()
            map_data = (g.scenario_skeleton or {}).get("map", {})
            route_text = (g.scenario_skeleton or {}).get("route_text", "")

            selections = await db.execute(
                select(InvestigationSelection).where(InvestigationSelection.phase_id == phase_id)
            )
            sels = selections.scalars().all()

            context = {
                "game": {
                    "id": g.id,
                    "scenario_skeleton": g.scenario_skeleton,
                    "gm_internal_state": g.gm_internal_state,
                    "route_text": route_text,
                },
                "players": {p.id: p for p in g.players},
                "selections": [(s.player_id, s.location_id) for s in sels],
                "map_data": map_data,
            }
        # DB session closed

        if not context["selections"]:
            logger.warning("No selections for phase %s", phase_id)
            async with self._sf() as db:
                phase = await db.execute(select(Phase).where(Phase.id == phase_id))
                p = phase.scalar_one()
                p.discoveries_status = "ready"
                await db.commit()
            return

        # 2. LLM calls in parallel (no DB session held)
        tasks = []
        for player_id, location_id in context["selections"]:
            player = context["players"].get(player_id)
            if player:
                tasks.append(self._generate_for_player(context, player, location_id, context["selections"]))

        results = await asyncio.gather(*tasks)

        # 3. Save results to DB → close session
        async with self._sf() as db:
            for player_id, discoveries in results:
                for d in discoveries:
                    db.add(
                        Evidence(
                            id=str(uuid.uuid4()),
                            game_id=game_id,
                            player_id=player_id,
                            phase_id=phase_id,
                            title=d["title"],
                            content=d["content"],
                            source="discovery",
                        )
                    )
            phase = await db.execute(select(Phase).where(Phase.id == phase_id))
            p = phase.scalar_one()
            p.discoveries_status = "ready"
            g_result = await db.execute(select(Game).where(Game.id == game_id))
            g = g_result.scalar_one()
            g.total_llm_cost_usd += sum(cost for _, _, cost in [r for r in results if len(r) == 3] if cost)
            await db.commit()
        # DB session closed

        logger.info("Discoveries generated for phase %s", phase_id)

    async def _generate_for_player(
        self, context: dict, player: Player, location_id: str, all_selections: list,
    ) -> tuple[str, list[dict]]:
        """Generate discoveries for one player. No DB access."""
        import json

        from madaminu.llm.client import LIGHT_MODEL, llm_client
        from madaminu.services.scenario_engine import _parse_scenario_json
        from madaminu.services.template_loader import load_template, render_template

        map_data = context["map_data"]
        location = None
        for area in map_data.get("areas", []):
            for room in area.get("rooms", []):
                if room.get("id") == location_id:
                    location = room
                    break
            if location:
                break

        if not location:
            logger.warning("Location %s not found", location_id)
            return player.id, []

        features = location.get("features", [])
        if not features:
            return player.id, []

        system_prompt = load_template("scenario_system")
        user_prompt = render_template(
            "investigation_batch",
            scenario_skeleton=json.dumps(context["game"]["scenario_skeleton"] or {}, ensure_ascii=False, indent=2),
            route_text=context["game"]["route_text"],
            gm_internal_state=json.dumps(context["game"]["gm_internal_state"] or {}, ensure_ascii=False, indent=2),
            player_id=player.id,
            player_name=player.character_name or player.display_name,
            player_role=player.role or "unknown",
            player_secret=player.secret_info or "N/A",
            player_objective=player.objective or "N/A",
            location_name=location.get("name", location_id),
            location_features=", ".join(features),
            existing_evidence="(なし)",
        )

        raw, usage = await llm_client.generate_json(system_prompt, user_prompt, model=LIGHT_MODEL)
        result = _parse_scenario_json(raw)

        discoveries = []
        for item in result.get("discoveries", []):
            discoveries.append({
                "title": item.get("title", "調査結果"),
                "content": item.get("content", ""),
                "feature": item.get("feature", ""),
            })

        logger.info("Generated %d discoveries for %s at %s", len(discoveries), player.id, location_id)
        return player.id, discoveries

    async def get_discoveries(self, game_id: str, player_id: str, phase_id: str) -> list[dict]:
        """Get discoveries from DB."""
        async with self._sf() as db:
            result = await db.execute(
                select(Evidence).where(
                    Evidence.game_id == game_id,
                    Evidence.player_id == player_id,
                    Evidence.phase_id == phase_id,
                    Evidence.source == "discovery",
                )
            )
            return [
                {"id": e.id, "title": e.title, "content": e.content, "feature": ""}
                for e in result.scalars()
            ]
