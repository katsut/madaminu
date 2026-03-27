import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, WebSocket
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.config import settings
from madaminu.db import get_db
from madaminu.db.database import async_session, engine
from madaminu.models import Base, Game, GameStatus
from madaminu.events import EventBus, ImagesReady, ScenarioReady

logger = logging.getLogger(__name__)
from madaminu.routers.characters import router as characters_router
from madaminu.routers.game import router as game_router
from madaminu.routers.images import router as images_router
from madaminu.routers.rooms import router as rooms_router
from madaminu.services.phase_manager import PhaseManager
from madaminu.services.speech_manager import SpeechManager
from madaminu.ws.handler import handle_websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.testing:
        # Alembic handles migrations on startup via Dockerfile CMD

        event_bus = EventBus()
        app.state.event_bus = event_bus
        app.state.phase_manager = PhaseManager(async_session)
        app.state.speech_manager = SpeechManager(async_session)

        event_bus.on(ScenarioReady, lambda e: None)
        event_bus.on(ImagesReady, lambda e: None)

        asyncio.create_task(_cleanup_old_rooms())

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
                select(Game)
                .where(Game.created_at < cutoff, Game.status.in_([GameStatus.ended, GameStatus.waiting]))
            )
            old_games = result.scalars().all()
            for game in old_games:
                await db.delete(game)
            if old_games:
                await db.commit()
                logger.info("Cleaned up %d old rooms", len(old_games))
    except Exception:
        logger.exception("Room cleanup failed")


DEPLOY_VERSION = "2026-03-27T04"


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": DEPLOY_VERSION}


@app.get("/debug/llm-test")
async def llm_test():
    from madaminu.llm.client import llm_client
    try:
        text, usage = await llm_client.generate(
            "You are a test assistant.", "Say hello in JSON: {\"message\": \"hello\"}", max_tokens=100
        )
        return {"text": text, "usage": str(usage), "model": usage.model}
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}


@app.websocket("/ws/{room_code}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, db: AsyncSession = Depends(get_db)):
    await handle_websocket(websocket, room_code, db)
