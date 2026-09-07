"""The FastAPI application object and its lifespan."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import main
from app.llm.client import get_openrouter_client


class TestApplication:
    def test_routers_are_mounted(self):
        paths = {route.path for route in main.app.routes if hasattr(route, "path")}

        assert "/health" in paths
        assert "/api/v1/resumes" in paths
        assert "/api/v1/interviews" in paths
        assert "/api/v1/interviews/{interview_id}/question" in paths
        assert "/api/v1/interviews/{interview_id}/results" in paths
        assert "/api/v1/interviews/{interview_id}/answers" in paths
        assert "/api/v1/interviews/{interview_id}/answers/{answer_id}/evaluate" in paths

    def test_openapi_schema_builds(self):
        """A schema that cannot be generated means /docs is broken."""
        schema = main.app.openapi()

        assert schema["info"]["title"] == main.settings.APP_NAME
        assert "/api/v1/resumes" in schema["paths"]


class TestLifespan:
    def test_startup_serves_requests_and_shutdown_disposes_the_engine(self, monkeypatch):
        engine = MagicMock()
        engine.dispose = AsyncMock()
        monkeypatch.setattr(main, "engine", engine)

        with TestClient(main.app) as client:
            assert client.get("/health").json() == {
                "status": "healthy",
                "env": main.settings.APP_ENV,
            }

        engine.dispose.assert_awaited_once()

    def test_shutdown_closes_the_llm_client(self, monkeypatch):
        engine = MagicMock()
        engine.dispose = AsyncMock()
        monkeypatch.setattr(main, "engine", engine)

        with patch("app.llm.client.AsyncOpenAI") as sdk:
            sdk.return_value.close = AsyncMock()
            get_openrouter_client()  # build the singleton this run would use
            assert get_openrouter_client.cache_info().currsize == 1

            with TestClient(main.app):
                pass

            sdk.return_value.close.assert_awaited_once()

        # The singleton is dropped so a restart builds a fresh pool.
        assert get_openrouter_client.cache_info().currsize == 0

    def test_shutdown_does_not_build_a_client_it_never_used(self, monkeypatch):
        engine = MagicMock()
        engine.dispose = AsyncMock()
        monkeypatch.setattr(main, "engine", engine)

        with patch("app.llm.client.AsyncOpenAI") as sdk:
            with TestClient(main.app):
                pass

            sdk.assert_not_called()

    def test_cleanup_continues_after_a_failing_step(self, monkeypatch):
        """A failure closing the database pool used to skip closing the LLM
        pool as well, because both shared one try block."""
        engine = MagicMock()
        engine.dispose = AsyncMock(side_effect=RuntimeError("pool already closed"))
        monkeypatch.setattr(main, "engine", engine)

        with patch("app.llm.client.AsyncOpenAI") as sdk:
            sdk.return_value.close = AsyncMock()
            get_openrouter_client()

            with TestClient(main.app) as client:
                assert client.get("/health").status_code == 200

            sdk.return_value.close.assert_awaited_once()

        assert get_openrouter_client.cache_info().currsize == 0


class TestHealthCheck:
    def test_reports_the_configured_environment(self):
        with TestClient(main.app) as client:
            body = client.get("/health").json()

        assert body["status"] == "healthy"
        assert body["env"] == main.settings.APP_ENV

    def test_a_failing_llm_close_does_not_break_shutdown(self, monkeypatch):
        """Shutdown must finish even when closing the LLM pool raises.

        The singleton is still dropped, so a restart does not inherit a client
        whose transport is already broken.
        """
        engine = MagicMock()
        engine.dispose = AsyncMock()
        monkeypatch.setattr(main, "engine", engine)

        with patch("app.llm.client.AsyncOpenAI") as sdk:
            sdk.return_value.close = AsyncMock(side_effect=RuntimeError("transport gone"))
            get_openrouter_client()

            with TestClient(main.app) as client:
                assert client.get("/health").status_code == 200

            sdk.return_value.close.assert_awaited_once()

        engine.dispose.assert_awaited_once()
        assert get_openrouter_client.cache_info().currsize == 0
