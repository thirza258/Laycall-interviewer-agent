import os
from unittest.mock import patch

from app.core.config import Settings, get_settings


class TestSettings:
    def test_default_values(self):
        """Settings should return defaults when no env vars are set."""
        with patch.dict(os.environ, {}, clear=True):
            # Reload to pick up empty env
            settings = Settings(_env_file=None)

            assert settings.APP_NAME == "My Mock Interview"
            assert settings.APP_ENV == "development"
            assert settings.DEBUG is False
            assert settings.DB_USER == "pasal_user"
            assert settings.DB_PASSWORD == "pasal_password"
            assert settings.DB_HOST == "localhost"
            assert settings.DB_PORT == "5432"
            assert settings.DB_NAME == "pasal_db"
            assert settings.OPENROUTER_API_KEY == "your_default_api_key"
            assert settings.OPENROUTER_MODEL == "google/gemma-4-26b-a4b-it"
            assert settings.MINIO_BUCKET == "wallpapers"
            assert settings.MINIO_SECURE is True

    def test_env_override(self):
        """Settings should read from environment variables."""
        env_vars = {
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "DB_HOST": "testhost",
            "DB_PORT": "9999",
            "DB_NAME": "testdb",
            "OPENROUTER_API_KEY": "sk-test",
            "MINIO_SECURE": "false",
            "DEBUG": "true",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings(_env_file=None)

            assert settings.DB_USER == "testuser"
            assert settings.DB_PASSWORD == "testpass"
            assert settings.DB_HOST == "testhost"
            assert settings.DB_PORT == "9999"
            assert settings.DB_NAME == "testdb"
            assert settings.OPENROUTER_API_KEY == "sk-test"
            assert settings.MINIO_SECURE is False
            assert settings.DEBUG is True

    def test_database_url_property(self):
        """DATABASE_URL should build a valid async postgres connection string."""
        env_vars = {
            "DB_USER": "u",
            "DB_PASSWORD": "p",
            "DB_HOST": "h",
            "DB_PORT": "5432",
            "DB_NAME": "d",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings(_env_file=None)

            expected = "postgresql+asyncpg://u:p@h:5432/d"
            assert settings.DATABASE_URL == expected

    def test_database_config_property(self):
        """DATABASE_CONFIG should return a dict with connection details."""
        env_vars = {
            "DB_USER": "u",
            "DB_PASSWORD": "p",
            "DB_HOST": "h",
            "DB_PORT": "5432",
            "DB_NAME": "d",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings(_env_file=None)

            config = settings.DATABASE_CONFIG
            assert config == {
                "user": "u",
                "password": "p",
                "host": "h",
                "port": "5432",
                "database": "d",
            }

    def test_get_settings_is_singleton(self):
        """get_settings() should return the same instance each call."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
