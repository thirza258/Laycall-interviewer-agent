import logging
from app.llm.client import OpenRouterClient
from app.llm.models import LLMRequest
from app.schemas.agents import JobDescriptionAnalysis, ResumeAnalysis, GapAnalysis, FinalInterviewSpec
from app.agents.utils import parse_and_validate_llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert interview architect. Synthesize the JD analysis, Resume analysis, and Gap analysis into a final interview specification.
This spec will be the single source of truth for generating interview questions. Keep it concise and actionable.
Return ONLY a valid JSON object. Do not include markdown, explanations, or extra text.

Expected JSON structure:
{
  "target_role": "string",
  "difficulty": "string (junior, mid, senior, expert)",
  "required_skills": ["string"],
  "focus_areas": ["string"],
  "candidate_strengths": ["string"],
  "candidate_gaps": ["string"]
}"""

class SpecBuilderAgent:
    def __init__(self, llm_client: OpenRouterClient):
        self.llm_client = llm_client

    async def build(
        self,
        jd_analysis: JobDescriptionAnalysis,
        resume_analysis: ResumeAnalysis,
        gap_analysis: GapAnalysis
    ) -> FinalInterviewSpec:
        input_context = {
            "jd_analysis": jd_analysis.model_dump(),
            "resume_analysis": resume_analysis.model_dump(),
            "gap_analysis": gap_analysis.model_dump()
        }

        request = LLMRequest(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Generate the final interview specification based on:\n{input_context}"}
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
            max_tokens=600
        )

        response = await self.llm_client.generate_completion(request)
        logger.info(f"Spec Builder completed | Model: {response.model} | Tokens: {response.usage}")

        return parse_and_validate_llm_json(response.content, FinalInterviewSpec)