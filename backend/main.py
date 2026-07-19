import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import get_settings
from app.db.session import engine 
from app.api.endpoints import resume, interviews, answer
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
    try:
        await engine.dispose()  # Close async DB connection pool
        client = get_openrouter_client()
        await client.close()    # Close LLM HTTP connection pool
        get_openrouter_client.cache_clear()  # Reset singleton for clean state
    except Exception as e:
        logger.warning(f"Cleanup failed: {e}")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.include_router(resume.router)
app.include_router(interviews.router)
app.include_router(answer.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "env": settings.APP_ENV}