import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import get_settings
from app.db.session import engine 
from app.api.endpoints import resumes, interviews, answers, hr_interviews
from app.llm.client import get_openrouter_client


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown lifecycle."""

    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")
    yield

    logger.info("Shutting down gracefully...")
    await _release_resources()


async def _release_resources() -> None:
    """Close both connection pools, independently.

    One shared try block meant a failure closing the database pool also
    skipped closing the LLM pool.
    """
    try:
        await engine.dispose()  # Close async DB connection pool
    except Exception as e:
        logger.warning(f"Database engine cleanup failed: {e}")

    # Only touch the LLM client if something actually built one — calling the
    # factory here would construct a fresh client just to close it.
    if not get_openrouter_client.cache_info().currsize:
        return

    try:
        await get_openrouter_client().close()  # Close LLM HTTP connection pool
    except Exception as e:
        logger.warning(f"LLM client cleanup failed: {e}")
    finally:
        get_openrouter_client.cache_clear()  # Reset singleton for clean state

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.include_router(resumes.router)
app.include_router(interviews.router)
app.include_router(answers.router)
app.include_router(hr_interviews.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "env": settings.APP_ENV}
