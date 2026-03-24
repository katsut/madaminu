from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.db import get_db
from madaminu.models import Game, GameStatus, Player
from madaminu.routers.schemas import CharacterResponse, CreateCharacterRequest

router = APIRouter(prefix="/api/v1/rooms", tags=["characters"])


async def _get_player_by_token(db: AsyncSession, room_code: str, token: str) -> Player:
    result = await db.execute(
        select(Player)
        .join(Game, Player.game_id == Game.id)
        .where(Game.room_code == room_code, Player.session_token == token)
    )
    player = result.scalar_one_or_none()
    if player is None:
        raise HTTPException(status_code=401, detail="Invalid token") from None
    return player


@router.post("/{room_code}/characters", response_model=CharacterResponse)
async def create_character(
    room_code: str,
    req: CreateCharacterRequest,
    x_session_token: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.room_code == room_code))
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Room not found") from None

    if game.status != GameStatus.waiting:
        raise HTTPException(status_code=400, detail="Game already started") from None

    player = await _get_player_by_token(db, room_code, x_session_token)

    player.character_name = req.character_name
    player.character_personality = req.character_personality
    player.character_background = req.character_background
    await db.commit()
    await db.refresh(player)

    return CharacterResponse(
        player_id=player.id,
        character_name=player.character_name,
        character_personality=player.character_personality,
        character_background=player.character_background,
    )
