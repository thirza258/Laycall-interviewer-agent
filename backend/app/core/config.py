from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from sqlalchemy.engine import URL

# Pick up a .env from the project root so a local run sees the same values
# docker compose passes in as environment variables.
load_dotenv()


class Settings(BaseSettings):
    # Defaults below are plain literals on purpose. Calling os.getenv() in a
    # field default freezes the value at import time — before the process
    # environment or .env can be overridden — which made settings depend on
    # import order. pydantic-settings reads the environment when Settings()
    # is constructed instead.
    APP_NAME: str = "My Mock Interview"

    DB_USER: str = "pasal_user"
    DB_PASSWORD: str = "pasal_password"
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "pasal_db"

    # A complete SQLAlchemy URL. When set it wins over the DB_* parts, so a
    # deployment can point at a managed database — and the test suite at
    # SQLite — without restating every component.
    DB_URL: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "DB_URL"),
        description="Full SQLAlchemy URL; overrides the DB_* components.",
    )

    OPENROUTER_API_KEY: str = "your_default_api_key"
    OPENROUTER_MODEL: str = "google/gemma-4-26b-a4b-it"

    # Read timeout for a single completion. LLM calls that generate a full
    # question set routinely need 30-60s, so this must be generous.
    OPENROUTER_TIMEOUT: float = 90.0
    # Connect timeout stays short so genuine network failures fail fast.
    OPENROUTER_CONNECT_TIMEOUT: float = 10.0
    # Retries for transient upstream failures (429, 5xx, timeouts, dropped
    # connections). Applied by the SDK and by our own soft-failure loop.
    OPENROUTER_MAX_RETRIES: int = 3

    # Ceiling for the whole five-call question generation pipeline. Must stay
    # below the reverse proxy's read timeout (300s in frontend/nginx.conf) so
    # the request fails with a real message instead of a dropped connection.
    QUESTION_GENERATION_TIMEOUT: float = 240.0

    # Storage is optional at import time: migrations, the health check and the
    # test suite must all work on a host with no object storage configured.
    # Uploads then fail with a named error instead of the whole process
    # refusing to start.
    MINIO_ENDPOINT: str | None = None
    MINIO_ACCESS_KEY: str | None = None
    MINIO_SECRET_KEY: str | None = None
    MINIO_BUCKET: str = "wallpapers"
    MINIO_SECURE: bool = True
    MINIO_PUBLIC_URL: str | None = None

    APP_ENV: str = "development"
    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def DATABASE_CONFIG(self) -> dict:
        return {
            "user": self.DB_USER,
            "password": self.DB_PASSWORD,
            "host": self.DB_HOST,
            "port": self.DB_PORT,
            "database": self.DB_NAME
        }

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_URL:
            return self.DB_URL
        return URL.create(
            "postgresql+asyncpg",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=int(self.DB_PORT),
            database=self.DB_NAME,
        ).render_as_string(hide_password=False)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
