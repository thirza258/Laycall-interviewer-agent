import logging
from app.llm.client import OpenRouterClient
from app.llm.models import LLMRequest
from app.schemas.agents import JobDescriptionAnalysis
from app.agents.utils import parse_and_validate_llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert HR analyst. Extract structured information from the provided job description.
Return ONLY a valid JSON object. Do not include explanations, markdown, or extra text.

Expected JSON structure:
{
  "job_title": "string",
  "company": "string",
  "required_skills": ["string"],
  "preferred_skills": ["string"],
  "responsibilities": ["string"]
}"""

class JobDescriptionParserAgent:
    def __init__(self, llm_client: OpenRouterClient):
        self.llm_client = llm_client

    async def analyze(self, job_description_text: str) -> JobDescriptionAnalysis:
        request = LLMRequest(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": job_description_text}
            ],
            temperature=0.1,  # Deterministic extraction
            response_format={"type": "json_object"},
            max_tokens=800
        )

        response = await self.llm_client.generate_completion(request)
        logger.info(f"JD Agent completed | Model: {response.model} | Tokens: {response.usage}")

        return parse_and_validate_llm_json(response.content, JobDescriptionAnalysis)