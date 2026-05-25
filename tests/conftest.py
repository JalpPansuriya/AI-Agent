import asyncio
import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings

@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    """Ensure database tables exist before running tests."""
    temp_engine = create_async_engine(settings.DATABASE_URL, future=True)
    async with temp_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await temp_engine.dispose()
    yield

@pytest.fixture
async def engine() -> AsyncGenerator:
    """Provide a function-scoped async engine bound to the current test's loop."""
    engine = create_async_engine(settings.DATABASE_URL, future=True)
    yield engine
    await engine.dispose()

@pytest.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session that rolls back after each test."""
    TestSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = TestSessionLocal(bind=connection)
        
        yield session
        
        await session.close()
        await transaction.rollback()

@pytest.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTPX AsyncClient configured to use our test database session."""
    # Override get_db dependency to yield our transactional test session
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    
    # Configure ASGI transport to run the app in-process
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
async def cleanup_redis():
    """Flush Redis database and disconnect the connection pool after each test case to avoid closed loop errors."""
    from app.core.redis import redis_client
    try:
        await redis_client.flushdb()
    except Exception:
        pass
    yield
    try:
        if hasattr(redis_client, "connection_pool") and redis_client.connection_pool:
            await redis_client.connection_pool.disconnect()
    except Exception:
        pass
