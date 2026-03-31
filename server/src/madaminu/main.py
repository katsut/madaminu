import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, WebSocket
from sqlalchemy import select

from madaminu.config import settings
from madaminu.db.database import async_session, engine
from madaminu.models import Game, GameStatus
from madaminu.routers.characters import router as characters_router
from madaminu.routers.game import router as game_router
from madaminu.routers.images import router as images_router
from madaminu.routers.rooms import router as rooms_router
from madaminu.ws.handler_v3 import handle_websocket_v3, start_ping_task, ws_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.testing:
        async with engine.begin() as conn:
            from madaminu.models import Base

            await conn.run_sync(Base.metadata.create_all)

    app.state.ws_manager = ws_manager
    app.state.session_factory = async_session

    if not settings.testing:
        asyncio.create_task(_cleanup_old_rooms())
        asyncio.create_task(start_ping_task())

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


DEPLOY_VERSION = "2026-03-31T01"


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": DEPLOY_VERSION}


@app.websocket("/ws/{room_code}")
async def websocket_endpoint(websocket: WebSocket, room_code: str):
    sf = websocket.app.state.session_factory
    await handle_websocket_v3(websocket, room_code, sf)
