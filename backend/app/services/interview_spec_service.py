import logging
from datetime import datetime, timezone
from typing import Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.interview_spec import InterviewSpec
from app.schemas.agents import FinalInterviewSpec, GapAnalysis, JobDescriptionAnalysis, ResumeAnalysis, FinalAssessment

logger = logging.getLogger(__name__)

class InterviewSpecService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_jd_analysis(self, interview_id: int, analysis: JobDescriptionAnalysis) -> dict:
        return await self._upsert_spec(interview_id, "jd_analysis", analysis.model_dump())

    async def save_resume_analysis(self, interview_id: int, analysis: ResumeAnalysis) -> dict:
        return await self._upsert_spec(interview_id, "resume_analysis", analysis.model_dump())
    
    async def save_gap_analysis(self, interview_id: int, analysis: GapAnalysis) -> dict:
        """Saves gap analysis to interview_specs.json_data.gap_analysis"""
        return await self._upsert_spec(interview_id, "gap_analysis", analysis.model_dump())
    
    async def save_final_spec(self, interview_id: int, spec: FinalInterviewSpec) -> dict:
        """Saves final spec to interview_specs.json_data.final_spec"""
        return await self._upsert_spec(interview_id, "final_spec", spec.model_dump())

    async def save_questions(self, interview_id: int, questions: List[dict]) -> dict:
        """Saves generated questions to interview_specs.json_data.questions"""
        return await self._upsert_spec(interview_id, "questions", questions)
    
    async def save_final_assessment(self, interview_id: int, assessment: FinalAssessment) -> dict:
        """Saves final assessment to interview_specs.json_data.final_assessment"""
        payload = assessment.model_dump()
        payload["completed_at"] = datetime.now(timezone.utc).isoformat()
        return await self._upsert_spec(interview_id, "final_assessment", payload)

    async def _upsert_spec(self, interview_id: int, key: str, value: Any) -> dict:
        result = await self.db.execute(
            select(InterviewSpec).where(InterviewSpec.interview_id == interview_id)
        )
        spec = result.scalar_one_or_none()

        if not spec:
            spec = InterviewSpec(interview_id=interview_id, json_data={})
            self.db.add(spec)
            await self.db.flush()

        if spec.json_data is None:
            spec.json_data = {}

        spec.json_data[key] = value
        await self.db.commit()
        await self.db.refresh(spec)

        logger.info(f"Saved '{key}' to interview_specs for interview {interview_id}")
        return spec.json_data
