from contextlib import asynccontextmanager

from fastapi import FastAPI

from madaminu.db.database import engine
from madaminu.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Madaminu API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
