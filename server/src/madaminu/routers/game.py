import asyncio
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.db import get_db
from madaminu.db.database import async_session
from madaminu.models import Game, GameStatus, Player
from madaminu.repositories import GameRepository
from madaminu.schemas.game import build_game_state
from madaminu.services.ai_player import fill_ai_players
from madaminu.services.errors import InvalidTransition
from madaminu.services.scenario_engine import generate_scenario
from madaminu.ws.handler_v3 import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rooms", tags=["game"])

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
    total_cost_usd: float


def validate_transition(current: GameStatus, target: GameStatus) -> None:
    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise InvalidTransition(f"Cannot transition from {current} to {target}")


async def _generate_images(game_id: str, room_code: str, session_factory):
    from madaminu.llm.client import llm_client
    from madaminu.services.image_generator import (
        generate_character_portrait,
        generate_scene_image,
        generate_victim_portrait,
    )

    client = llm_client._client

    async with session_factory() as db:
        result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.id == game_id))
        game = result.scalar_one_or_none()
        if game is None:
            return

        tasks = []

        if game.scenario_skeleton:
            setting = game.scenario_skeleton.get("setting", {})
            setting_desc = setting.get("location", "") or setting.get("situation", "") or setting.get("description", "")
            if setting_desc:
                tasks.append(("scene", None, generate_scene_image(client, setting_desc)))

            victim = game.scenario_skeleton.get("victim", {})
            if victim.get("name"):
                victim_coro = generate_victim_portrait(
                    client,
                    victim["name"],
                    victim.get("description", ""),
                )
                tasks.append(("victim", None, victim_coro))

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

        results = await asyncio.gather(*[t[2] for t in tasks], return_exceptions=True)

        for (task_type, player_id, _), result_or_error in zip(tasks, results, strict=True):
            if isinstance(result_or_error, Exception):
                logger.exception("Image generation failed: %s %s", task_type, player_id or "scene")
                continue

            if task_type == "scene":
                game.scene_image = result_or_error
            elif task_type == "victim":
                game.victim_image = result_or_error
            elif task_type == "portrait":
                for p in game.players:
                    if p.id == player_id:
                        p.portrait_image = result_or_error
                        break

        await db.commit()


async def _generate_scenario_background(game_id: str, room_code: str, session_factory):
    from madaminu.services.game_service import GameService

    try:
        await ws_manager.broadcast(
            room_code,
            {
                "type": "progress",
                "data": {"step": "scenario", "status": "in_progress"},
            },
        )

        for attempt in range(3):
            try:
                async with session_factory() as db:
                    _, gen_usages = await generate_scenario(db, game_id)
                    total_cost = sum(u.estimated_cost_usd for u in gen_usages)
                    logger.info(
                        "Scenario generated for %s (attempt %d), cost: $%.4f",
                        room_code,
                        attempt + 1,
                        total_cost,
                    )
                    break
            except Exception:
                logger.exception("Scenario generation attempt %d failed for %s", attempt + 1, room_code)
                if attempt == 2:
                    raise

        await ws_manager.broadcast(
            room_code,
            {
                "type": "progress",
                "data": {"step": "scenario", "status": "done"},
            },
        )

        # Generate images first
        await ws_manager.broadcast(
            room_code,
            {
                "type": "progress",
                "data": {"step": "scene_image", "status": "in_progress"},
            },
        )
        await ws_manager.broadcast(
            room_code,
            {
                "type": "progress",
                "data": {"step": "portraits", "status": "in_progress"},
            },
        )

        await _generate_images(game_id, room_code, session_factory)

        await ws_manager.broadcast(
            room_code,
            {
                "type": "progress",
                "data": {"step": "scene_image", "status": "done"},
            },
        )
        await ws_manager.broadcast(
            room_code,
            {
                "type": "progress",
                "data": {"step": "portraits", "status": "done"},
            },
        )

        # Start first phase after images are ready
        from madaminu.services.discovery_service import DiscoveryService
        from madaminu.ws.actions import _finalize_phase_start

        game_service = GameService(session_factory)
        discovery_service = DiscoveryService(session_factory)
        result = await game_service.advance_phase(game_id, force=True)

        # 1st game.state: phase preparing (includes image URLs)
        await ws_manager.broadcast_game_state(room_code, game_id, game_service)

        # Finalize: wait 3s → ready → 2nd game.state → schedule timer
        if result.phase:
            asyncio.create_task(
                _finalize_phase_start(
                    game_id,
                    room_code,
                    result.phase,
                    discovery_service,
                    game_service,
                    ws_manager,
                )
            )

        await ws_manager.broadcast(room_code, {"type": "game.ready", "data": {"room_code": room_code}})

    except Exception:
        logger.exception("Background scenario generation failed for game %s", game_id)
        try:
            async with session_factory() as db:
                result = await db.execute(select(Game).where(Game.id == game_id))
                game = result.scalar_one_or_none()
                if game and game.status == GameStatus.generating:
                    game.status = GameStatus.waiting
                    await db.commit()
        except Exception:
            logger.exception("Failed to reset game status for %s", game_id)
        await ws_manager.broadcast(room_code, {"type": "game.generation_failed", "data": {"room_code": room_code}})


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

    not_ready = [p for p in game.players if p.character_name and not p.is_ready and not p.is_ai and not p.is_host]
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
        await db.commit()

    validate_transition(game.status, GameStatus.generating)
    game.status = GameStatus.generating
    await db.commit()

    session_factory = getattr(request.app.state, "_session_factory", None) or async_session

    await ws_manager.broadcast(room_code, {"type": "game.generating", "data": {"room_code": room_code}})

    asyncio.create_task(
        _generate_scenario_background(
            game_id=game.id,
            room_code=room_code,
            session_factory=session_factory,
        )
    )

    return StartGameResponse(
        status=game.status,
        total_cost_usd=round(game.total_llm_cost_usd, 4),
    )


