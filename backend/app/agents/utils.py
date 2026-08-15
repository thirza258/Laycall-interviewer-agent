import re
import json
from typing import TypeVar, Type
from pydantic import BaseModel, ValidationError
from app.llm.exceptions import OpenRouterValidationError

T = TypeVar('T', bound=BaseModel)

# ```json ... ``` or ``` ... ``` around the payload
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def _extract_json_candidates(content: str):
    """Yield progressively looser readings of the model's output."""
    text = content.strip()
    yield text

    fenced = _FENCE_RE.search(text)
    if fenced:
        yield fenced.group(1).strip()

    # Last resort: the outermost {...} block, which survives leading or
    # trailing prose the model added despite instructions not to.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        yield text[start:end + 1]


def parse_and_validate_llm_json(response_content: str, model: Type[T]) -> T:
    """
    Extracts JSON from LLM response, strips markdown formatting,
    and validates against the provided Pydantic model.
    """
    last_error: Exception | None = None

    for candidate in _extract_json_candidates(response_content or ""):
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            continue

        try:
            return model.model_validate(data)
        except ValidationError as e:
            # Valid JSON in the wrong shape: looser readings will not help.
            raise OpenRouterValidationError(
                f"LLM returned JSON that does not match {model.__name__}: {e}"
            ) from e

    raise OpenRouterValidationError(
        f"LLM returned invalid JSON: {last_error}\nContent: {response_content[:200]}"
    )
