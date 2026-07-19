import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.models.interview import Interview, InterviewStatus
from app.db.models.question import Question
from app.db.models.answer import Answer

logger = logging.getLogger(__name__)

class InterviewCompletionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_and_update(self, interview_id: int) -> tuple[bool, dict]:
        """
        Checks if all questions for an interview have been answered.
        If yes, updates status to 'completed' and returns summary.
        
        Returns:
            (is_complete: bool, summary: dict)
        """
        # Count total questions
        total_stmt = select(func.count(Question.id)).where(
            Question.interview_id == interview_id
        )
        total_questions = (await self.db.execute(total_stmt)).scalar_one()

        # Count answered questions (via JOIN with answers)
        answered_stmt = select(func.count(Answer.id)).join(
            Question, Answer.question_id == Question.id
        ).where(Question.interview_id == interview_id)
        answered_count = (await self.db.execute(answered_stmt)).scalar_one()

        is_complete = total_questions > 0 and answered_count >= total_questions

        summary = {
            "interview_id": interview_id,
            "total_questions": total_questions,
            "answered_count": answered_count,
            "completion_percentage": round((answered_count / total_questions * 100) if total_questions > 0 else 0, 1),
            "is_complete": is_complete
        }

        if is_complete:
            # Fetch and update interview status
            interview = (await self.db.execute(
                select(Interview).where(Interview.id == interview_id)
            )).scalar_one_or_none()
            
            if interview and interview.status != InterviewStatus.COMPLETED:
                interview.mark_completed()
                await self.db.commit()
                logger.info(f"Interview {interview_id} marked as COMPLETED")
                summary["status_updated"] = True
            else:
                summary["status_updated"] = False

        return is_complete, summary