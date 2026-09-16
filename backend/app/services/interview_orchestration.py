import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.core.config import get_settings
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

# The pipeline is retried from the upload endpoint and from the first
# "next question" request, so two calls can overlap for one interview. These
# locks keep a retry from producing a duplicate question set.
_generation_locks: dict[int, asyncio.Lock] = {}


def _generation_lock(interview_id: int) -> asyncio.Lock:
    lock = _generation_locks.get(interview_id)
    if lock is None:
        lock = asyncio.Lock()
        _generation_locks[interview_id] = lock
    return lock


class InterviewOrchestrationService:
    def __init__(self, db: AsyncSession, llm_client: OpenRouterClient):
        self.db = db
        self.llm_client = llm_client
        self.spec_service = InterviewSpecService(db)
        self.generation_timeout = get_settings().QUESTION_GENERATION_TIMEOUT

    async def generate_questions(self, interview_id: int) -> int:
        """
        Run the full pipeline and persist generated questions. Returns count.

        Idempotent: if questions already exist for the interview (because a
        concurrent request generated them first), the existing count is
        returned instead of generating a second set.

        Raises TimeoutError if the pipeline exceeds QUESTION_GENERATION_TIMEOUT,
        so a stuck run cannot outlive the caller's connection.
        """
        async with _generation_lock(interview_id):
            existing = await self.count_questions(interview_id)
            if existing:
                logger.info(
                    f"Interview {interview_id} already has {existing} questions; "
                    f"skipping generation"
                )
                return existing

            return await asyncio.wait_for(
                self._run_pipeline(interview_id),
                timeout=self.generation_timeout,
            )

    def is_generating(self, interview_id: int) -> bool:
        """True while another request is running the pipeline for this interview."""
        lock = _generation_locks.get(interview_id)
        return bool(lock and lock.locked())

    async def count_questions(self, interview_id: int) -> int:
        result = await self.db.execute(
            select(func.count(Question.id)).where(Question.interview_id == interview_id)
        )
        return result.scalar_one()

    async def can_generate(self, interview_id: int) -> bool:
        """True when the interview has the inputs the pipeline needs."""
        if not await self._get_job_description(interview_id):
            return False
        return bool(await self._get_resume_text(interview_id))

    async def _run_pipeline(self, interview_id: int) -> int:
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
            select(Resume)
            .where(Resume.interview_id == interview_id)
            .order_by(Resume.id.desc())
            .limit(1)
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
