import logging
from app.llm.client import OpenRouterClient
from app.llm.models import LLMRequest
from app.schemas.agents import ResumeAnalysis
from app.agents.utils import parse_and_validate_llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert technical recruiter. Analyze the provided resume and extract key candidate information.
Return ONLY a valid JSON object. Do not include explanations, markdown, or extra text.

Expected JSON structure:
{
  "education": ["string"],
  "skills": ["string"],
  "projects": ["string"],
  "experience": ["string"]
}"""

class ResumeAnalysisAgent:
    def __init__(self, llm_client: OpenRouterClient):
        self.llm_client = llm_client

    async def analyze(self, resume_text: str) -> ResumeAnalysis:
        request = LLMRequest(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": resume_text}
            ],
            temperature=0.2, 
            response_format={"type": "json_object"},
            max_tokens=1200
        )

        response = await self.llm_client.generate_completion(request)
        logger.info(f"Resume Agent completed | Model: {response.model} | Tokens: {response.usage}")

        return parse_and_validate_llm_json(response.content, ResumeAnalysis)