import logging
from app.llm.client import OpenRouterClient
from app.llm.models import LLMRequest
from app.schemas.agents import AnswerEvaluation
from app.agents.utils import parse_and_validate_llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert technical interviewer evaluating candidate responses.
Score the answer on two dimensions (0-10 scale) and provide constructive feedback.

SCORING GUIDELINES:
- Technical Score: Accuracy, depth, correctness of technical concepts
- Communication Score: Clarity, structure, conciseness, articulation

FEEDBACK GUIDELINES:
- Be specific, actionable, and encouraging
- Highlight strengths first, then areas for improvement
- Keep feedback under 200 words

Return ONLY a valid JSON object. Do not include markdown, explanations, or extra text.

Expected JSON structure:
{
  "technical_score": integer (0-10),
  "communication_score": integer (0-10),
  "feedback": "string"
}"""

class AnswerEvaluationAgent:
    def __init__(self, llm_client: OpenRouterClient):
        self.llm_client = llm_client

    async def evaluate(
        self,
        question_text: str,
        answer_text: str,
        context: dict | None = None
    ) -> AnswerEvaluation:
        """
        Evaluates a candidate's answer against the question.
        
        Args:
            question_text: The original interview question
            answer_text: The candidate's submitted answer
            context: Optional dict with jd_analysis, resume_analysis, etc. for richer evaluation
        """
        # Build context-aware prompt
        context_str = ""
        if context:
            context_str = f"\n\nADDITIONAL CONTEXT:\n{context}"

        user_prompt = f"""
QUESTION: {question_text}

CANDIDATE ANSWER: {answer_text}{context_str}

Evaluate this response according to the scoring guidelines.
"""

        request = LLMRequest(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Lower temperature for consistent scoring
            response_format={"type": "json_object"},
            max_tokens=400
        )

        response = await self.llm_client.generate_completion(request)
        logger.info(f"Evaluation Agent completed | Model: {response.model} | Tokens: {response.usage}")

        return parse_and_validate_llm_json(response.content, AnswerEvaluation)