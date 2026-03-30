from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from madaminu.config import settings

_is_sqlite = "sqlite" in settings.async_database_url

if _is_sqlite:
    engine = create_async_engine(settings.async_database_url, echo=settings.debug)
else:
    engine = create_async_engine(
        settings.async_database_url,
        echo=settings.debug,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=300,
    )
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
