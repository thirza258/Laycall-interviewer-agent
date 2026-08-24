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


class TestDatabaseUrlOverride:
    def test_db_url_overrides_the_components(self):
        """A full URL wins over the DB_* parts, which is how the suite and
        single-URL deployments point at another database."""
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite+aiosqlite:///:memory:"}, clear=True):
            settings = Settings(_env_file=None)

            assert settings.DB_URL == "sqlite+aiosqlite:///:memory:"
            assert settings.DATABASE_URL == "sqlite+aiosqlite:///:memory:"

    def test_db_url_alias_is_also_accepted(self):
        with patch.dict(os.environ, {"DB_URL": "postgresql+asyncpg://a:b@c:1/d"}, clear=True):
            assert Settings(_env_file=None).DATABASE_URL == "postgresql+asyncpg://a:b@c:1/d"

    def test_components_are_used_when_no_url_is_set(self):
        env = {"DB_USER": "u", "DB_PASSWORD": "p", "DB_HOST": "h", "DB_PORT": "1", "DB_NAME": "n"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

            assert settings.DB_URL is None
            assert settings.DATABASE_URL == "postgresql+asyncpg://u:p@h:1/n"

    def test_environment_is_read_at_construction_not_at_import(self):
        """Defaults used to be captured by os.getenv() in the class body, so a
        value exported after import was ignored and the settings depended on
        import order."""
        with patch.dict(os.environ, {"DB_NAME": "first"}, clear=True):
            assert Settings(_env_file=None).DB_NAME == "first"
        with patch.dict(os.environ, {"DB_NAME": "second"}, clear=True):
            assert Settings(_env_file=None).DB_NAME == "second"

    def test_storage_settings_are_optional(self):
        """The app has to import and migrate on a host with no storage
        credentials; uploads fail on their own instead."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None)

            assert settings.MINIO_ENDPOINT is None
            assert settings.MINIO_ACCESS_KEY is None
            assert settings.MINIO_SECRET_KEY is None
            assert settings.MINIO_PUBLIC_URL is None
