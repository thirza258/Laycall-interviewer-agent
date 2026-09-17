import asyncio
import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.hr_candidate import HrCandidateAgent
from app.core.config import get_settings
from app.db.models.hr_interview import HrInterview
from app.llm.client import OpenRouterClient
from app.llm.exceptions import OpenRouterError, OpenRouterTimeoutError
from app.schemas.hr_interview import HrQuestionCreate, MAX_TURNS

logger = logging.getLogger(__name__)


class HrInterviewService:
    def __init__(self, db: AsyncSession, llm_client: OpenRouterClient):
        self.db = db
        self.agent = HrCandidateAgent(llm_client)

    async def get(self, session_id: str) -> HrInterview:
        interview = (await self.db.execute(
            select(HrInterview).where(HrInterview.id == session_id).execution_options(populate_existing=True)
        )).scalar_one_or_none()
        if interview is None:
            raise HTTPException(404, "HR interview not found")
        return interview

    @staticmethod
    def already_answered(interview: HrInterview, payload: HrQuestionCreate) -> bool:
        for turn in interview.turns:
            if turn["request_id"] == str(payload.request_id):
                if turn["question"] != payload.question:
                    raise HTTPException(409, "This request ID was already used for another question.")
                return True
        return False

    async def _generate(self, operation):
        try:
            return await asyncio.wait_for(operation, timeout=get_settings().QUESTION_GENERATION_TIMEOUT)
        except (TimeoutError, OpenRouterTimeoutError) as error:
            raise HTTPException(504, "The model took too long. Please retry; your conversation is saved.") from error
        except OpenRouterError as error:
            logger.warning("HR interview model failed: %s", type(error).__name__)
            raise HTTPException(503, "Could not get a response from the interview model. Please try again.") from error

    async def ask(self, session_id: str, payload: HrQuestionCreate) -> HrInterview:
        interview = await self.get(session_id)
        if self.already_answered(interview, payload):
            return interview
        if interview.status == "completed":
            raise HTTPException(409, "This interview is completed. Start a new session to keep practicing.")
        if len(interview.turns) >= MAX_TURNS:
            raise HTTPException(409, "This session has reached 30 questions. Finish it to see your feedback.")
        if payload.expected_turn_count != len(interview.turns):
            raise HTTPException(409, "This conversation changed in another tab. Reload the session before asking again.")

        revision, profile, turns = interview.revision, interview.profile, list(interview.turns)
        # Release the read transaction while waiting for the provider. The
        # conditional update below protects writes across workers and tabs.
        await self.db.commit()
        reply = await self._generate(self.agent.reply(profile, turns, payload.question))
        turns.append({
            "request_id": str(payload.request_id), "question": payload.question,
            "answer": reply.answer, "created_at": datetime.now(timezone.utc).isoformat(),
        })
        saved = await self._save(session_id, revision, turns=turns)
        current = await self.get(session_id)
        if not saved and not self.already_answered(current, payload):
            raise HTTPException(409, "This conversation changed in another tab. Reload the session before asking again.")
        return current

    async def finish(self, session_id: str) -> HrInterview:
        interview = await self.get(session_id)
        if interview.status == "completed":
            return interview
        if not interview.turns:
            raise HTTPException(409, "Ask at least one question before finishing the interview.")
        revision, profile, turns = interview.revision, interview.profile, list(interview.turns)
        await self.db.commit()
        feedback = await self._generate(self.agent.review(profile, turns))
        saved = await self._save(session_id, revision, status="completed", feedback=feedback.model_dump())
        current = await self.get(session_id)
        if not saved and current.status != "completed":
            raise HTTPException(409, "This conversation changed. Reload it and finish again to include the latest answer.")
        return current

    async def _save(self, session_id: str, revision: int, **values) -> bool:
        result = await self.db.execute(
            update(HrInterview)
            .where(HrInterview.id == session_id, HrInterview.revision == revision, HrInterview.status == "in_progress")
            .values(**values, revision=revision + 1)
            .execution_options(synchronize_session=False)
        )
        await self.db.commit()
        return result.rowcount == 1
