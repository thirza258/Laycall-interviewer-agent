import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.evaluation_service import EvaluationService
from app.schemas.agents import AnswerEvaluation


class TestEvaluationService:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        return EvaluationService(mock_db)

    @pytest.mark.asyncio
    async def test_save_evaluation_creates_record(self, service, mock_db):
        """Should create and persist an evaluation record."""
        mock_db.execute.return_value = AsyncMock()
        # Simulate no existing evaluation
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        evaluation = AnswerEvaluation(
            technical_score=8,
            communication_score=7,
            feedback="Great answer with clear examples and good communication.",
        )

        result = await service.save_evaluation("42", evaluation)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_save_duplicate_evaluation_raises(self, service, mock_db):
        """Should raise ValueError if evaluation already exists for the answer."""
        mock_existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing
        mock_db.execute.return_value = mock_result

        evaluation = AnswerEvaluation(
            technical_score=5,
            communication_score=5,
            feedback="Decent answer, could use more detail.",
        )

        with pytest.raises(ValueError, match="already exists"):
            await service.save_evaluation("42", evaluation)

        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_evaluation_with_integer_answer_id(self, service, mock_db):
        """Should accept integer answer_id."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        evaluation = AnswerEvaluation(
            technical_score=9,
            communication_score=8,
            feedback="Great job explaining async patterns.",
        )

        result = await service.save_evaluation(42, evaluation)
        assert result is not None
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_evaluation_with_max_scores(self, service, mock_db):
        """Should accept maximum valid scores (10/10)."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        evaluation = AnswerEvaluation(
            technical_score=10,
            communication_score=10,
            feedback="Perfect answer with flawless technical accuracy and excellent communication.",
        )

        result = await service.save_evaluation(1, evaluation)
        assert result is not None

    @pytest.mark.asyncio
    async def test_save_evaluation_with_zero_scores(self, service, mock_db):
        """Should accept minimum valid scores (0/10)."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        evaluation = AnswerEvaluation(
            technical_score=0,
            communication_score=0,
            feedback="The answer was completely off-topic and unclear.",
        )

        result = await service.save_evaluation(1, evaluation)
        assert result is not None


# InterviewCompletionService, InterviewSpecService, ResumeExtractionService and
# InterviewFinalizationService are exercised against a real database in
# tests/integration/test_services.py. Mocking the session hid the bug that
# mattered most there: an in-place JSONB write that never reached the database.


class TestInterviewOrchestrationService:
    """Question generation must survive a transient LLM failure."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        from app.services.interview_orchestration import InterviewOrchestrationService

        return InterviewOrchestrationService(mock_db, MagicMock())

    @staticmethod
    def _count_result(count: int):
        result = MagicMock()
        result.scalar_one.return_value = count
        return result

    @pytest.mark.asyncio
    async def test_skips_generation_when_questions_exist(self, service, mock_db):
        """A retry must not append a second set of questions."""
        mock_db.execute.return_value = self._count_result(12)
        service._run_pipeline = AsyncMock()

        count = await service.generate_questions(1)

        assert count == 12
        service._run_pipeline.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_runs_pipeline_when_no_questions(self, service, mock_db):
        mock_db.execute.return_value = self._count_result(0)
        service._run_pipeline = AsyncMock(return_value=15)

        count = await service.generate_questions(2)

        assert count == 15
        service._run_pipeline.assert_awaited_once_with(2)

    @pytest.mark.asyncio
    async def test_concurrent_calls_generate_once(self, service, mock_db):
        """Overlapping retries for one interview must not both run the pipeline."""
        import asyncio

        counts = iter([0, 20])

        async def execute(*_args, **_kwargs):
            return self._count_result(next(counts, 20))

        mock_db.execute = AsyncMock(side_effect=execute)

        async def slow_pipeline(_interview_id):
            await asyncio.sleep(0)
            return 20

        service._run_pipeline = AsyncMock(side_effect=slow_pipeline)

        results = await asyncio.gather(
            service.generate_questions(3), service.generate_questions(3)
        )

        assert results == [20, 20]
        service._run_pipeline.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cannot_generate_without_inputs(self, service, mock_db):
        """No job description means there is nothing to regenerate from."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result

        assert await service.can_generate(4) is False

    @pytest.mark.asyncio
    async def test_generation_is_bounded_by_timeout(self, service, mock_db):
        """A stuck pipeline must not outlive the caller's connection."""
        import asyncio

        mock_db.execute.return_value = self._count_result(0)
        service.generation_timeout = 0.05

        async def hanging_pipeline(_interview_id):
            await asyncio.sleep(5)
            return 10

        service._run_pipeline = AsyncMock(side_effect=hanging_pipeline)

        with pytest.raises((asyncio.TimeoutError, TimeoutError)):
            await service.generate_questions(5)

    @pytest.mark.asyncio
    async def test_is_generating_reports_in_flight_run(self, service, mock_db):
        """The endpoint uses this to answer immediately instead of queueing."""
        import asyncio

        mock_db.execute.return_value = self._count_result(0)
        started = asyncio.Event()

        async def slow_pipeline(_interview_id):
            started.set()
            await asyncio.sleep(0.2)
            return 10

        service._run_pipeline = AsyncMock(side_effect=slow_pipeline)

        assert service.is_generating(6) is False
        task = asyncio.create_task(service.generate_questions(6))
        await started.wait()
        assert service.is_generating(6) is True

        await task
        assert service.is_generating(6) is False


class TestResumeExtractionGuards:
    """The guard on a resume row that carries no object path.

    `resumes.file_path` is NOT NULL, so this state cannot be reached through
    a persisted row — which is exactly why the session is stubbed here rather
    than using the SQLite fixture. The guard still earns its test: it is what
    turns a hand-edited row or a future nullable migration into a named error
    instead of `None` being handed to the storage client.
    """

    @staticmethod
    def _session_returning(resume):
        result = MagicMock()
        result.scalar_one_or_none.return_value = resume
        db = AsyncMock()
        db.execute = AsyncMock(return_value=result)
        return db

    @pytest.mark.asyncio
    async def test_resume_without_a_file_path_raises(self):
        from app.db.models.resume import Resume
        from app.services.resume_extraction import ResumeExtractionService

        resume = Resume(id=7, interview_id=1, file_path=None)
        service = ResumeExtractionService(self._session_returning(resume))

        with pytest.raises(ValueError, match="Resume 7 has no associated file path"):
            await service.extract_and_save(7)

    @pytest.mark.asyncio
    async def test_missing_resume_names_the_id(self):
        from app.services.resume_extraction import ResumeExtractionService

        service = ResumeExtractionService(self._session_returning(None))

        with pytest.raises(ValueError, match="Resume with ID 7 not found"):
            await service.extract_and_save(7)
