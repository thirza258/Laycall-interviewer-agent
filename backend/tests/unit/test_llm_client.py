import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm.models import LLMRequest, LLMResponse, LLMUsage
from app.llm.client import OpenRouterClient, get_openrouter_client
from app.llm.exceptions import (
    OpenRouterTimeoutError,
    OpenRouterRateLimitError,
    OpenRouterAPIError,
    OpenRouterTruncatedError,
    OpenRouterValidationError,
)


def make_completion(
    content='{"answer": "yes"}',
    finish_reason="stop",
    model="test-model",
    error=None,
    choices=...,
):
    """
    Build a stand-in for an OpenAI ChatCompletion.

    A bare MagicMock auto-creates a truthy `.error`, which a real response
    only carries when the upstream provider failed — so it is set explicitly.
    """
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_choice.finish_reason = finish_reason

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 10
    mock_usage.completion_tokens = 5
    mock_usage.total_tokens = 15

    mock_response = MagicMock()
    mock_response.choices = [mock_choice] if choices is ... else choices
    mock_response.model = model
    mock_response.usage = mock_usage
    mock_response.error = error
    return mock_response


class TestOpenRouterClient:
    """Tests for the OpenRouter client wrapper."""

    @pytest.fixture
    def mock_openai(self):
        with patch("app.llm.client.AsyncOpenAI") as mock:
            yield mock

    @pytest.fixture
    def client(self, mock_openai):
        return OpenRouterClient()

    @pytest.fixture
    def no_sleep(self):
        """Skip retry backoff so retry tests stay fast."""
        with patch("app.llm.client.asyncio.sleep", new=AsyncMock()) as mock:
            yield mock

    def test_client_initialization(self, client, mock_openai):
        """Client should initialize AsyncOpenAI with correct base URL."""
        mock_openai.assert_called_once()
        call_kwargs = mock_openai.call_args.kwargs
        assert call_kwargs["base_url"] == "https://openrouter.ai/api/v1"
        assert "api_key" in call_kwargs

    def test_client_timeout_allows_slow_completions(self, client, mock_openai):
        """Read timeout must be generous; connect timeout must stay short."""
        timeout = mock_openai.call_args.kwargs["timeout"]
        assert timeout.read >= 60.0, "LLM completions routinely exceed a short timeout"
        assert timeout.connect <= 15.0, "Connection failures should fail fast"

    def test_client_retries_transient_failures(self, client, mock_openai):
        """The SDK should be configured to retry transient upstream errors."""
        assert mock_openai.call_args.kwargs["max_retries"] >= 1

    def test_default_headers(self, client):
        """Client should set HTTP-Referer and X-Title headers."""
        assert "HTTP-Referer" in client.default_headers
        assert "X-Title" in client.default_headers
        assert client.default_headers["X-Title"] == "Interviewer Backend"

    @pytest.mark.asyncio
    async def test_generate_completion_success(self, client):
        """Should parse a successful LLM response."""
        mock_response = make_completion('{"answer": "yes"}')
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
    async def test_uses_configured_model_by_default(self, client):
        """A request without a model should use settings.OPENROUTER_MODEL."""
        client.client.chat.completions.create = AsyncMock(return_value=make_completion())

        await client.generate_completion(
            LLMRequest(messages=[{"role": "user", "content": "Hi"}])
        )

        assert client.client.chat.completions.create.call_args.kwargs["model"] == client.default_model

    @pytest.mark.asyncio
    async def test_explicit_model_overrides_default(self, client):
        client.client.chat.completions.create = AsyncMock(return_value=make_completion())

        await client.generate_completion(
            LLMRequest(messages=[{"role": "user", "content": "Hi"}], model="vendor/other")
        )

        assert client.client.chat.completions.create.call_args.kwargs["model"] == "vendor/other"

    @pytest.mark.asyncio
    async def test_inline_error_payload_is_retried(self, client, no_sleep):
        """HTTP 200 with an upstream error payload should be retried, then succeed."""
        client.client.chat.completions.create = AsyncMock(
            side_effect=[
                make_completion(error={"code": 502, "message": "no instances available"}),
                make_completion(content='{"answer": "recovered"}'),
            ]
        )

        request = LLMRequest(messages=[{"role": "user", "content": "Hi"}])
        result = await client.generate_completion(request)

        assert result.content == '{"answer": "recovered"}'
        assert client.client.chat.completions.create.await_count == 2

    @pytest.mark.asyncio
    async def test_inline_error_payload_gives_up_after_retries(self, client, no_sleep):
        """Persistent upstream errors should surface as an API error, not as valid data."""
        client.client.chat.completions.create = AsyncMock(
            return_value=make_completion(error={"code": 503, "message": "provider down"})
        )

        request = LLMRequest(messages=[{"role": "user", "content": "Hi"}])
        with pytest.raises(OpenRouterAPIError):
            await client.generate_completion(request)

        assert client.client.chat.completions.create.await_count == client.max_retries

    @pytest.mark.asyncio
    async def test_inline_rate_limit_is_not_retried(self, client, no_sleep):
        """An inline 429 is a rate limit, not a transient blip."""
        client.client.chat.completions.create = AsyncMock(
            return_value=make_completion(error={"code": 429, "message": "slow down"})
        )

        request = LLMRequest(messages=[{"role": "user", "content": "Hi"}])
        with pytest.raises(OpenRouterRateLimitError):
            await client.generate_completion(request)

        assert client.client.chat.completions.create.await_count == 1

    @pytest.mark.asyncio
    async def test_inline_client_error_is_not_retried(self, client, no_sleep):
        """A bad key or missing credits will not fix itself; fail immediately."""
        client.client.chat.completions.create = AsyncMock(
            return_value=make_completion(error={"code": 401, "message": "invalid api key"})
        )

        request = LLMRequest(messages=[{"role": "user", "content": "Hi"}])
        with pytest.raises(OpenRouterAPIError):
            await client.generate_completion(request)

        assert client.client.chat.completions.create.await_count == 1

    @pytest.mark.asyncio
    async def test_missing_choices_is_retried(self, client, no_sleep):
        client.client.chat.completions.create = AsyncMock(
            side_effect=[make_completion(choices=[]), make_completion()]
        )

        request = LLMRequest(messages=[{"role": "user", "content": "Hi"}])
        result = await client.generate_completion(request)

        assert result.content == '{"answer": "yes"}'
        assert client.client.chat.completions.create.await_count == 2

    @pytest.mark.asyncio
    async def test_empty_content_is_retried(self, client, no_sleep):
        client.client.chat.completions.create = AsyncMock(
            side_effect=[make_completion(content="   "), make_completion()]
        )

        request = LLMRequest(messages=[{"role": "user", "content": "Hi"}])
        result = await client.generate_completion(request)

        assert result.content == '{"answer": "yes"}'
        assert client.client.chat.completions.create.await_count == 2

    @pytest.mark.asyncio
    async def test_truncated_response_names_the_cause(self, client, no_sleep):
        """finish_reason=length means a token budget problem, not invalid JSON."""
        client.client.chat.completions.create = AsyncMock(
            return_value=make_completion(content='{"questions": [', finish_reason="length")
        )

        request = LLMRequest(messages=[{"role": "user", "content": "Hi"}])
        with pytest.raises(OpenRouterTruncatedError) as exc_info:
            await client.generate_completion(request)

        assert "token limit" in str(exc_info.value)
        assert client.client.chat.completions.create.await_count == 1

    @pytest.mark.asyncio
    async def test_token_limit_with_complete_json_is_kept(self, client, no_sleep):
        """Hitting the cap after the JSON closed is not a failure."""
        client.client.chat.completions.create = AsyncMock(
            return_value=make_completion(content='{"ok": true}\n', finish_reason="length")
        )

        request = LLMRequest(messages=[{"role": "user", "content": "Hi"}])
        result = await client.generate_completion(request)

        assert result.content == '{"ok": true}\n'

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
