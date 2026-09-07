import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.db.models.interview import Interview, InterviewStatus
from app.db.models.job_description import JobDescription
from app.db.models.resume import Resume
from app.db.models.question import Question
from app.db.models.answer import Answer
from app.db.models.evaluation import Evaluation
from app.db.models.interview_spec import InterviewSpec
from app.services import interview_orchestration
from app.services.interview_finalization import InterviewFinalizationService
from app.services.interview_orchestration import InterviewOrchestrationService


class TestCreateInterview:
    @pytest.mark.asyncio
    async def test_create_interview_success(self, test_client, db_session):
        """Creating an interview with a valid resume_id should return 201."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        resume = Resume(interview_id=interview.id, file_path="resumes/1/doc.pdf", raw_text="text")
        db_session.add(resume)
        await db_session.commit()

        response = await test_client.post(
            "/api/v1/interviews",
            json={
                "job_description": "We are looking for a senior backend engineer with 5+ years experience.",
                "resume_id": resume.id,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert data["id"] is not None
        assert "job_description" in data
        assert data["job_description"]["raw_text"] == "We are looking for a senior backend engineer with 5+ years experience."

    @pytest.mark.asyncio
    async def test_create_interview_resume_not_found(self, test_client, db_session):
        """Creating an interview with a non-existent resume_id should return 404."""
        response = await test_client.post(
            "/api/v1/interviews",
            json={
                "job_description": "We need a Python developer with at least 3 years experience.",
                "resume_id": 99999,
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_interview_short_job_description(self, test_client, db_session):
        """Job description must be at least 10 characters."""
        response = await test_client.post(
            "/api/v1/interviews",
            json={"job_description": "short", "resume_id": 1},
        )

        assert response.status_code == 422


class TestGetQuestion:
    @pytest.mark.asyncio
    async def test_get_first_question(self, test_client, db_session):
        """Getting the first question (no last_question_id) for an interview."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        q1 = Question(
            interview_id=interview.id, question="First question?",
            question_type="technical", difficulty="easy", sequence=1,
        )
        q2 = Question(
            interview_id=interview.id, question="Second question?",
            question_type="technical", difficulty="medium", sequence=2,
        )
        db_session.add_all([q1, q2])
        await db_session.commit()

        response = await test_client.get(f"/api/v1/interviews/{interview.id}/question")

        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "First question?"
        assert "question_id" in data

    @pytest.mark.asyncio
    async def test_get_next_question_with_last_id(self, test_client, db_session):
        """Getting the next question after a given question_id."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        q1 = Question(interview_id=interview.id, question="Q1", question_type="tech", difficulty="easy", sequence=1)
        q2 = Question(interview_id=interview.id, question="Q2", question_type="tech", difficulty="easy", sequence=2)
        q3 = Question(interview_id=interview.id, question="Q3", question_type="tech", difficulty="easy", sequence=3)
        db_session.add_all([q1, q2, q3])
        await db_session.commit()

        # Get after q1 → should get q2
        response = await test_client.get(
            f"/api/v1/interviews/{interview.id}/question",
            params={"last_question_id": str(q1.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "Q2"

    @pytest.mark.asyncio
    async def test_get_question_no_more_questions(self, test_client, db_session):
        """When asking after the last question, should return 404."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        q1 = Question(interview_id=interview.id, question="Last Q", question_type="tech", difficulty="easy", sequence=1)
        db_session.add(q1)
        await db_session.commit()

        response = await test_client.get(
            f"/api/v1/interviews/{interview.id}/question",
            params={"last_question_id": str(q1.id)},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_question_interview_not_found(self, test_client, db_session):
        response = await test_client.get("/api/v1/interviews/99999/question")
        assert response.status_code == 404


class TestGetResults:
    @pytest.mark.asyncio
    async def test_get_results_interview_not_found(self, test_client, db_session):
        response = await test_client.get("/api/v1/interviews/99999/results")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_results_without_assessment(self, test_client, db_session):
        """Results for an interview without a final assessment should default to empty lists."""
        interview = Interview(status=InterviewStatus.COMPLETED)
        db_session.add(interview)
        await db_session.flush()

        spec = InterviewSpec(interview_id=interview.id, json_data={"final_spec": {}})
        db_session.add(spec)
        await db_session.commit()

        response = await test_client.get(f"/api/v1/interviews/{interview.id}/results")

        assert response.status_code == 200
        data = response.json()
        assert data["interview_id"] == interview.id
        assert data["status"] == "completed"
        assert data["strengths"] == []
        assert data["weaknesses"] == []
        assert data["recommendations"] == []

    @pytest.mark.asyncio
    async def test_get_results_with_assessment(self, test_client, db_session):
        """Results for a completed interview with a final assessment."""
        interview = Interview(status=InterviewStatus.COMPLETED)
        db_session.add(interview)
        await db_session.flush()

        spec = InterviewSpec(
            interview_id=interview.id,
            json_data={
                "final_assessment": {
                    "overall_score": 85,
                    "technical_score": 80,
                    "communication_score": 90,
                    "strengths": ["Python expertise"],
                    "weaknesses": ["Design patterns"],
                    "recommendations": ["Study GoF"],
                },
            },
        )
        db_session.add(spec)
        await db_session.commit()

        response = await test_client.get(f"/api/v1/interviews/{interview.id}/results")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_score"] == 85
        assert data["technical_score"] == 80
        assert data["communication_score"] == 90
        assert data["strengths"] == ["Python expertise"]


class TestCreateInterviewEdgeCases:
    @pytest.mark.asyncio
    async def test_create_interview_without_resume(self, test_client, db_session):
        """Creating an interview without a resume_id should succeed."""
        response = await test_client.post(
            "/api/v1/interviews",
            json={
                "job_description": "We need a Python developer with at least 3 years experience.",
                "resume_id": None,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert data["id"] is not None
        assert data["job_description"]["raw_text"] == "We need a Python developer with at least 3 years experience."

    @pytest.mark.asyncio
    async def test_create_interview_multiple_for_same_resume(self, test_client, db_session):
        """Multiple interviews can reference the same resume."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        resume = Resume(interview_id=interview.id, file_path="resumes/1/doc.pdf", raw_text="text")
        db_session.add(resume)
        await db_session.commit()

        for _ in range(3):
            response = await test_client.post(
                "/api/v1/interviews",
                json={
                    "job_description": "We are looking for a backend engineer with Python experience.",
                    "resume_id": resume.id,
                },
            )
            assert response.status_code == 201


class TestGetQuestionEdgeCases:
    @pytest.mark.asyncio
    async def test_get_question_no_questions_for_interview(self, test_client, db_session):
        """Getting a question for an interview with no questions should return 404."""
        interview = Interview()
        db_session.add(interview)
        await db_session.commit()

        response = await test_client.get(f"/api/v1/interviews/{interview.id}/question")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_question_invalid_last_question_id(self, test_client, db_session):
        """Passing a non-existent last_question_id should return 404."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        question = Question(
            interview_id=interview.id, question="Q1",
            question_type="tech", difficulty="easy", sequence=1,
        )
        db_session.add(question)
        await db_session.commit()

        response = await test_client.get(
            f"/api/v1/interviews/{interview.id}/question",
            params={"last_question_id": 99999},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_question_invalid_interview_id_format(self, test_client, db_session):
        """Passing a non-integer interview_id should return 422."""
        response = await test_client.get("/api/v1/interviews/not-an-integer/question")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_question_invalid_last_question_id_format(self, test_client, db_session):
        """Passing a non-integer last_question_id should return 422."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        question = Question(
            interview_id=interview.id, question="Q1",
            question_type="tech", difficulty="easy", sequence=1,
        )
        db_session.add(question)
        await db_session.commit()

        response = await test_client.get(
            f"/api/v1/interviews/{interview.id}/question",
            params={"last_question_id": "not-an-integer"},
        )

        assert response.status_code == 422


class TestGetResultsEdgeCases:
    @pytest.mark.asyncio
    async def test_get_results_pending_interview(self, test_client, db_session):
        """Getting results for a pending (not completed) interview should succeed with defaults."""
        interview = Interview(status=InterviewStatus.PENDING)
        db_session.add(interview)
        await db_session.commit()

        response = await test_client.get(f"/api/v1/interviews/{interview.id}/results")

        assert response.status_code == 200
        data = response.json()
        assert data["interview_id"] == interview.id
        assert data["status"] == "pending"
        assert data["completed_at"] is None
        assert data["strengths"] == []
        assert data["weaknesses"] == []
        assert data["recommendations"] == []

    @pytest.mark.asyncio
    async def test_get_results_in_progress_interview(self, test_client, db_session):
        """Getting results for an in-progress interview should succeed with defaults."""
        interview = Interview(status=InterviewStatus.IN_PROGRESS)
        db_session.add(interview)
        await db_session.commit()

        response = await test_client.get(f"/api/v1/interviews/{interview.id}/results")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_get_results_no_spec(self, test_client, db_session):
        """Getting results when no interview spec exists should succeed with defaults."""
        interview = Interview(status=InterviewStatus.COMPLETED)
        db_session.add(interview)
        await db_session.commit()

        response = await test_client.get(f"/api/v1/interviews/{interview.id}/results")

        assert response.status_code == 200
        data = response.json()
        assert data["strengths"] == []
        assert data["weaknesses"] == []
        assert data["recommendations"] == []

    @pytest.mark.asyncio
    async def test_get_results_with_partial_assessment(self, test_client, db_session):
        """Results with only some assessment fields should fill defaults for missing keys."""
        interview = Interview(status=InterviewStatus.COMPLETED)
        db_session.add(interview)
        await db_session.flush()

        spec = InterviewSpec(
            interview_id=interview.id,
            json_data={
                "final_assessment": {
                    "overall_score": 70,
                    "technical_score": 65,
                    # Missing: communication_score, strengths, weaknesses, recommendations
                },
            },
        )
        db_session.add(spec)
        await db_session.commit()

        response = await test_client.get(f"/api/v1/interviews/{interview.id}/results")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_score"] == 70
        assert data["technical_score"] == 65
        assert data["strengths"] == []
        assert data["weaknesses"] == []
        assert data["recommendations"] == []

    @pytest.mark.asyncio
    async def test_get_results_invalid_interview_id_format(self, test_client, db_session):
        """Passing a non-integer interview_id should return 422."""
        response = await test_client.get("/api/v1/interviews/not-an-integer/results")

        assert response.status_code == 422


class TestNextQuestionGenerationRetry:
    """The retry the endpoint runs when an interview has no questions yet.

    Reaching it needs three things at once: zero Question rows, a job
    description, and a resume carrying extracted text. Anything less and the
    endpoint returns the plain "no questions" answer instead.
    """

    @pytest_asyncio.fixture
    async def generatable(self, db_session):
        """An interview the pipeline could generate from, with no questions."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        db_session.add_all([
            JobDescription(
                interview_id=interview.id,
                raw_text="Senior backend engineer, Python and FastAPI.",
            ),
            Resume(
                interview_id=interview.id,
                file_path="resumes/1/cv.pdf",
                raw_text="Five years of async Python.",
            ),
        ])
        await db_session.commit()
        return interview

    @pytest.mark.asyncio
    async def test_retry_generates_the_missing_questions(
        self, test_client, db_session, generatable
    ):
        """A successful retry serves the question it just generated."""
        async def generate(interview_id):
            db_session.add(Question(
                interview_id=interview_id, question="Explain async/await.",
                question_type="technical", difficulty="medium", sequence=1,
            ))
            await db_session.commit()
            return 1

        with patch.object(
            InterviewOrchestrationService, "generate_questions",
            AsyncMock(side_effect=generate),
        ):
            response = await test_client.get(
                f"/api/v1/interviews/{generatable.id}/question"
            )

        assert response.status_code == 200
        assert response.json()["question"] == "Explain async/await."

    @pytest.mark.asyncio
    async def test_generation_already_in_flight_returns_409(
        self, test_client, generatable
    ):
        """A caller must not queue behind a running pipeline.

        The lock is the real one the service uses, held for the duration of
        the request rather than stubbed, so this exercises `is_generating`
        against the state a concurrent upload would actually leave behind.
        """
        lock = interview_orchestration._generation_lock(generatable.id)

        async with lock:
            response = await test_client.get(
                f"/api/v1/interviews/{generatable.id}/question"
            )

        assert response.status_code == 409
        assert "still being prepared" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_missing_inputs_reported_as_400(
        self, test_client, generatable
    ):
        """A ValueError from the pipeline is the caller's problem, not a 500."""
        with patch.object(
            InterviewOrchestrationService, "generate_questions",
            AsyncMock(side_effect=ValueError("No job description found")),
        ):
            response = await test_client.get(
                f"/api/v1/interviews/{generatable.id}/question"
            )

        assert response.status_code == 400
        assert response.json()["detail"] == "No job description found"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("error", [asyncio.TimeoutError(), TimeoutError()])
    async def test_generation_timeout_returns_504(
        self, test_client, generatable, error
    ):
        """Both timeout types the pipeline can raise map to 504."""
        with patch.object(
            InterviewOrchestrationService, "generate_questions",
            AsyncMock(side_effect=error),
        ):
            response = await test_client.get(
                f"/api/v1/interviews/{generatable.id}/question"
            )

        assert response.status_code == 504
        assert "longer than expected" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_unreachable_model_returns_503(
        self, test_client, generatable
    ):
        """Any other pipeline failure is reported as the model being down."""
        with patch.object(
            InterviewOrchestrationService, "generate_questions",
            AsyncMock(side_effect=RuntimeError("connection reset")),
        ):
            response = await test_client.get(
                f"/api/v1/interviews/{generatable.id}/question"
            )

        assert response.status_code == 503
        assert "Could not reach the interview model" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_no_retry_without_a_resume(self, test_client, db_session):
        """Nothing to generate from: the plain "no questions" answer stands."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()
        db_session.add(JobDescription(
            interview_id=interview.id, raw_text="Backend engineer."
        ))
        await db_session.commit()

        with patch.object(
            InterviewOrchestrationService, "generate_questions", AsyncMock()
        ) as generate:
            response = await test_client.get(
                f"/api/v1/interviews/{interview.id}/question"
            )

        generate.assert_not_awaited()
        assert response.status_code == 404


class TestResultsFinalizationFailure:
    @pytest.mark.asyncio
    async def test_failed_finalization_still_returns_the_interview(
        self, test_client, db_session
    ):
        """A broken final-assessment call must not take the whole report down.

        The endpoint builds the assessment on read when it is missing. If that
        raises, the caller should still get the interview with a null score
        rather than a 500.
        """
        interview = Interview()
        db_session.add(interview)
        await db_session.commit()

        with patch.object(
            InterviewFinalizationService, "finalize_if_complete",
            AsyncMock(side_effect=RuntimeError("model unavailable")),
        ):
            response = await test_client.get(
                f"/api/v1/interviews/{interview.id}/results"
            )

        assert response.status_code == 200
        assert response.json()["overall_score"] is None
