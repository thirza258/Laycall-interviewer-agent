import asyncio
from functools import lru_cache
import json
import logging
import random
from typing import Any, Optional

import httpx
from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError, APIConnectionError
from pydantic import ValidationError

from app.core.config import get_settings
from app.llm.exceptions import (
    OpenRouterAPIError,
    OpenRouterEmptyResponseError,
    OpenRouterRateLimitError,
    OpenRouterTimeoutError,
    OpenRouterTruncatedError,
    OpenRouterValidationError,
)
from app.llm.models import LLMRequest, LLMResponse, LLMUsage

logger = logging.getLogger(__name__)

# Upstream status codes worth another attempt. Anything else (400 bad request,
# 401 bad key, 402 out of credits, 403, 404 unknown model) is a configuration
# problem that retrying only makes slower.
RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504, 520, 522, 524}

LLM_FAILURE_MESSAGE = "Failed to get response from LLM"
RATE_LIMIT_MESSAGE = "Rate limit exceeded. Please wait before trying again."

FREE_OPENROUTER_MODELS = [
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3.5-lightning:free",
    "cohere/north-mini-code:free",
    "recursive/flint-v1.0:free",
    "xingchen-agi/xing4.0-29b-a4b:free",
    "nvidia/nemotron-3.5-super-vl:free",
    "dots-studio/dots-3-note-preview:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "google/gemma-4-31b-it:free",
]


def get_shuffled_free_models() -> list[str]:
    models = list(FREE_OPENROUTER_MODELS)
    random.shuffle(models)
    return models


def is_credit_exhausted_error(exc_or_status: Any, message: str = "") -> bool:
    code = None
    if isinstance(exc_or_status, int):
        code = exc_or_status
    else:
        for attr in ("status_code", "http_status", "code"):
            val = getattr(exc_or_status, attr, None)
            if isinstance(val, int):
                code = val
                break
        if code is None and hasattr(exc_or_status, "response"):
            resp = getattr(exc_or_status, "response", None)
            code = getattr(resp, "status_code", None)

    msg_str = f"{exc_or_status} {message}".lower()
    if code == 402:
        return True

    if "rate limit" in msg_str and not any(k in msg_str for k in ("credit", "payment", "balance")):
        return False

    credit_keywords = (
        "402",
        "credit",
        "payment required",
        "run out of credits",
        "insufficient balance",
        "insufficient credits",
        "insufficient_quota",
        "exceeded your current quota",
        "out of credit",
    )
    return any(kw in msg_str for kw in credit_keywords)


def _is_parseable_json(content: str) -> bool:
    """Whether the content still yields a JSON object despite a truncated finish."""
    text = content.strip()
    for candidate in (text, text[text.find("{"): text.rfind("}") + 1]):
        if not candidate:
            continue
        try:
            json.loads(candidate)
            return True
        except ValueError:
            continue
    return False


