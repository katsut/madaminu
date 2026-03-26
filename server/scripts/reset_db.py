"""Drop all tables and types, then let alembic recreate them."""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from madaminu.config import settings


async def reset():
    engine = create_async_engine(settings.async_database_url)
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        print("Database reset complete.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(reset())
