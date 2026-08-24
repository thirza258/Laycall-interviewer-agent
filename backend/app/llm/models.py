from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class LLMRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(
        ...,
        min_length=1,
        description="List of chat messages (e.g., [{'role': 'user', 'content': '...'}])",
    )
    model: Optional[str] = Field(
        default=None,
        description="OpenRouter model identifier. Defaults to settings.OPENROUTER_MODEL."
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    response_format: Optional[Dict[str, str]] = Field(default=None, description="e.g., {'type': 'json_object'}")

class LLMUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class LLMResponse(BaseModel):
    content: str
    model: str
    finish_reason: str
    usage: Optional[LLMUsage] = None