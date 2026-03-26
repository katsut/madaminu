import contextlib
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, WebSocket
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from madaminu.config import settings
from madaminu.db import get_db
from madaminu.db.database import async_session, engine
from madaminu.models import Base
from madaminu.events import EventBus, ImagesReady, ScenarioReady
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

    yield

    if not settings.testing:
        await engine.dispose()


app = FastAPI(title="Madaminu API", version="0.1.0", lifespan=lifespan)
app.include_router(rooms_router)
app.include_router(characters_router)
app.include_router(game_router)
app.include_router(images_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.websocket("/ws/{room_code}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, db: AsyncSession = Depends(get_db)):
    await handle_websocket(websocket, room_code, db)
