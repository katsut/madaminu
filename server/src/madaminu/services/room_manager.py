import random
import string
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.models import ConnectionStatus, Game, GameStatus, Player

MAX_PLAYERS = 7
MIN_PLAYERS = 4
ROOM_CODE_LENGTH = 6


def _generate_room_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=ROOM_CODE_LENGTH))


async def create_room(db: AsyncSession, display_name: str, password: str | None = None) -> tuple[Game, Player]:
    for _ in range(10):
        code = _generate_room_code()
        existing = await db.execute(select(Game).where(Game.room_code == code))
        if existing.scalar_one_or_none() is None:
            break
    else:
        raise ValueError("Failed to generate unique room code")

    game = Game(
        id=str(uuid.uuid4()),
        room_code=code,
        status=GameStatus.waiting,
        password=password if password else None,
    )
    db.add(game)
    await db.flush()

    player = Player(
        id=str(uuid.uuid4()),
        game_id=game.id,
        session_token=str(uuid.uuid4()),
        display_name=display_name,
        is_host=True,
        connection_status=ConnectionStatus.offline,
    )
    db.add(player)
    await db.flush()

    game.host_player_id = player.id
    await db.commit()
    await db.refresh(game)
    await db.refresh(player)

    return game, player


async def join_room(
    db: AsyncSession, room_code: str, display_name: str, password: str | None = None
) -> tuple[Game, Player]:
    result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.room_code == room_code))
    game = result.scalar_one_or_none()
    if game is None:
        raise ValueError("Room not found")

    if game.status != GameStatus.waiting:
        raise ValueError("Game already started")

    if game.password and game.password != password:
        raise ValueError("Invalid password")

    if len(game.players) >= MAX_PLAYERS:
        raise ValueError(f"Room is full (max {MAX_PLAYERS} players)")

    player = Player(
        id=str(uuid.uuid4()),
        game_id=game.id,
        session_token=str(uuid.uuid4()),
        display_name=display_name,
        is_host=False,
        connection_status=ConnectionStatus.offline,
    )
    db.add(player)
    await db.commit()
    await db.refresh(player)

    return game, player


async def list_rooms(db: AsyncSession) -> list[Game]:
    result = await db.execute(
        select(Game)
        .options(selectinload(Game.players))
        .where(Game.status == GameStatus.waiting)
        .order_by(Game.created_at.desc())
        .limit(20)
    )
    return list(result.scalars().all())


async def get_room(db: AsyncSession, room_code: str) -> Game:
    result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.room_code == room_code))
    game = result.scalar_one_or_none()
    if game is None:
        raise ValueError("Room not found")
    return game
