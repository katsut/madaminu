from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.models import Game, Phase


async def get_game_with_phases(db: AsyncSession, game_id: str) -> Game:
    result = await db.execute(
        select(Game).options(selectinload(Game.phases), selectinload(Game.players)).where(Game.id == game_id)
    )
    return result.scalar_one()


async def get_current_phase(db: AsyncSession, game_id: str) -> Phase | None:
    game = await db.execute(select(Game).where(Game.id == game_id))
    g = game.scalar_one()
    if not g.current_phase_id:
        return None
    result = await db.execute(select(Phase).where(Phase.id == g.current_phase_id))
    return result.scalar_one_or_none()


async def end_phase(db: AsyncSession, phase_id: str) -> bool:
    """End a phase atomically. Returns True if this call ended it, False if already ended."""
    result = await db.execute(
        update(Phase)
        .where(Phase.id == phase_id, Phase.ended_at.is_(None))
        .values(ended_at=datetime.utcnow())
    )
    return result.rowcount > 0


async def get_next_phase(db: AsyncSession, game: Game, current_phase: Phase) -> Phase | None:
    sorted_phases = sorted(game.phases, key=lambda p: p.phase_order)
    current_idx = next(i for i, p in enumerate(sorted_phases) if p.id == current_phase.id)
    if current_idx + 1 >= len(sorted_phases):
        return None
    return sorted_phases[current_idx + 1]


async def start_phase(db: AsyncSession, phase: Phase, game: Game):
    """Set started_at, deadline_at, and update game.current_phase_id."""
    phase.started_at = datetime.utcnow()
    phase.deadline_at = datetime.utcnow() + timedelta(seconds=phase.duration_sec)
    game.current_phase_id = phase.id
