"""Shared test fixtures.

The suite runs with no external services: SQLite stands in for PostgreSQL,
and the OpenRouter and MinIO clients are stubbed at their boundaries. Set
TEST_DATABASE_URL to run the same tests against a real PostgreSQL instance.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Ensure the backend directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:"
)

# These must be set before any app module is imported: app.db.session builds
# its engine at import time, and Settings would otherwise read a developer's
# .env — pointing the suite at a real database.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
# Forced empty rather than merely unset: app.core.config calls load_dotenv(),
# which copies a developer's .env into the environment. Real credentials there
# sent unstubbed code paths to live object storage (a 6s DNS timeout per test).
# Empty means any such path fails immediately with "not configured".
for _storage_var in (
    "MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "MINIO_PUBLIC_URL"
):
    os.environ[_storage_var] = ""


# A single payload that satisfies every agent schema at once (each model
# ignores the keys it does not declare). One fake response therefore carries
# the whole pipeline — JD parse, resume analysis, gap analysis, spec build,
# question generation, answer evaluation and final review.
FAKE_LLM_PAYLOAD = {
    "job_title": "Senior Backend Engineer",
    "company": "Acme",
    "required_skills": ["Python", "FastAPI"],
    "preferred_skills": ["Kubernetes"],
    "responsibilities": ["Build APIs"],
    "education": ["BSc Computer Science"],
    "skills": ["Python", "SQL"],
    "projects": ["Interview platform"],
    "experience": ["5 years backend"],
    "matched_skills": ["Python"],
    "missing_skills": ["Kubernetes"],
    "strengths": ["Clear communicator"],
    "focus_areas": ["Container orchestration"],
    "target_role": "Senior Backend Engineer",
    "difficulty": "senior",
    "candidate_strengths": ["Async Python"],
    "candidate_gaps": ["Kubernetes"],
    "questions": [
        {"question": "Explain async/await.", "type": "technical", "difficulty": "medium"},
        {"question": "Describe a hard bug you fixed.", "type": "behavioral", "difficulty": "easy"},
    ],
    "technical_score": 8,
    "communication_score": 9,
    "feedback": "Solid answer with concrete examples and a clear structure.",
    "overall_score": 82,
    "weaknesses": ["Limited Kubernetes exposure"],
    "recommendations": ["Proceed to the system design round"],
}


@pytest_asyncio.fixture
async def test_engine():
    """A fresh schema per test.

    Every endpoint commits for real, so rolling back after a test isolates
    nothing. An in-memory database on a StaticPool (one shared connection)
    is both properly isolated and fast.
    """
    is_sqlite = TEST_DATABASE_URL.startswith("sqlite")
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
        poolclass=StaticPool if is_sqlite else None,
        connect_args={"check_same_thread": False} if is_sqlite else {},
    )

    if is_sqlite:
        # SQLite ignores ON DELETE CASCADE unless foreign keys are switched on
        # per connection, which the cascade tests rely on.
        @event.listens_for(engine.sync_engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record):  # pragma: no cover
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    from app.db.base import Base
    from app.db import models  # noqa: F401 — registers every table on Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Per-test async session bound to the per-test schema."""
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
def fake_llm_response():
    """The LLMResponse every stubbed completion returns."""
    from app.llm.models import LLMResponse

    return LLMResponse(
        content=json.dumps(FAKE_LLM_PAYLOAD),
        model="fake/model",
        finish_reason="stop",
    )


@pytest.fixture
def fake_llm_client(fake_llm_response):
    """Stand-in for OpenRouterClient that never touches the network."""
    from app.llm.client import OpenRouterClient

    client = AsyncMock(spec=OpenRouterClient)
    client.generate_completion = AsyncMock(return_value=fake_llm_response)
    return client


@pytest_asyncio.fixture
async def test_client(db_session, fake_llm_client):
    """Async HTTP client for testing FastAPI endpoints."""
    from app.db.session import get_db
    from app.llm.client import get_openrouter_client
    from main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_openrouter_client] = lambda: fake_llm_client

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_process_state():
    """Clear the module-level caches that would otherwise leak between tests."""
    from app.core.minio_client import MinIOClient
    from app.llm.client import get_openrouter_client
    from app.services import interview_orchestration

    def reset():
        MinIOClient._instance = None
        # Tests that patch the OpenAI SDK leave a client whose transport is a
        # mock in this cache; anything resolving the real dependency later
        # would pick it up.
        get_openrouter_client.cache_clear()
        interview_orchestration._generation_locks.clear()

    reset()
    yield
    reset()
