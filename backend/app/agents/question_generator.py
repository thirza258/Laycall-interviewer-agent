import logging
from typing import List
from app.llm.client import OpenRouterClient
from app.llm.models import LLMRequest
from app.schemas.agents import FinalInterviewSpec, GeneratedQuestions
from app.agents.utils import parse_and_validate_llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert technical interviewer. Generate 10 to 20 high-quality interview questions based on the provided specification.
Ensure a balanced mix of types (technical, behavioral, system_design, etc.) and difficulties (easy, medium, hard).
Prioritize questions that address the candidate's gaps and focus areas while validating their strengths.
Return ONLY a valid JSON object containing a 'questions' array. Do not include markdown, explanations, or extra text.

Expected JSON structure:
{
  "questions": [
    {
      "question": "string",
      "type": "string",
      "difficulty": "string"
    }
  ]
}"""

class QuestionGeneratorAgent:
    def __init__(self, llm_client: OpenRouterClient):
        self.llm_client = llm_client

    async def generate(self, spec: FinalInterviewSpec) -> List[dict]:
        request = LLMRequest(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Generate interview questions based on this specification:\n{spec.model_dump_json(indent=2)}"}
            ],
            temperature=0.7, # Higher creativity for question phrasing
            response_format={"type": "json_object"},
            max_tokens=1500
        )

        response = await self.llm_client.generate_completion(request)
        logger.info(f"Question Generator completed | Model: {response.model} | Tokens: {response.usage}")

        # Validate and extract list
        validated = parse_and_validate_llm_json(response.content, GeneratedQuestions)
        return [q.model_dump() for q in validated.questions]