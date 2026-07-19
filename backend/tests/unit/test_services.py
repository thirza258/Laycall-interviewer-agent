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


class TestInterviewCompletionService:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        from app.services.interview_completion_service import InterviewCompletionService
        return InterviewCompletionService(mock_db)

    @pytest.mark.asyncio
    async def test_check_all_questions_answered(self, service, mock_db):
        """When all questions are answered, is_complete should be True."""
        # Mock count queries: total questions = 5, answered = 5
        call_count = 0
        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            mock_result = MagicMock()
            if call_count == 0:
                mock_result.scalar.return_value = 5  # total questions
            else:
                mock_result.scalar.return_value = 5  # answered count
            call_count += 1
            return mock_result

        mock_db.execute = mock_execute

        # Mock getting the interview
        mock_interview = MagicMock()
        mock_interview.status = "in_progress"
        mock_db.get = AsyncMock(return_value=mock_interview)

        is_complete, summary = await service.check_and_update(1)

        assert is_complete is True
        assert summary["total_questions"] == 5
        assert summary["answered_count"] == 5
        assert summary["completion_percentage"] == 100.0

    @pytest.mark.asyncio
    async def test_check_not_all_answered(self, service, mock_db):
        """When not all questions are answered, is_complete should be False."""
        call_count = 0
        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            mock_result = MagicMock()
            if call_count == 0:
                mock_result.scalar.return_value = 5  # total
            else:
                mock_result.scalar.return_value = 2  # answered
            call_count += 1
            return mock_result

        mock_db.execute = mock_execute

        is_complete, summary = await service.check_and_update(1)
        assert is_complete is False
        assert summary["completion_percentage"] == 40.0

    @pytest.mark.asyncio
    async def test_zero_questions(self, service, mock_db):
        """When there are no questions, should not be complete."""
        call_count = 0
        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            mock_result = MagicMock()
            mock_result.scalar.return_value = 0
            call_count += 1
            return mock_result

        mock_db.execute = mock_execute

        is_complete, summary = await service.check_and_update(1)
        assert is_complete is False


class TestInterviewSpecService:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        from app.services.interview_spec_service import InterviewSpecService
        return InterviewSpecService(mock_db)

    @pytest.mark.asyncio
    async def test_upsert_creates_new_spec(self, service, mock_db):
        """When no spec exists for the interview, a new one should be created."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service._upsert_spec(1, "test_key", {"data": "value"})

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        assert result["test_key"] == {"data": "value"}
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_upsert_updates_existing_spec(self, service, mock_db):
        """When a spec already exists, it should be updated."""
        existing_spec = MagicMock()
        existing_spec.json_data = {"existing_key": "old_value"}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_spec
        mock_db.execute.return_value = mock_result

        result = await service._upsert_spec(1, "new_key", "new_value")

        assert existing_spec.json_data["new_key"] == "new_value"
        assert existing_spec.json_data["existing_key"] == "old_value"
        mock_db.add.assert_not_called()  # Should not create new
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_jd_analysis(self, service, mock_db):
        """save_jd_analysis should delegate to _upsert_spec."""
        from app.schemas.agents import JobDescriptionAnalysis

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        analysis = JobDescriptionAnalysis(
            job_title="Dev", company="Co",
            required_skills=["Python"], preferred_skills=[],
            responsibilities=[],
        )
        result = await service.save_jd_analysis(1, analysis)
        assert "jd_analysis" in result
