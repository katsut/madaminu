import asyncio
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.config import settings
from madaminu.db import get_db
from madaminu.models import Game, GameStatus, Player
from madaminu.repositories import GameRepository
from madaminu.schemas.game import build_game_state
from madaminu.services.ai_player import fill_ai_players
from madaminu.services.errors import InvalidTransition
from madaminu.services.scenario_engine import generate_scenario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rooms", tags=["game"])

MAX_VALIDATION_RETRIES = 2
LLM_COST_LIMIT_USD = 2.0

VALID_TRANSITIONS = {
    GameStatus.waiting: [GameStatus.generating],
    GameStatus.generating: [GameStatus.playing, GameStatus.waiting],
    GameStatus.playing: [GameStatus.voting, GameStatus.ended],
    GameStatus.voting: [GameStatus.ended],
    GameStatus.ended: [],
}


class StartGameResponse(BaseModel):
    status: str
    scenario_setting: dict | None = None
    total_cost_usd: float


def validate_transition(current: GameStatus, target: GameStatus) -> None:
    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise InvalidTransition(f"Cannot transition from {current} to {target}")


async def _generate_images_background(game_id: str, room_code: str, session_factory, ws_manager=None):
    from madaminu.llm.client import llm_client
    from madaminu.services.image_generator import (
        generate_character_portrait,
        generate_scene_image,
        generate_victim_portrait,
    )
    from madaminu.ws.messages import WSMessage

    client = llm_client._client

    try:
        async with session_factory() as db:
            result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.id == game_id))
            game = result.scalar_one_or_none()
            if game is None:
                return

            # Build all image generation tasks in parallel
            tasks = []

            # Scene image
            setting_desc = ""
            if game.scenario_skeleton:
                setting = game.scenario_skeleton.get("setting", {})
                setting_desc = (
                    setting.get("location", "") or setting.get("situation", "") or setting.get("description", "")
                )

            if setting_desc:
                tasks.append(("scene", None, generate_scene_image(client, setting_desc)))

            # Victim portrait
            if game.scenario_skeleton:
                victim = game.scenario_skeleton.get("victim", {})
                victim_name = victim.get("name", "")
                victim_desc = victim.get("description", "")
                if victim_name:
                    tasks.append(("victim", None, generate_victim_portrait(client, victim_name, victim_desc)))

            # Character portraits
            for player in game.players:
                if player.character_name:
                    tasks.append(
                        (
                            "portrait",
                            player.id,
                            generate_character_portrait(
                                client,
                                player.character_gender or "不明",
                                player.character_age or "不明",
                                player.character_appearance or "",
                            ),
                        )
                    )

            # Execute all in parallel
            results = await asyncio.gather(
                *[t[2] for t in tasks],
                return_exceptions=True,
            )

            # Save results
            for (task_type, player_id, _), result_or_error in zip(tasks, results, strict=True):
                if isinstance(result_or_error, Exception):
                    logger.exception("Image generation failed: %s %s", task_type, player_id or "scene")
                    continue

                if task_type == "scene":
                    game.scene_image = result_or_error
                    logger.info("Scene image generated for game %s", room_code)
                elif task_type == "victim":
                    game.victim_image = result_or_error
                    logger.info("Victim image generated for game %s", room_code)
                elif task_type == "portrait":
                    for p in game.players:
                        if p.id == player_id:
                            p.portrait_image = result_or_error
                            logger.info("Portrait generated for %s", p.character_name)
                            break

            await db.commit()

        # Notify clients that images are ready
        if ws_manager:
            await ws_manager.broadcast(
                room_code,
                WSMessage(type="images.ready", data={"room_code": room_code}),
            )

    except Exception:
        logger.exception("Image generation background task failed for game %s", game_id)


