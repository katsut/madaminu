from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from madaminu.models import Game, Player


class PlayerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_id(self, player_id: str) -> Player | None:
        result = await self.db.execute(select(Player).where(Player.id == player_id))
        return result.scalar_one_or_none()

    async def find_by_session_token(self, token: str) -> Player | None:
        result = await self.db.execute(select(Player).where(Player.session_token == token))
        return result.scalar_one_or_none()

    async def find_by_game_and_token(self, game_id: str, token: str) -> Player | None:
        result = await self.db.execute(select(Player).where(Player.game_id == game_id, Player.session_token == token))
        return result.scalar_one_or_none()

    async def find_by_room_code_and_token(self, room_code: str, token: str) -> Player | None:
        result = await self.db.execute(
            select(Player)
            .join(Game, Player.game_id == Game.id)
            .where(Game.room_code == room_code, Player.session_token == token)
        )
        return result.scalar_one_or_none()

    async def save(self, player: Player) -> Player:
        self.db.add(player)
        await self.db.flush()
        return player

    async def commit(self):
        await self.db.commit()
