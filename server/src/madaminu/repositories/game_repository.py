from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.models import Game, GameStatus


class GameRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_id(self, game_id: str) -> Game | None:
        result = await self.db.execute(select(Game).options(selectinload(Game.players)).where(Game.id == game_id))
        return result.scalar_one_or_none()

    async def find_by_room_code(self, room_code: str) -> Game | None:
        result = await self.db.execute(
            select(Game).options(selectinload(Game.players)).where(Game.room_code == room_code)
        )
        return result.scalar_one_or_none()

    async def find_waiting_rooms(self, limit: int = 20) -> list[Game]:
        result = await self.db.execute(
            select(Game)
            .options(selectinload(Game.players))
            .where(Game.status == GameStatus.waiting)
            .order_by(Game.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def save(self, game: Game) -> Game:
        self.db.add(game)
        await self.db.flush()
        return game

    async def commit(self):
        await self.db.commit()