class KeepEvidenceRequest(BaseModel):
    discovery_id: str


@router.post("/{room_code}/keep-evidence")
async def keep_evidence_http(
    request: Request,
    room_code: str,
    body: KeepEvidenceRequest,
    x_session_token: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """HTTP endpoint to keep a discovery as evidence."""
    from madaminu.models import Evidence
    from madaminu.services.scenario_engine import keep_evidence

    result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.room_code == room_code))
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404)

    player = next((p for p in game.players if p.session_token == x_session_token), None)
    if player is None:
        raise HTTPException(status_code=403)

    # Check duplicate
    existing = await db.execute(
        select(Evidence).where(
            Evidence.game_id == game.id,
            Evidence.player_id == player.id,
            Evidence.phase_id == game.current_phase_id,
            Evidence.source == "investigation",
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Already kept evidence this phase")

    ev_result = await db.execute(select(Evidence).where(Evidence.id == body.discovery_id))
    ev = ev_result.scalar_one_or_none()
    if ev is None:
        raise HTTPException(status_code=404, detail="Discovery not found")
    discovery = {"id": ev.id, "title": ev.title, "content": ev.content}

    evidence = await keep_evidence(db, game.id, player.id, discovery)
    return {"id": evidence.id, "title": evidence.title, "content": evidence.content}


@router.get("/{room_code}/discoveries")
async def get_discoveries(
    request: Request,
    room_code: str,
    x_session_token: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Get discoveries for current investigation phase from DB."""
    from madaminu.models import Evidence

    result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.room_code == room_code))
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404)

    player = next((p for p in game.players if p.session_token == x_session_token), None)
    if player is None:
        raise HTTPException(status_code=403)

    ev_result = await db.execute(
        select(Evidence).where(
            Evidence.game_id == game.id,
            Evidence.player_id == player.id,
            Evidence.phase_id == game.current_phase_id,
            Evidence.source == "discovery",
        )
    )
    evidences = ev_result.scalars().all()

    discoveries = [
        {"id": e.id, "title": e.title, "content": e.content, "feature": "", "can_tamper": False} for e in evidences
    ]
    return {"discoveries": discoveries}


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

    from madaminu.models import Evidence

    evidence_result = await db.execute(
        select(Evidence).where(Evidence.game_id == game.id).order_by(Evidence.revealed_at)
    )
    all_evidence = evidence_result.scalars().all()
    evidence_by_player: dict[str, list[dict]] = {}
    for ev in all_evidence:
        evidence_by_player.setdefault(ev.player_id, []).append(
            {
                "title": ev.title,
                "content": ev.content,
                "source": ev.source,
            }
        )

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
                "evidences": evidence_by_player.get(p.id, []),
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
