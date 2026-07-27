import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.interview import Interview, InterviewStatus
from app.db.models.job_description import JobDescription
from app.db.models.resume import Resume
from app.db.models.question import Question
from app.llm.client import OpenRouterClient
from app.agents.job_description_parser import JobDescriptionParserAgent
from app.agents.resume_analyzer import ResumeAnalysisAgent
from app.agents.gap_analysis_agent import GapAnalysisAgent
from app.agents.spec_builder import SpecBuilderAgent
from app.agents.question_generator import QuestionGeneratorAgent
from app.services.interview_spec_service import InterviewSpecService

logger = logging.getLogger(__name__)


class InterviewOrchestrationService:
    def __init__(self, db: AsyncSession, llm_client: OpenRouterClient):
        self.db = db
        self.llm_client = llm_client
        self.spec_service = InterviewSpecService(db)

    async def generate_questions(self, interview_id: int) -> int:
        """Run the full pipeline and persist generated questions. Returns count."""

        interview = await self._get_interview(interview_id)
        if not interview:
            raise ValueError(f"Interview {interview_id} not found")

        jd_text = await self._get_job_description(interview_id)
        if not jd_text:
            raise ValueError(f"No job description found for interview {interview_id}")

        resume_text = await self._get_resume_text(interview_id)
        if not resume_text:
            raise ValueError(f"No resume found for interview {interview_id}")

        logger.info(f"Starting question generation pipeline for interview {interview_id}")

        # Step 1: Parse job description
        jd_agent = JobDescriptionParserAgent(self.llm_client)
        jd_analysis = await jd_agent.analyze(jd_text)
        await self.spec_service.save_jd_analysis(interview_id, jd_analysis)
        logger.info(f"Step 1/5: JD analysis complete for interview {interview_id}")

        # Step 2: Analyze resume
        resume_agent = ResumeAnalysisAgent(self.llm_client)
        resume_analysis = await resume_agent.analyze(resume_text)
        await self.spec_service.save_resume_analysis(interview_id, resume_analysis)
        logger.info(f"Step 2/5: Resume analysis complete for interview {interview_id}")

        # Step 3: Gap analysis
        gap_agent = GapAnalysisAgent(self.llm_client)
        gap_analysis = await gap_agent.analyze(jd_analysis, resume_analysis)
        await self.spec_service.save_gap_analysis(interview_id, gap_analysis)
        logger.info(f"Step 3/5: Gap analysis complete for interview {interview_id}")

        # Step 4: Build interview spec
        spec_agent = SpecBuilderAgent(self.llm_client)
        final_spec = await spec_agent.build(jd_analysis, resume_analysis, gap_analysis)
        await self.spec_service.save_final_spec(interview_id, final_spec)
        logger.info(f"Step 4/5: Spec building complete for interview {interview_id}")

        # Step 5: Generate questions
        q_agent = QuestionGeneratorAgent(self.llm_client)
        questions = await q_agent.generate(final_spec)
        await self.spec_service.save_questions(interview_id, questions)
        logger.info(f"Step 5/5: Generated {len(questions)} questions for interview {interview_id}")

        # Persist questions to the questions table
        count = await self._save_questions(interview_id, questions)

        # Update interview status to in_progress
        interview.status = InterviewStatus.IN_PROGRESS
        await self.db.commit()

        logger.info(f"Pipeline complete: {count} questions saved for interview {interview_id}")
        return count

    async def _get_interview(self, interview_id: int):
        result = await self.db.execute(select(Interview).where(Interview.id == interview_id))
        return result.scalar_one_or_none()

    async def _get_job_description(self, interview_id: int) -> str | None:
        result = await self.db.execute(
            select(JobDescription).where(JobDescription.interview_id == interview_id)
        )
        jd = result.scalar_one_or_none()
        return jd.raw_text if jd else None

    async def _get_resume_text(self, interview_id: int) -> str | None:
        result = await self.db.execute(
            select(Resume).where(Resume.interview_id == interview_id)
        )
        resume = result.scalar_one_or_none()
        return resume.raw_text if resume else None

    async def _save_questions(self, interview_id: int, questions: list[dict]) -> int:
        for i, q in enumerate(questions):
            question = Question(
                interview_id=interview_id,
                question=q["question"],
                question_type=q.get("type", "general"),
                difficulty=q.get("difficulty", "medium"),
                sequence=i + 1,
            )
            self.db.add(question)

        await self.db.commit()
        return len(questions)
