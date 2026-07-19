import logging
from app.llm.client import OpenRouterClient
from app.llm.models import LLMRequest
from app.schemas.agents import JobDescriptionAnalysis, ResumeAnalysis, GapAnalysis
from app.agents.utils import parse_and_validate_llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert technical hiring manager. Compare the candidate's resume analysis against the job description analysis.
Identify exact matches, missing requirements, candidate strengths, and interview focus areas.
Base your analysis STRICTLY on the provided data. Do not invent skills or requirements.
Return ONLY a valid JSON object. Do not include markdown, explanations, or extra text.

Expected JSON structure:
{
  "matched_skills": ["string"],
  "missing_skills": ["string"],
  "strengths": ["string"],
  "focus_areas": ["string"]
}"""

class GapAnalysisAgent:
    def __init__(self, llm_client: OpenRouterClient):
        self.llm_client = llm_client

    async def analyze(
        self, 
        jd_analysis: JobDescriptionAnalysis, 
        resume_analysis: ResumeAnalysis
    ) -> GapAnalysis:
        """
        Compares structured JD and Resume analyses to generate a skill gap report.
        """
        # Format inputs as clean JSON for the LLM context window
        jd_json = jd_analysis.model_dump_json(indent=2)
        resume_json = resume_analysis.model_dump_json(indent=2)

        request = LLMRequest(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"""
JOB DESCRIPTION ANALYSIS:
{jd_json}

CANDIDATE RESUME ANALYSIS:
{resume_json}

Generate the gap analysis based on the above data.
"""}
            ],
            temperature=0.2,  # Balanced for analytical reasoning + structure
            response_format={"type": "json_object"},
            max_tokens=600
        )

        response = await self.llm_client.generate_completion(request)
        logger.info(f"Gap Agent completed | Model: {response.model} | Tokens: {response.usage}")

        return parse_and_validate_llm_json(response.content, GapAnalysis)