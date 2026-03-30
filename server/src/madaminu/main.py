import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from madaminu.config import settings
from madaminu.db import get_db
from madaminu.db.database import async_session, engine
from madaminu.events import EventBus, ImagesReady, ScenarioReady
from madaminu.models import Game, GameStatus
from madaminu.routers.characters import router as characters_router
from madaminu.routers.game import router as game_router
from madaminu.routers.images import router as images_router
from madaminu.routers.rooms import router as rooms_router
from madaminu.services.phase_manager import PhaseManager
from madaminu.services.speech_manager import SpeechManager
from madaminu.ws.handler import handle_websocket

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.testing:
        async with engine.begin() as conn:
            from madaminu.models import Base

            await conn.run_sync(Base.metadata.create_all)

    app.state.phase_manager = PhaseManager(async_session)
    app.state.speech_manager = SpeechManager(async_session)

    if not settings.testing:
        event_bus = EventBus()
        app.state.event_bus = event_bus

        event_bus.on(ScenarioReady, lambda e: None)
        event_bus.on(ImagesReady, lambda e: None)

        asyncio.create_task(_cleanup_old_rooms())
        asyncio.create_task(_restore_active_timers(app.state.phase_manager))

    yield

    if not settings.testing:
        await engine.dispose()


app = FastAPI(title="Madaminu API", version="0.1.0", lifespan=lifespan)
app.include_router(rooms_router)
app.include_router(characters_router)
app.include_router(game_router)
app.include_router(images_router)


async def _cleanup_old_rooms():
    cutoff = datetime.utcnow() - timedelta(hours=24)
    try:
        async with async_session() as db:
            result = await db.execute(
                select(Game).where(Game.created_at < cutoff, Game.status.in_([GameStatus.ended, GameStatus.waiting]))
            )
            old_games = result.scalars().all()
            for game in old_games:
                await db.delete(game)
            if old_games:
                await db.commit()
                logger.info("Cleaned up %d old rooms", len(old_games))
    except Exception:
        logger.exception("Room cleanup failed")


async def _restore_active_timers(pm: PhaseManager):
    """Restore timers for games that are currently playing after server restart."""
    from madaminu.models import Phase

    try:
        async with async_session() as db:
            result = await db.execute(
                select(Game).where(Game.status.in_([GameStatus.playing, GameStatus.voting]))
            )
            active_games = result.scalars().all()

            for game in active_games:
                if not game.current_phase_id:
                    continue
                phase_result = await db.execute(select(Phase).where(Phase.id == game.current_phase_id))
                phase = phase_result.scalar_one_or_none()
                if phase and phase.started_at and phase.duration_sec:
                    logger.info(
                        "Restoring timer for game %s phase %s (%s)",
                        game.room_code,
                        phase.phase_type,
                        phase.id,
                    )
                    pm._start_timer(game.id, game.room_code, phase)
    except Exception:
        logger.exception("Timer restoration failed")


DEPLOY_VERSION = "2026-03-30T15"


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": DEPLOY_VERSION}


@app.get("/debug/timers")
async def debug_timers():
    pm = getattr(app.state, "phase_manager", None)
    if not pm:
        return {"error": "no phase_manager"}

    timers = {}
    for game_id, task in pm._timers.items():
        timers[game_id] = {"done": task.done(), "cancelled": task.cancelled()}

    advancing = list(getattr(pm, "_advancing_rooms", set()) if hasattr(pm, "_advancing_rooms") else [])

    # Check active games
    games_info = []
    try:
        async with async_session() as db:
            result = await db.execute(
                select(Game).where(Game.status.in_([GameStatus.playing, GameStatus.voting]))
            )
            from madaminu.models import Phase
            for game in result.scalars().all():
                phase = None
                if game.current_phase_id:
                    pr = await db.execute(select(Phase).where(Phase.id == game.current_phase_id))
                    phase = pr.scalar_one_or_none()
                games_info.append({
                    "room_code": game.room_code,
                    "game_id": game.id,
                    "status": game.status,
                    "current_phase": phase.phase_type if phase else None,
                    "deadline_at": str(phase.deadline_at) if phase and phase.deadline_at else None,
                    "started_at": str(phase.started_at) if phase and phase.started_at else None,
                    "has_timer": game.id in pm._timers,
                })
    except Exception as e:
        games_info = [{"error": str(e)}]

    return {"timers": timers, "advancing_rooms": advancing, "games": games_info}


@app.get("/debug/llm-test")
async def llm_test():
    from madaminu.llm.client import llm_client

    try:
        text, usage = await llm_client.generate(
            "You are a test assistant.", 'Say hello in JSON: {"message": "hello"}', max_tokens=100
        )
        return {"text": text, "usage": str(usage), "model": usage.model}
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}


@app.websocket("/ws/{room_code}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, db: AsyncSession = Depends(get_db)):
    await handle_websocket(websocket, room_code, db)
