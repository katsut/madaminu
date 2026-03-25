import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.db import get_db
from madaminu.models import Game, GameStatus, Player
from madaminu.services.ai_player import fill_ai_players
from madaminu.services.scenario_engine import generate_scenario, validate_scenario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rooms", tags=["game"])

MAX_VALIDATION_RETRIES = 2


class StartGameResponse(BaseModel):
    status: str
    scenario_setting: dict
    total_cost_usd: float


@router.post("/{room_code}/start", response_model=StartGameResponse)
async def start_game(
    request: Request,
    room_code: str,
    x_session_token: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.room_code == room_code))
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Room not found") from None

    if game.status != GameStatus.waiting:
        raise HTTPException(status_code=400, detail="Game already started") from None

    player_result = await db.execute(
        select(Player).where(Player.game_id == game.id, Player.session_token == x_session_token)
    )
    player = player_result.scalar_one_or_none()
    if player is None or not player.is_host:
        raise HTTPException(status_code=403, detail="Only the host can start the game") from None

    characters_ready = sum(1 for p in game.players if p.character_name)
    if characters_ready < 4:
        ai_added = await fill_ai_players(db, game.id, target_count=4)
        if ai_added:
            logger.info("Added %d AI players to fill the room", len(ai_added))
            characters_ready += len(ai_added)
        if characters_ready < 4:
            raise HTTPException(status_code=400, detail=f"Need at least 4 characters, got {characters_ready}") from None

    total_cost = 0.0

    scenario, gen_usages = await generate_scenario(db, game.id)
    total_cost += sum(u.estimated_cost_usd for u in gen_usages)
    logger.info("Scenario generated, cost: $%.4f", total_cost)

    pm = getattr(request.app.state, "phase_manager", None)
    if pm:
        await pm.start_first_phase(game.id, room_code)

    return StartGameResponse(
        status=game.status,
        scenario_setting=scenario.get("setting", {}) if scenario else {},
        total_cost_usd=round(total_cost, 4),
    )
