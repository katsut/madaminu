import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from madaminu.models import InvestigationSelection


async def get_selections(db: AsyncSession, phase_id: str) -> list[InvestigationSelection]:
    result = await db.execute(select(InvestigationSelection).where(InvestigationSelection.phase_id == phase_id))
    return list(result.scalars().all())


async def upsert_selection(db: AsyncSession, game_id: str, phase_id: str, player_id: str, location_id: str):
    result = await db.execute(
        select(InvestigationSelection).where(
            InvestigationSelection.phase_id == phase_id,
            InvestigationSelection.player_id == player_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.location_id = location_id
    else:
        db.add(
            InvestigationSelection(
                id=str(uuid.uuid4()),
                game_id=game_id,
                phase_id=phase_id,
                player_id=player_id,
                location_id=location_id,
            )
        )
