import base64
import hashlib
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.db import get_db
from madaminu.models import Game, Player
from madaminu.services.map_renderer import render_map_svg

router = APIRouter(prefix="/api/v1/images", tags=["images"])

MAX_SIZE = 1024
CACHE_HEADERS = {"Cache-Control": "public, max-age=86400, immutable"}

_resize_cache: dict[str, bytes] = {}
_CACHE_MAX = 200


def _resize_image(image_bytes: bytes, size: int) -> bytes:
    if size >= MAX_SIZE:
        return image_bytes

    cache_key = hashlib.md5(image_bytes[:256]).hexdigest() + f"_{size}"
    if cache_key in _resize_cache:
        return _resize_cache[cache_key]

    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail((size, size), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    result = buf.getvalue()

    if len(_resize_cache) < _CACHE_MAX:
        _resize_cache[cache_key] = result

    return result


@router.get("/player/{player_id}")
async def get_player_portrait(
    player_id: str,
    size: int = Query(default=MAX_SIZE, ge=32, le=MAX_SIZE),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one_or_none()
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found") from None
    if player.portrait_image is None:
        raise HTTPException(status_code=404, detail="Portrait not yet generated") from None

    image_bytes = base64.b64decode(player.portrait_image)
    resized = _resize_image(image_bytes, size)
    return Response(content=resized, media_type="image/png", headers=CACHE_HEADERS)


@router.get("/game/{room_code}/scene")
async def get_scene_image(
    room_code: str,
    size: int = Query(default=MAX_SIZE, ge=32, le=MAX_SIZE),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.room_code == room_code))
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found") from None
    if game.scene_image is None:
        raise HTTPException(status_code=404, detail="Scene image not yet generated") from None

    image_bytes = base64.b64decode(game.scene_image)
    resized = _resize_image(image_bytes, size)
    return Response(content=resized, media_type="image/png", headers=CACHE_HEADERS)


@router.get("/game/{room_code}/victim")
async def get_victim_image(
    room_code: str,
    size: int = Query(default=MAX_SIZE, ge=32, le=MAX_SIZE),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Game).where(Game.room_code == room_code))
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found") from None
    if game.victim_image is None:
        raise HTTPException(status_code=404, detail="Victim image not yet generated") from None

    image_bytes = base64.b64decode(game.victim_image)
    resized = _resize_image(image_bytes, size)
    return Response(content=resized, media_type="image/png", headers=CACHE_HEADERS)


@router.get("/game/{room_code}/map")
async def get_map_svg(
    room_code: str,
    highlight: str = Query(default="", description="Room ID to highlight"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Game).where(Game.room_code == room_code))
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found") from None
    if not game.scenario_skeleton or "map" not in game.scenario_skeleton:
        raise HTTPException(status_code=404, detail="Map not yet generated") from None

    svg = render_map_svg(game.scenario_skeleton["map"], highlight_room=highlight or None)
    return Response(content=svg, media_type="image/svg+xml")
