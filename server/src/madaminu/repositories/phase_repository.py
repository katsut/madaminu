from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from madaminu.models import Phase


class PhaseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_id(self, phase_id: str) -> Phase | None:
        result = await self.db.execute(select(Phase).where(Phase.id == phase_id))
        return result.scalar_one_or_none()

    async def find_by_game_id(self, game_id: str) -> list[Phase]:
        result = await self.db.execute(select(Phase).where(Phase.game_id == game_id).order_by(Phase.phase_order))
        return list(result.scalars().all())

    async def find_expired(self) -> list[Phase]:
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(Phase).where(
                Phase.deadline_at.isnot(None),
                Phase.deadline_at <= now,
                Phase.ended_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def save(self, phase: Phase) -> Phase:
        self.db.add(phase)
        await self.db.flush()
        return phase

    async def commit(self):
        await self.db.commit()
