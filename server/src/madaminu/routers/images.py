import base64

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.db import get_db
from madaminu.models import Game, Player

router = APIRouter(prefix="/api/v1/images", tags=["images"])


@router.get("/player/{player_id}")
async def get_player_portrait(player_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one_or_none()
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found") from None
    if player.portrait_image is None:
        raise HTTPException(status_code=404, detail="Portrait not yet generated") from None

    image_bytes = base64.b64decode(player.portrait_image)
    return Response(content=image_bytes, media_type="image/png")


@router.get("/game/{room_code}/scene")
async def get_scene_image(room_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Game).options(selectinload(Game.players)).where(Game.room_code == room_code)
    )
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found") from None
    if game.scene_image is None:
        raise HTTPException(status_code=404, detail="Scene image not yet generated") from None

    image_bytes = base64.b64decode(game.scene_image)
    return Response(content=image_bytes, media_type="image/png")
