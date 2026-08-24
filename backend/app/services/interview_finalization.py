import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.final_review_agent import FinalReviewAgent
from app.db.models.answer import Answer
from app.db.models.evaluation import Evaluation
from app.db.models.interview_spec import InterviewSpec
from app.db.models.question import Question
from app.llm.client import OpenRouterClient
from app.services.interview_completion_service import InterviewCompletionService
from app.services.interview_spec_service import InterviewSpecService

logger = logging.getLogger(__name__)


class InterviewFinalizationService:
    """Turns a fully answered interview into its final assessment.

    The final review agent previously had no caller, so `/results` answered
    with empty scores no matter how many questions were answered.
    """

    def __init__(self, db: AsyncSession, llm_client: OpenRouterClient):
        self.db = db
        self.llm_client = llm_client
        self.completion_service = InterviewCompletionService(db)
        self.spec_service = InterviewSpecService(db)

    async def finalize_if_complete(self, interview_id: int) -> dict | None:
        """Generate and store the final assessment once every question is answered.

        Returns the assessment (existing or newly generated), or None while the
        interview is still in progress. Idempotent: a stored assessment is
        returned as-is instead of being regenerated.
        """
        existing = await self._stored_assessment(interview_id)
        if existing:
            return existing

        is_complete, summary = await self.completion_service.check_and_update(interview_id)
        if not is_complete:
            logger.debug(
                f"Interview {interview_id} not finalized: "
                f"{summary['answered_count']}/{summary['total_questions']} answered"
            )
            return None

        return await self._generate_assessment(interview_id)

    async def _generate_assessment(self, interview_id: int) -> dict | None:
        questions, answers, evaluations = await self._evaluated_answers(interview_id)
        if not questions:
            logger.warning(
                f"Interview {interview_id} is complete but has no evaluated answers; "
                f"skipping final assessment"
            )
            return None

        agent = FinalReviewAgent(self.llm_client)
        assessment = await agent.generate_assessment(
            questions=questions,
            answers=answers,
            evaluations=evaluations,
            job_context=await self._job_context(interview_id),
        )
        await self.spec_service.save_final_assessment(interview_id, assessment)
        logger.info(
            f"Final assessment stored for interview {interview_id} "
            f"(overall={assessment.overall_score})"
        )
        return assessment.model_dump()

    async def _evaluated_answers(
        self, interview_id: int
    ) -> tuple[list[dict], list[dict], list[dict]]:
        """Question/answer/evaluation triples, aligned by construction.

        The final review agent zips the three lists together, so they have to
        line up. One inner join ordered by sequence guarantees that: an answer
        without an evaluation drops out of all three lists at once instead of
        shifting the others.
        """
        stmt = (
            select(Question, Answer, Evaluation)
            .join(Answer, Answer.question_id == Question.id)
            .join(Evaluation, Evaluation.answer_id == Answer.id)
            .where(Question.interview_id == interview_id)
            .order_by(Question.sequence, Answer.id)
        )
        rows = (await self.db.execute(stmt)).all()

        questions = [
            {"question": q.question, "type": q.question_type, "difficulty": q.difficulty}
            for q, _, _ in rows
        ]
        answers = [{"answer": a.answer} for _, a, _ in rows]
        evaluations = [
            {
                "technical_score": e.technical_score,
                "communication_score": e.communication_score,
                "feedback": e.feedback,
            }
            for _, _, e in rows
        ]
        return questions, answers, evaluations

    async def _job_context(self, interview_id: int) -> dict | None:
        """The stored interview spec, which carries the target role and skills."""
        spec = await self._spec(interview_id)
        if not spec or not spec.json_data:
            return None
        return spec.json_data.get("final_spec")

    async def _stored_assessment(self, interview_id: int) -> dict | None:
        spec = await self._spec(interview_id)
        if not spec or not spec.json_data:
            return None
        return spec.json_data.get("final_assessment")

    async def _spec(self, interview_id: int) -> InterviewSpec | None:
        result = await self.db.execute(
            select(InterviewSpec).where(InterviewSpec.interview_id == interview_id)
        )
        return result.scalar_one_or_none()
