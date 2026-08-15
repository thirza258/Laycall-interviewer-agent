import pytest
from pydantic import ValidationError

from app.llm.models import LLMRequest, LLMResponse, LLMUsage
from app.llm.exceptions import (
    OpenRouterError,
    OpenRouterRateLimitError,
    OpenRouterTimeoutError,
    OpenRouterValidationError,
    OpenRouterAPIError,
)


class TestLLMRequest:
    def test_minimal_request(self):
        req = LLMRequest(messages=[{"role": "user", "content": "Hello"}])
        # No model means "use the configured OPENROUTER_MODEL"; the client
        # resolves it at request time.
        assert req.model is None
        assert req.temperature == 0.7
        assert req.max_tokens is None
        assert req.response_format is None

    def test_full_request(self):
        req = LLMRequest(
            messages=[{"role": "system", "content": "You are helpful."}],
            model="test-model",
            temperature=0.3,
            max_tokens=100,
            response_format={"type": "json_object"},
        )
        assert req.model == "test-model"
        assert req.temperature == 0.3
        assert req.max_tokens == 100
        assert req.response_format == {"type": "json_object"}

    def test_temperature_bounds(self):
        """Temperature must be between 0.0 and 2.0."""
        LLMRequest(messages=[{"role": "user", "content": "x"}], temperature=0.0)
        LLMRequest(messages=[{"role": "user", "content": "x"}], temperature=2.0)

        with pytest.raises(ValidationError):
            LLMRequest(messages=[{"role": "user", "content": "x"}], temperature=-0.1)

        with pytest.raises(ValidationError):
            LLMRequest(messages=[{"role": "user", "content": "x"}], temperature=2.1)

    def test_max_tokens_must_be_positive(self):
        with pytest.raises(ValidationError):
            LLMRequest(
                messages=[{"role": "user", "content": "x"}], max_tokens=0
            )

    def test_empty_messages_raises(self):
        with pytest.raises(ValidationError):
            LLMRequest(messages=[])


class TestLLMUsage:
    def test_create_usage(self):
        usage = LLMUsage(
            prompt_tokens=100, completion_tokens=50, total_tokens=150
        )
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150


class TestLLMResponse:
    def test_minimal_response(self):
        resp = LLMResponse(content="Hello back", model="test", finish_reason="stop")
        assert resp.content == "Hello back"
        assert resp.model == "test"
        assert resp.finish_reason == "stop"
        assert resp.usage is None

    def test_response_with_usage(self):
        usage = LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        resp = LLMResponse(
            content="Hi", model="m", finish_reason="stop", usage=usage
        )
        assert resp.usage.prompt_tokens == 10
        assert resp.usage.completion_tokens == 5


class TestLLMExceptions:
    def test_base_exception(self):
        err = OpenRouterError("something went wrong")
        assert str(err) == "something went wrong"
        assert isinstance(err, Exception)

    def test_rate_limit_error(self):
        err = OpenRouterRateLimitError()
        assert isinstance(err, OpenRouterError)

    def test_timeout_error(self):
        err = OpenRouterTimeoutError()
        assert isinstance(err, OpenRouterError)

    def test_validation_error(self):
        err = OpenRouterValidationError("bad JSON")
        assert "bad JSON" in str(err)
        assert isinstance(err, OpenRouterError)

    def test_api_error_with_detail(self):
        err = OpenRouterAPIError(
            message="server error",
            status_code=500,
            error_detail="internal failure",
        )
        assert err.message == "server error"
        assert err.status_code == 500
        assert err.error_detail == "internal failure"
        assert "500" in str(err)
        assert isinstance(err, OpenRouterError)

    def test_api_error_without_detail(self):
        err = OpenRouterAPIError(message="gone", status_code=410)
        assert err.error_detail == ""
        assert isinstance(err, OpenRouterError)
