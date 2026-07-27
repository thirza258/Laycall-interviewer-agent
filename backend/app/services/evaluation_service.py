import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.evaluation import Evaluation
from app.schemas.agents import AnswerEvaluation

logger = logging.getLogger(__name__)

class EvaluationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_evaluation(
        self,
        answer_id: int,
        evaluation: AnswerEvaluation
    ) -> Evaluation:
        """Persist evaluation to database. Returns the saved Evaluation model."""
        
        # Check if evaluation already exists (idempotency)
        existing = await self.db.execute(
            select(Evaluation).where(Evaluation.answer_id == answer_id)
        )
        if existing.scalar_one_or_none():
            logger.warning(f"Evaluation already exists for answer {answer_id}")
            raise ValueError("Evaluation already exists for this answer")

        new_eval = Evaluation(
            answer_id=answer_id,
            technical_score=evaluation.technical_score,
            communication_score=evaluation.communication_score,
            feedback=evaluation.feedback
        )
        
        self.db.add(new_eval)
        await self.db.commit()
        await self.db.refresh(new_eval)
        
        logger.info(f"Evaluation saved: answer={answer_id}, tech_score={evaluation.technical_score}")
        return new_eval