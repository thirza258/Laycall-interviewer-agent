import asyncio
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure the backend directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Prevent the real .env from being loaded during tests
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DEBUG", "false")


def build_test_db_url() -> str:
    """Build a test database URL.

    Uses TEST_DATABASE_URL env var if set, otherwise derives from the
    real database URL by appending _test to the database name.
    """
    override = os.environ.get("TEST_DATABASE_URL")
    if override:
        return override

    from app.core.config import get_settings

    settings = get_settings()
    url = settings.DATABASE_URL
    db_name = settings.DB_NAME
    test_db_name = f"{db_name}_test"
    return url.replace(f"/{db_name}", f"/{test_db_name}")


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Session-scoped async engine connected to the test database."""
    db_url = build_test_db_url()
    engine = create_async_engine(db_url, echo=False, future=True)

    # Create all tables from SQLAlchemy metadata
    from app.db.base import Base
    from app.db.models import (  # noqa: F401 — ensure all models are imported
        Interview,
        Resume,
        JobDescription,
        InterviewSpec,
        Question,
        Answer,
        Evaluation,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Per-test async session. Rolls back after each test."""
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_client(db_session):
    """Async HTTP client for testing FastAPI endpoints."""
    from app.db.session import get_db
    from main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
