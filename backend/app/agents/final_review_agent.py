import logging
from typing import List
from app.llm.client import OpenRouterClient
from app.llm.models import LLMRequest
from app.schemas.agents import FinalAssessment
from app.agents.utils import parse_and_validate_llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior hiring manager synthesizing a complete interview assessment.
Analyze the candidate's performance across all questions, answers, and evaluations.

SCORING:
- overall_score: Weighted average (60% technical, 40% communication), scaled 0-100
- technical_score: Aggregate of technical evaluations, scaled 0-100
- communication_score: Aggregate of communication evaluations, scaled 0-100

FEEDBACK GUIDELINES:
- strengths: 3-5 specific, evidence-based positive observations
- weaknesses: 2-4 constructive, non-judgmental improvement areas
- recommendations: 3-5 actionable next steps (e.g., "Proceed to next round", "Focus on system design practice")

Return ONLY a valid JSON object. Do not include markdown, explanations, or extra text.

Expected JSON structure:
{
  "overall_score": integer (0-100),
  "technical_score": integer (0-100),
  "communication_score": integer (0-100),
  "strengths": ["string"],
  "weaknesses": ["string"],
  "recommendations": ["string"]
}"""

class FinalReviewAgent:
    def __init__(self, llm_client: OpenRouterClient):
        self.llm_client = llm_client

    async def generate_assessment(
        self,
        questions: List[dict],
        answers: List[dict],
        evaluations: List[dict],
        job_context: dict | None = None
    ) -> FinalAssessment:
        """
        Generates a holistic interview assessment from structured Q&A data.
        
        Args:
            questions: List of {"question": str, "type": str, "difficulty": str}
            answers: List of {"answer": str, "created_at": str}
            evaluations: List of {"technical_score": int, "communication_score": int, "feedback": str}
            job_context: Optional dict with jd_analysis, final_spec, etc.
        """
        # Format data for LLM context (truncate long answers for token efficiency)
        qa_pairs = []
        for i, (q, a, e) in enumerate(zip(questions, answers, evaluations), 1):
            qa_pairs.append({
                "q_num": i,
                "question": q["question"][:200],  # Truncate for context window
                "answer": a["answer"][:300],
                "evaluation": e
            })

        context_str = ""
        if job_context:
            context_str = f"\n\nJOB CONTEXT:\nTarget Role: {job_context.get('target_role', 'N/A')}\nRequired Skills: {job_context.get('required_skills', [])}"

        user_prompt = f"""
INTERVIEW DATA:
{qa_pairs}
{context_str}

Generate the final assessment based on this complete interview record.
"""

        request = LLMRequest(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,  # Low temperature for consistent, reliable scoring
            response_format={"type": "json_object"},
            max_tokens=800
        )

        response = await self.llm_client.generate_completion(request)
        logger.info(f"Final Review Agent completed | Model: {response.model} | Tokens: {response.usage}")

        return parse_and_validate_llm_json(response.content, FinalAssessment)