from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from madaminu.db import get_db
from madaminu.routers.schemas import (
    CreateRoomRequest,
    CreateRoomResponse,
    JoinRoomRequest,
    JoinRoomResponse,
    PlayerInfo,
    RoomInfoResponse,
)
from madaminu.services.room_manager import create_room, get_room, join_room

router = APIRouter(prefix="/api/v1/rooms", tags=["rooms"])


@router.post("", response_model=CreateRoomResponse)
async def create_room_endpoint(req: CreateRoomRequest, db: AsyncSession = Depends(get_db)):
    try:
        game, player = await create_room(db, req.display_name)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
    return CreateRoomResponse(
        room_code=game.room_code,
        player_id=player.id,
        session_token=player.session_token,
    )


@router.post("/{room_code}/join", response_model=JoinRoomResponse)
async def join_room_endpoint(room_code: str, req: JoinRoomRequest, db: AsyncSession = Depends(get_db)):
    try:
        _, player = await join_room(db, room_code, req.display_name)
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
        players=[
            PlayerInfo(
                id=p.id,
                display_name=p.display_name,
                character_name=p.character_name,
                is_host=p.is_host,
                connection_status=p.connection_status,
            )
            for p in game.players
        ],
    )
