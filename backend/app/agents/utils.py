import re
import json
from typing import Any, TypeVar, Type
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


def _known_keys(model: Type[T]) -> set[str]:
    """Field names and aliases the model accepts as input."""
    keys: set[str] = set()
    for name, field in model.model_fields.items():
        keys.add(name)
        if field.alias:
            keys.add(field.alias)
    return keys


def _list_field(model: Type[T]) -> str | None:
    """The single list-valued field of a wrapper model, if there is exactly one."""
    list_fields = [
        name for name, field in model.model_fields.items()
        if getattr(field.annotation, "__origin__", None) is list
        or field.annotation is list
    ]
    return list_fields[0] if len(list_fields) == 1 else None


def _coerce_payload(data: Any, model: Type[T]) -> Any:
    """Straighten out the two shapes models reach for instead of the schema."""
    known = _known_keys(model)

    # A bare array where a wrapper object was asked for: {"questions": [...]}
    # arrives as [...] often enough that failing the whole pipeline over it
    # is not worth it.
    if isinstance(data, list):
        field = _list_field(model)
        return {field: data} if field else data

    # One extra layer of nesting, e.g. {"gap_analysis": {...}}. Only unwrapped
    # when the outer key is not itself part of the schema.
    if isinstance(data, dict) and len(data) == 1 and not (known & data.keys()):
        (inner,) = data.values()
        if isinstance(inner, (dict, list)):
            return _coerce_payload(inner, model)

    return data


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

        payload = _coerce_payload(data, model)

        # Well-formed JSON that shares no field with the target schema is a
        # different answer entirely (an error object, a refusal, prose in a
        # dict). Every field of most agent schemas has a default, so validating
        # it would "succeed" and hand the pipeline an empty analysis.
        if not isinstance(payload, dict) or not (_known_keys(model) & payload.keys()):
            raise OpenRouterValidationError(
                f"LLM returned JSON with none of the fields {model.__name__} "
                f"expects: {str(payload)[:200]}"
            )

        try:
            return model.model_validate(payload)
        except ValidationError as e:
            # Valid JSON in the wrong shape: looser readings will not help.
            raise OpenRouterValidationError(
                f"LLM returned JSON that does not match {model.__name__}: {e}"
            ) from e

    raise OpenRouterValidationError(
        f"LLM returned invalid JSON: {last_error}\nContent: {response_content[:200]}"
    )
