#!/bin/sh
set -e

# v3 migration: drop all tables and recreate from scratch
# Remove this block after first successful deploy
if [ "${RESET_DB:-false}" = "true" ]; then
    echo "RESET_DB=true: dropping all tables..."
    uv run python -c "
import asyncio
from sqlalchemy import text
from madaminu.db.database import engine

async def reset():
    async with engine.begin() as conn:
        await conn.execute(text('DROP SCHEMA public CASCADE'))
        await conn.execute(text('CREATE SCHEMA public'))
    await engine.dispose()

asyncio.run(reset())
"
    echo "Database reset complete."
fi

uv run alembic upgrade head
exec uv run uvicorn madaminu.main:app --host 0.0.0.0 --port ${PORT:-8000}