async def _generate_scenario_background(
    game_id: str,
    room_code: str,
    session_factory,
    phase_manager,
    ws_manager,
):
    from madaminu.ws.messages import WSMessage

    try:
        # Step 1: Scenario generation
        if ws_manager:
            await ws_manager.broadcast(
                room_code, WSMessage(type="progress", data={"step": "scenario", "status": "in_progress"})
            )

        scenario = None
        for attempt in range(3):
            try:
                async with session_factory() as db:
                    scenario, gen_usages = await generate_scenario(db, game_id)
                    total_cost = sum(u.estimated_cost_usd for u in gen_usages)
                    logger.info(
                        "Scenario generated for %s (attempt %d), cost: $%.4f", room_code, attempt + 1, total_cost
                    )
                    break
            except Exception:
                logger.warning("Scenario generation attempt %d failed for %s", attempt + 1, room_code)
                if attempt == 2:
                    raise

        if ws_manager:
            await ws_manager.broadcast(
                room_code, WSMessage(type="progress", data={"step": "scenario", "status": "done"})
            )

        # Step 2: Start first phase
        if phase_manager:
            await phase_manager.start_first_phase(game_id, room_code)

        # Step 3: Send full game state to all players
        if ws_manager:
            async with session_factory() as db:
                from madaminu.schemas.game import build_game_state

                game_result = await db.execute(
                    select(Game).options(selectinload(Game.players)).where(Game.id == game_id)
                )
                game = game_result.scalar_one_or_none()
                if game:
                    for player in game.players:
                        state = await build_game_state(db, game, player.id)
                        await ws_manager.send_to_player(room_code, player.id, WSMessage(type="game.state", data=state))

        # Step 4: Generate images (parallel, async)
        if ws_manager:
            await ws_manager.broadcast(
                room_code, WSMessage(type="progress", data={"step": "scene_image", "status": "in_progress"})
            )
            await ws_manager.broadcast(
                room_code, WSMessage(type="progress", data={"step": "portraits", "status": "in_progress"})
            )

        await _generate_images_background(game_id, room_code, session_factory, ws_manager)

        # Step 5: Send updated game state with image URLs
        if ws_manager:
            await ws_manager.broadcast(
                room_code, WSMessage(type="progress", data={"step": "scene_image", "status": "done"})
            )
            await ws_manager.broadcast(
                room_code, WSMessage(type="progress", data={"step": "portraits", "status": "done"})
            )

            async with session_factory() as db:
                from madaminu.schemas.game import build_game_state

                game_result = await db.execute(
                    select(Game).options(selectinload(Game.players)).where(Game.id == game_id)
                )
                game = game_result.scalar_one_or_none()
                if game:
                    for player in game.players:
                        state = await build_game_state(db, game, player.id)
                        await ws_manager.send_to_player(room_code, player.id, WSMessage(type="game.state", data=state))

            await ws_manager.broadcast(room_code, WSMessage(type="game.ready", data={"room_code": room_code}))
    except Exception:
        logger.exception("Background scenario generation failed for game %s", game_id)
        if ws_manager:
            await ws_manager.broadcast(
                room_code,
                WSMessage(type="error", data={"message": "Scenario generation failed"}),
            )


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

    if game.total_llm_cost_usd > LLM_COST_LIMIT_USD:
        raise HTTPException(status_code=429, detail="LLM cost limit exceeded for this game") from None

    player_result = await db.execute(
        select(Player).where(Player.game_id == game.id, Player.session_token == x_session_token)
    )
    player = player_result.scalar_one_or_none()
    if player is None or not player.is_host:
        raise HTTPException(status_code=403, detail="Only the host can start the game") from None

    not_ready = [p for p in game.players if p.character_name and not p.is_ready and not p.is_ai]
    if not_ready:
        names = ", ".join(p.display_name for p in not_ready)
        raise HTTPException(status_code=400, detail=f"Not all players are ready: {names}") from None

    characters_ready = sum(1 for p in game.players if p.character_name)
    if characters_ready < 4:
        ai_added = await fill_ai_players(db, game.id, target_count=4)
        if ai_added:
            logger.info("Added %d AI players to fill the room", len(ai_added))
            characters_ready += len(ai_added)
        if characters_ready < 4:
            raise HTTPException(status_code=400, detail=f"Need at least 4 characters, got {characters_ready}") from None

    if settings.testing:
        scenario, gen_usages = await generate_scenario(db, game.id)
        total_cost = sum(u.estimated_cost_usd for u in gen_usages)
        logger.info("Scenario generated, cost: $%.4f", total_cost)

        pm = getattr(request.app.state, "phase_manager", None)
        if pm:
            await pm.start_first_phase(game.id, room_code)

        return StartGameResponse(
            status=game.status,
            scenario_setting=scenario.get("setting", {}) if scenario else {},
            total_cost_usd=round(total_cost, 4),
        )

    validate_transition(game.status, GameStatus.generating)
    game.status = GameStatus.generating
    await db.commit()

    from madaminu.db.database import async_session
    from madaminu.ws.handler import manager as ws_manager
    from madaminu.ws.messages import WSMessage

    pm = getattr(request.app.state, "phase_manager", None)
    session_factory = getattr(request.app.state, "_session_factory", None) or async_session

    await ws_manager.broadcast(
        room_code,
        WSMessage(type="game.generating", data={"room_code": room_code}),
    )

    asyncio.create_task(
        _generate_scenario_background(
            game_id=game.id,
            room_code=room_code,
            session_factory=session_factory,
            phase_manager=pm,
            ws_manager=ws_manager,
        )
    )

    return StartGameResponse(
        status=game.status,
        total_cost_usd=round(game.total_llm_cost_usd, 4),
    )


@router.get("/{room_code}/debug")
async def get_debug_info(
    room_code: str,
    x_session_token: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.room_code == room_code))
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404) from None

    player = next((p for p in game.players if p.session_token == x_session_token), None)
    if player is None or not player.is_host:
        raise HTTPException(status_code=403, detail="Host only") from None

    return {
        "players": [
            {
                "id": p.id,
                "display_name": p.display_name,
                "character_name": p.character_name,
                "role": p.role,
                "secret_info": p.secret_info,
                "objective": p.objective,
                "is_ai": p.is_ai,
            }
            for p in game.players
        ],
    }


@router.get("/{room_code}/state")
async def get_game_state(
    room_code: str,
    x_session_token: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    game_repo = GameRepository(db)
    game = await game_repo.find_by_room_code(room_code)
    if game is None:
        raise HTTPException(status_code=404)

    player = next((p for p in game.players if p.session_token == x_session_token), None)
    if player is None:
        raise HTTPException(status_code=403)

    return await build_game_state(db, game, player.id)
