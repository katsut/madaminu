"""Game progression service. All state in DB, no memory state."""

import logging
import random
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from madaminu.models import Evidence, Game, GameStatus, Phase, PhaseType
from madaminu.repositories import phase_repo, selection_repo

logger = logging.getLogger(__name__)


@dataclass
class AdvanceResult:
    status: str  # "advanced" | "already_advanced" | "not_expired" | "game_ended"
    phase: Phase | None = None
    remaining_sec: int | None = None


class GameService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._sf = session_factory

    async def advance_phase(self, game_id: str, force: bool = False) -> AdvanceResult:
        """Advance to the next phase. DB-level exclusion prevents double advance."""
        async with self._sf() as db:
            game = await phase_repo.get_game_with_phases(db, game_id)
            current = next((p for p in game.phases if p.id == game.current_phase_id), None)
            if current is None:
                return AdvanceResult("already_advanced")

            # Check deadline (unless forced by host)
            if not force and current.deadline_at and datetime.utcnow() < current.deadline_at:
                remaining = int((current.deadline_at - datetime.utcnow()).total_seconds())
                return AdvanceResult("not_expired", remaining_sec=max(0, remaining))

            # Atomic end: only succeeds if not already ended
            ended = await phase_repo.end_phase(db, current.id)
            if not ended:
                # Someone else advanced first — return current phase
                refreshed_current = await phase_repo.get_current_phase(db, game_id)
                return AdvanceResult("already_advanced", phase=refreshed_current)

            # Find and start next phase
            next_phase = await phase_repo.get_next_phase(db, game, current)
            if next_phase is None:
                game.status = GameStatus.ended
                await db.commit()
                logger.info("Game %s ended (last phase)", game.room_code)
                return AdvanceResult("game_ended")

            await phase_repo.start_phase(db, next_phase, game)

            if next_phase.phase_type == PhaseType.voting:
                game.status = GameStatus.voting

            # Auto-assign locations for investigation
            if next_phase.phase_type == PhaseType.investigation:
                next_phase.discoveries_status = "generating"
                await self._auto_assign_locations(db, game, current)

            await db.commit()
            logger.info("Advanced %s → %s for %s", current.phase_type, next_phase.phase_type, game.room_code)
            return AdvanceResult("advanced", phase=next_phase)

    async def select_location(self, game_id: str, player_id: str, location_id: str):
        """Player selects investigation location during planning phase."""
        async with self._sf() as db:
            current = await phase_repo.get_current_phase(db, game_id)
            if not current or current.phase_type != PhaseType.planning:
                return
            await selection_repo.upsert_selection(db, game_id, current.id, player_id, location_id)
            await db.commit()

    async def keep_evidence(self, game_id: str, player_id: str, discovery_id: str) -> Evidence | None:
        """Keep a discovery as permanent evidence."""
        async with self._sf() as db:
            # Check not already kept this phase
            current = await phase_repo.get_current_phase(db, game_id)
            if not current:
                return None
            existing = await db.execute(
                select(Evidence).where(
                    Evidence.game_id == game_id,
                    Evidence.player_id == player_id,
                    Evidence.phase_id == current.id,
                    Evidence.source == "investigation",
                )
            )
            if existing.scalar_one_or_none():
                return None

            # Find the discovery
            discovery = await db.execute(select(Evidence).where(Evidence.id == discovery_id))
            disc = discovery.scalar_one_or_none()
            if not disc or disc.player_id != player_id:
                return None

            # Create kept evidence
            kept = Evidence(
                id=str(uuid.uuid4()),
                game_id=game_id,
                player_id=player_id,
                phase_id=current.id,
                title=disc.title,
                content=disc.content,
                source="investigation",
            )
            db.add(kept)
            await db.commit()
            return kept

    async def vote(self, game_id: str, player_id: str, suspect_id: str) -> dict:
        """Cast a vote. Returns vote status."""
        from madaminu.models import Vote

        async with self._sf() as db:
            # Check not already voted
            existing = await db.execute(
                select(Vote).where(Vote.game_id == game_id, Vote.voter_player_id == player_id)
            )
            if existing.scalar_one_or_none():
                return {"error": "already_voted"}

            db.add(Vote(id=str(uuid.uuid4()), game_id=game_id, voter_player_id=player_id, suspect_player_id=suspect_id))
            await db.commit()

            # Count votes
            game = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.id == game_id))
            g = game.scalar_one()
            votes = await db.execute(select(Vote).where(Vote.game_id == game_id))
            all_votes = votes.scalars().all()
            human_count = sum(1 for p in g.players if not p.is_ai)

            return {
                "voted_count": len(all_votes),
                "total_human": human_count,
                "all_voted": len(all_votes) >= human_count,
            }

    async def get_state(self, game_id: str, player_id: str) -> dict:
        """Build full game state for a specific player."""
        async with self._sf() as db:
            game = await db.execute(
                select(Game).options(selectinload(Game.players)).where(Game.id == game_id)
            )
            g = game.scalar_one()
            from madaminu.schemas.game import build_game_state

            return await build_game_state(db, g, player_id)

    async def _auto_assign_locations(self, db: AsyncSession, game: Game, planning_phase: Phase):
        """Assign random locations to players who didn't select during planning."""
        selections = await selection_repo.get_selections(db, planning_phase.id)
        selected_players = {s.player_id for s in selections}

        map_data = (game.scenario_skeleton or {}).get("map", {})
        all_rooms = [
            room["id"]
            for area in map_data.get("areas", [])
            for room in area.get("rooms", [])
            if room.get("room_type", "room") not in ("corridor", "entrance", "stairs")
        ]

        if not all_rooms:
            return

        # Find the next investigation phase
        sorted_phases = sorted(game.phases, key=lambda p: p.phase_order)
        inv_phase = None
        for p in sorted_phases:
            if p.phase_order > planning_phase.phase_order and p.phase_type == PhaseType.investigation:
                inv_phase = p
                break

        if not inv_phase:
            return

        for player in game.players:
            if player.id not in selected_players:
                loc = random.choice(all_rooms)
                await selection_repo.upsert_selection(db, game.id, inv_phase.id, player.id, loc)
                logger.info("Auto-assigned %s to %s", loc, player.id)
