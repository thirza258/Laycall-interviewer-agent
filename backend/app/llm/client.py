from functools import lru_cache
import logging
from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError, APIConnectionError
from pydantic import ValidationError

from app.core.config import get_settings
from app.llm.exceptions import (
    OpenRouterAPIError,
    OpenRouterRateLimitError,
    OpenRouterTimeoutError,
    OpenRouterValidationError,
)
from app.llm.models import LLMRequest, LLMResponse, LLMUsage

logger = logging.getLogger(__name__)

class OpenRouterClient:
    def __init__(self):
        settings = get_settings()
        
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
            timeout=10.0, 
        )
        
        self.default_headers = {
            "HTTP-Referer": "https://rag.nevatal.tech",
            "X-Title": "Interviewer Backend"
        }

    async def close(self):
        """Gracefully close the underlying HTTP client to release the connection pool."""
        if self.client:
            await self.client.close()
    
    async def generate_completion(self, request: LLMRequest) -> LLMResponse:
        """
        Sends a prompt to OpenRouter via the OpenAI SDK and returns a validated response.
        Leverages the SDK's built-in retry, timeout, and error handling.
        """
        try:
            response = await self.client.chat.completions.create(
                model=request.model,
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                response_format=request.response_format,
                extra_headers=self.default_headers  # Pass OpenRouter-specific headers
            )

        except APITimeoutError as e:
            logger.error("OpenRouter request timed out.")
            raise OpenRouterTimeoutError("The LLM request timed out. Please try again.") from e
            
        except RateLimitError as e:
            logger.warning("OpenRouter rate limit exceeded.")
            raise OpenRouterRateLimitError("Rate limit exceeded. Please wait before trying again.") from e
            
        except APIConnectionError as e:
            logger.error(f"Network error during OpenRouter request: {e}")
            raise OpenRouterAPIError("Network error occurred", 500, str(e)) from e
            
        except APIError as e:
            status_code = getattr(e, 'status_code', 500)
            error_detail = str(e)
            
            if status_code == 429:
                raise OpenRouterRateLimitError("Rate limit exceeded. Please wait before trying again.") from e
                
            logger.error(f"OpenRouter API error: {status_code} - {error_detail}")
            raise OpenRouterAPIError("Failed to get response from LLM", status_code, error_detail) from e

        # --- Response Validation ---
        try:
            choice = response.choices[0]
            usage = response.usage
            
            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                finish_reason=choice.finish_reason or "unknown",
                usage=LLMUsage(
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens
                ) if usage else None
            )
            
        except (IndexError, AttributeError, ValidationError) as e:
            logger.error(f"Failed to validate OpenRouter response structure: {response}")
            raise OpenRouterValidationError("Invalid response format from LLM provider.") from e


@lru_cache(maxsize=1)
def get_openrouter_client() -> OpenRouterClient:
    return OpenRouterClient()