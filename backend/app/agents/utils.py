import re
import json
from typing import TypeVar, Type
from pydantic import BaseModel
from app.llm.exceptions import OpenRouterValidationError

T = TypeVar('T', bound=BaseModel)

def parse_and_validate_llm_json(response_content: str, model: Type[T]) -> T:
    """
    Extracts JSON from LLM response, strips markdown formatting,
    and validates against the provided Pydantic model.
    """
    cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', response_content.strip(), flags=re.MULTILINE)
    
    try:
        data = json.loads(cleaned)
        return model.model_validate(data)
    except (json.JSONDecodeError, ValueError) as e:
        raise OpenRouterValidationError(f"LLM returned invalid JSON: {e}\nContent: {response_content[:200]}")