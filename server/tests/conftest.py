import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from madaminu.db.database import get_db
from madaminu.main import app
from madaminu.models import Base

TEST_DATABASE_URL = "sqlite+aiosqlite://"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