class OpenRouterClient:
    def __init__(self):
        settings = get_settings()

        self.default_model = settings.OPENROUTER_MODEL
        self.max_retries = max(1, settings.OPENROUTER_MAX_RETRIES)

        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
            # Split timeout: a completion may legitimately take a minute, but a
            # connection that cannot be established should fail in seconds.
            timeout=httpx.Timeout(
                settings.OPENROUTER_TIMEOUT,
                connect=settings.OPENROUTER_CONNECT_TIMEOUT,
            ),
            # The SDK handles backoff for timeouts, dropped connections, 429s
            # and 5xx responses.
            max_retries=self.max_retries,
        )

        self.default_headers = {
            "HTTP-Referer": "https://rag.nevatal.id",
            "X-Title": "Interviewer Backend"
        }

    async def close(self):
        """Gracefully close the underlying HTTP client to release the connection pool."""
        if self.client:
            await self.client.close()

    async def generate_completion(self, request: LLMRequest) -> LLMResponse:
        """
        Sends a prompt to OpenRouter via the OpenAI SDK and returns a validated response.

        Transport-level failures (timeouts, dropped connections, 429, 5xx) are
        retried by the SDK. Responses that arrive as HTTP 200 but carry no usable
        completion are invisible to the SDK, so they are retried here.
        """
        model = request.model or self.default_model
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self._create_completion(model, request)
                return self._build_response(response, model)

            except Exception as e:
                if is_credit_exhausted_error(e):
                    logger.warning(
                        f"OpenRouter credits exhausted ({e}), falling back to shuffled free models"
                    )
                    for free_model in get_shuffled_free_models():
                        try:
                            logger.info(f"Retrying with free fallback model: {free_model}")
                            fb_response = await self._create_completion(free_model, request)
                            return self._build_response(fb_response, free_model)
                        except Exception as fb_exc:
                            logger.warning(f"Free model {free_model} failed: {fb_exc}")
                            continue

                if isinstance(e, OpenRouterEmptyResponseError):
                    last_error = e
                    if attempt < self.max_retries:
                        delay = self._backoff_delay(attempt)
                        logger.warning(
                            f"Empty completion from {model} "
                            f"(attempt {attempt}/{self.max_retries}): {e}. "
                            f"Retrying in {delay:.1f}s."
                        )
                        await asyncio.sleep(delay)
                        continue

                    logger.error(f"Empty completion from {model} after {attempt} attempts: {e}")
                    raise OpenRouterAPIError(
                        "The model returned no usable response after several attempts",
                        502,
                        str(e),
                    ) from e

                raise

        # Unreachable: the loop either returns or raises.
        raise OpenRouterAPIError(LLM_FAILURE_MESSAGE, 502, str(last_error))

    async def _create_completion(self, model: str, request: LLMRequest) -> Any:
        """Issue the request and translate SDK exceptions into domain exceptions."""
        try:
            return await self.client.chat.completions.create(
                model=model,
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                response_format=request.response_format,
                extra_headers=self.default_headers  # Pass OpenRouter-specific headers
            )

        except APITimeoutError as e:
            logger.error(f"OpenRouter request to {model} timed out after retries.")
            raise OpenRouterTimeoutError(
                "The LLM request timed out. Please try again."
            ) from e

        except RateLimitError as e:
            logger.warning(f"OpenRouter rate limit exceeded for {model}.")
            raise OpenRouterRateLimitError(RATE_LIMIT_MESSAGE) from e

        except APIConnectionError as e:
            logger.error(f"Network error during OpenRouter request: {e}")
            raise OpenRouterAPIError("Network error occurred", 500, str(e)) from e

        except APIError as e:
            status_code = getattr(e, 'status_code', 500) or 500
            error_detail = str(e)

            if status_code == 429:
                raise OpenRouterRateLimitError(RATE_LIMIT_MESSAGE) from e

            logger.error(f"OpenRouter API error: {status_code} - {error_detail}")
            raise OpenRouterAPIError(LLM_FAILURE_MESSAGE, status_code, error_detail) from e

    def _build_response(self, response: Any, model: str) -> LLMResponse:
        """Validate the payload and turn it into an LLMResponse."""
        # OpenRouter can answer HTTP 200 with an inline error instead of a
        # completion (provider outage, upstream rate limit, moderation).
        inline_error = getattr(response, "error", None)
        if inline_error:
            self._raise_for_inline_error(inline_error, model)

        choices = getattr(response, "choices", None)
        if not choices:
            raise OpenRouterEmptyResponseError(
                f"Response from {model} contained no choices"
            )

        try:
            choice = choices[0]
            usage = getattr(response, "usage", None)
            content = choice.message.content or ""
            finish_reason = choice.finish_reason or "unknown"

            llm_response = LLMResponse(
                content=content,
                model=getattr(response, "model", None) or model,
                finish_reason=finish_reason,
                usage=LLMUsage(
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens
                ) if usage else None
            )

        except (IndexError, AttributeError, ValidationError) as e:
            logger.error(f"Failed to validate OpenRouter response structure: {response}")
            raise OpenRouterValidationError("Invalid response format from LLM provider.") from e

        # A blank completion is a transient provider hiccup, not a valid answer.
        if not llm_response.content.strip():
            raise OpenRouterEmptyResponseError(
                f"Response from {model} contained empty content "
                f"(finish_reason={llm_response.finish_reason})"
            )

        # Truncated output silently breaks JSON parsing downstream; name the
        # cause instead of surfacing it as "invalid JSON". Content that still
        # parses is kept — hitting the cap on trailing text costs nothing.
        if llm_response.finish_reason == "length":
            completion_tokens = (
                llm_response.usage.completion_tokens if llm_response.usage else "unknown"
            )
            if not _is_parseable_json(llm_response.content):
                raise OpenRouterTruncatedError(
                    f"The model hit its token limit before finishing "
                    f"(model={llm_response.model}, completion_tokens={completion_tokens}). "
                    f"Increase max_tokens for this request."
                )
            logger.warning(
                f"{llm_response.model} hit its token limit but returned parseable "
                f"content ({completion_tokens} completion tokens)"
            )

        return llm_response

    def _raise_for_inline_error(self, inline_error: Any, model: str) -> None:
        """Translate an HTTP-200 error payload into the matching exception."""
        if isinstance(inline_error, dict):
            code = inline_error.get("code")
            message = inline_error.get("message", str(inline_error))
        else:
            code = getattr(inline_error, "code", None)
            message = getattr(inline_error, "message", str(inline_error))

        try:
            status_code = int(code)
        except (TypeError, ValueError):
            status_code = 502

        if status_code == 429:
            logger.warning(f"OpenRouter returned an inline rate limit for {model}: {message}")
            raise OpenRouterRateLimitError(RATE_LIMIT_MESSAGE)

        if status_code in RETRYABLE_STATUS_CODES:
            raise OpenRouterEmptyResponseError(
                f"Upstream error {status_code} from {model}: {message}"
            )

        logger.error(f"OpenRouter inline error: {status_code} - {message}")
        raise OpenRouterAPIError(LLM_FAILURE_MESSAGE, status_code, str(message))

    @staticmethod
    def _backoff_delay(attempt: int) -> float:
        """Exponential backoff with jitter, capped at 8 seconds."""
        return min(2 ** (attempt - 1), 8) + random.uniform(0, 0.5)


@lru_cache(maxsize=1)
def get_openrouter_client() -> OpenRouterClient:
    return OpenRouterClient()
