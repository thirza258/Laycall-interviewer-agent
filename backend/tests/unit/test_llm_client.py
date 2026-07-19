import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm.models import LLMRequest, LLMResponse, LLMUsage
from app.llm.client import OpenRouterClient, get_openrouter_client
from app.llm.exceptions import (
    OpenRouterTimeoutError,
    OpenRouterRateLimitError,
    OpenRouterAPIError,
    OpenRouterValidationError,
)


class TestOpenRouterClient:
    """Tests for the OpenRouter client wrapper."""

    @pytest.fixture
    def mock_openai(self):
        with patch("app.llm.client.AsyncOpenAI") as mock:
            yield mock

    @pytest.fixture
    def client(self, mock_openai):
        return OpenRouterClient()

    def test_client_initialization(self, client, mock_openai):
        """Client should initialize AsyncOpenAI with correct base URL."""
        mock_openai.assert_called_once()
        call_kwargs = mock_openai.call_args.kwargs
        assert call_kwargs["base_url"] == "https://openrouter.ai/api/v1"
        assert call_kwargs["timeout"] == 10.0
        assert "api_key" in call_kwargs

    def test_default_headers(self, client):
        """Client should set HTTP-Referer and X-Title headers."""
        assert "HTTP-Referer" in client.default_headers
        assert "X-Title" in client.default_headers
        assert client.default_headers["X-Title"] == "Interviewer Backend"

    @pytest.mark.asyncio
    async def test_generate_completion_success(self, client):
        """Should parse a successful LLM response."""
        mock_choice = MagicMock()
        mock_choice.message.content = '{"answer": "yes"}'
        mock_choice.finish_reason = "stop"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 5
        mock_usage.total_tokens = 15

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "test-model"
        mock_response.usage = mock_usage

        client.client.chat.completions.create = AsyncMock(return_value=mock_response)

        request = LLMRequest(messages=[{"role": "user", "content": "Are you there?"}])
        result = await client.generate_completion(request)

        assert result.content == '{"answer": "yes"}'
        assert result.model == "test-model"
        assert result.finish_reason == "stop"
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 5
        assert result.usage.total_tokens == 15

    @pytest.mark.asyncio
    async def test_generate_completion_timeout(self, client):
        """Should raise OpenRouterTimeoutError on timeout."""
        from openai import APITimeoutError

        client.client.chat.completions.create = AsyncMock(
            side_effect=APITimeoutError(request=MagicMock())
        )
        request = LLMRequest(messages=[{"role": "user", "content": "Hi"}])

        with pytest.raises(OpenRouterTimeoutError):
            await client.generate_completion(request)

    @pytest.mark.asyncio
    async def test_generate_completion_rate_limit(self, client):
        """Should raise OpenRouterRateLimitError on 429."""
        from openai import RateLimitError

        client.client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError(
                message="rate limited", response=MagicMock(), body={}
            )
        )
        request = LLMRequest(messages=[{"role": "user", "content": "Hi"}])

        with pytest.raises(OpenRouterRateLimitError):
            await client.generate_completion(request)

    @pytest.mark.asyncio
    async def test_generate_completion_api_error(self, client):
        """Should raise OpenRouterAPIError on API error."""
        from openai import APIError

        client.client.chat.completions.create = AsyncMock(
            side_effect=APIError(
                message="internal error",
                request=MagicMock(),
                body={"error": "boom"},
            )
        )
        request = LLMRequest(messages=[{"role": "user", "content": "Hi"}])

        with pytest.raises(OpenRouterAPIError) as exc_info:
            await client.generate_completion(request)

        assert "internal error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_completion_connection_error(self, client):
        """Should raise OpenRouterAPIError on connection error."""
        from openai import APIConnectionError

        client.client.chat.completions.create = AsyncMock(
            side_effect=APIConnectionError(request=MagicMock())
        )
        request = LLMRequest(messages=[{"role": "user", "content": "Hi"}])

        with pytest.raises(OpenRouterAPIError):
            await client.generate_completion(request)

    @pytest.mark.asyncio
    async def test_close(self, client):
        """close() should delegate to the underlying client."""
        client.client.close = AsyncMock()
        await client.close()
        client.client.close.assert_awaited_once()


class TestGetOpenRouterClient:
    def test_singleton(self):
        """get_openrouter_client should return cached singleton."""
        # Clear the LRU cache before testing
        get_openrouter_client.cache_clear()

        with patch("app.llm.client.OpenRouterClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            c1 = get_openrouter_client()
            c2 = get_openrouter_client()
            assert c1 is c2
            assert mock_cls.call_count == 1
