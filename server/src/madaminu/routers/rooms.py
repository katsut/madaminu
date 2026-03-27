from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.db import get_db
from madaminu.models import Game, Player
from madaminu.routers.schemas import (
    CreateRoomRequest,
    CreateRoomResponse,
    JoinRoomRequest,
    JoinRoomResponse,
    PlayerInfo,
    RoomInfoResponse,
    RoomListItem,
)
from madaminu.services.room_manager import create_room, get_room, join_room, list_rooms

router = APIRouter(prefix="/api/v1/rooms", tags=["rooms"])


@router.get("", response_model=list[RoomListItem])
async def list_rooms_endpoint(db: AsyncSession = Depends(get_db)):
    rooms = await list_rooms(db)
    return [
        RoomListItem(
            room_code=g.room_code,
            status=g.status,
            player_count=len(g.players),
            host_name=next((p.display_name for p in g.players if p.is_host), None),
            has_password=g.password is not None,
        )
        for g in rooms
    ]


@router.post("", response_model=CreateRoomResponse)
async def create_room_endpoint(req: CreateRoomRequest, db: AsyncSession = Depends(get_db), x_device_id: str | None = Header(None)):
    try:
        game, player = await create_room(db, req.display_name, req.password, device_id=x_device_id)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
    return CreateRoomResponse(
        room_code=game.room_code,
        player_id=player.id,
        session_token=player.session_token,
    )


@router.post("/{room_code}/join", response_model=JoinRoomResponse)
async def join_room_endpoint(room_code: str, req: JoinRoomRequest, db: AsyncSession = Depends(get_db), x_device_id: str | None = Header(None)):
    try:
        _, player = await join_room(db, room_code, req.display_name, req.password, device_id=x_device_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return JoinRoomResponse(
        player_id=player.id,
        session_token=player.session_token,
    )


@router.get("/{room_code}", response_model=RoomInfoResponse)
async def get_room_endpoint(room_code: str, db: AsyncSession = Depends(get_db)):
    try:
        game = await get_room(db, room_code)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    return RoomInfoResponse(
        room_code=game.room_code,
        status=game.status,
        host_player_id=game.host_player_id,
        has_password=game.password is not None,
        players=[
            PlayerInfo(
                id=p.id,
                display_name=p.display_name,
                character_name=p.character_name,
                is_host=p.is_host,
                is_ready=p.is_ready,
                connection_status=p.connection_status,
            )
            for p in game.players
        ],
    )


@router.post("/{room_code}/ready")
async def toggle_ready(room_code: str, x_session_token: str = Header(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Player)
        .join(Game, Player.game_id == Game.id)
        .where(Game.room_code == room_code, Player.session_token == x_session_token)
    )
    player = result.scalar_one_or_none()
    if player is None:
        raise HTTPException(status_code=403, detail="Invalid token") from None

    player.is_ready = not player.is_ready
    await db.commit()
    return {"is_ready": player.is_ready}


@router.get("/mine/list")
async def list_my_rooms(x_device_id: str = Header(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Player)
        .options(selectinload(Player.game))
        .where(Player.device_id == x_device_id)
        .order_by(Player.created_at.desc())
        .limit(20)
    )
    players = result.scalars().all()

    rooms = []
    for p in players:
        g = p.game
        if g is None:
            continue
        rooms.append({
            "room_code": g.room_code,
            "status": g.status,
            "is_host": p.is_host,
            "display_name": p.display_name,
            "character_name": p.character_name,
            "session_token": p.session_token,
            "player_id": p.id,
            "created_at": str(g.created_at) if g.created_at else None,
        })
    return rooms


@router.delete("/{room_code}")
async def delete_room(room_code: str, x_device_id: str = Header(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Game).options(selectinload(Game.players)).where(Game.room_code == room_code)
    )
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Room not found") from None

    host = next((p for p in game.players if p.is_host), None)
    if host is None or host.device_id != x_device_id:
        raise HTTPException(status_code=403, detail="Only the host can delete this room") from None

    # Clear self-referencing FKs before cascade delete
    game.host_player_id = None
    game.current_phase_id = None
    await db.flush()

    await db.delete(game)
    await db.commit()
    return {"status": "deleted"}
