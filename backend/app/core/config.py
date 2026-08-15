from functools import lru_cache
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()  

class Settings(BaseSettings):
    APP_NAME: str = "My Mock Interview"
    
    
    DB_USER: str = os.getenv("DB_USER", "pasal_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "pasal_password")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "pasal_db")
    
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "your_default_api_key")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "google/gemma-4-26b-a4b-it")

    # Read timeout for a single completion. LLM calls that generate a full
    # question set routinely need 30-60s, so this must be generous.
    OPENROUTER_TIMEOUT: float = float(os.getenv("OPENROUTER_TIMEOUT", "90"))
    # Connect timeout stays short so genuine network failures fail fast.
    OPENROUTER_CONNECT_TIMEOUT: float = float(os.getenv("OPENROUTER_CONNECT_TIMEOUT", "10"))
    # Retries for transient upstream failures (429, 5xx, timeouts, dropped
    # connections). Applied by the SDK and by our own soft-failure loop.
    OPENROUTER_MAX_RETRIES: int = int(os.getenv("OPENROUTER_MAX_RETRIES", "3"))

    # Ceiling for the whole five-call question generation pipeline. Must stay
    # below the reverse proxy's read timeout (300s in frontend/nginx.conf) so
    # the request fails with a real message instead of a dropped connection.
    QUESTION_GENERATION_TIMEOUT: float = float(
        os.getenv("QUESTION_GENERATION_TIMEOUT", "240")
    )
    
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "wallpapers")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "True").lower() == "true"
    MINIO_PUBLIC_URL: str = os.getenv("MINIO_PUBLIC_URL")

    APP_ENV: str = "development"
    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
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
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

@lru_cache()
def get_settings() -> Settings:
    return Settings()