import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock

from app.llm.exceptions import (
    OpenRouterAPIError,
    OpenRouterRateLimitError,
    OpenRouterTimeoutError,
    OpenRouterTruncatedError,
    OpenRouterValidationError,
)
from app.db.models.interview import Interview
from app.db.models.resume import Resume
from app.db.models.job_description import JobDescription
from app.db.models.question import Question
from app.db.models.answer import Answer
from app.db.models.evaluation import Evaluation


class TestSubmitAnswer:
    @pytest.mark.asyncio
    async def test_submit_answer_success(self, test_client, db_session):
        """Submitting a valid answer should return 201."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        question = Question(
            interview_id=interview.id, question="What is async?",
            question_type="technical", difficulty="medium", sequence=1,
        )
        db_session.add(question)
        await db_session.commit()

        response = await test_client.post(
            f"/api/v1/interviews/{interview.id}/answers",
            json={
                "question_id": str(question.id),
                "answer": "Async allows non-blocking I/O operations.",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["answer"] == "Async allows non-blocking I/O operations."
        assert "id" in data

    @pytest.mark.asyncio
    async def test_submit_answer_interview_not_found(self, test_client, db_session):
        """Submitting an answer for a non-existent interview should return 404."""
        response = await test_client.post(
            "/api/v1/interviews/99999/answers",
            json={
                "question_id": 99999,
                "answer": "My answer.",
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_answer_question_not_in_interview(self, test_client, db_session):
        """Submitting an answer where the question doesn't belong to the interview should return 404."""
        interview1 = Interview()
        interview2 = Interview()
        db_session.add_all([interview1, interview2])
        await db_session.flush()

        question = Question(
            interview_id=interview1.id, question="Q?", question_type="tech",
            difficulty="easy", sequence=1,
        )
        db_session.add(question)
        await db_session.commit()

        # Submit answer under interview2 for a question belonging to interview1
        response = await test_client.post(
            f"/api/v1/interviews/{interview2.id}/answers",
            json={"question_id": str(question.id), "answer": "Answer text."},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_empty_answer(self, test_client, db_session):
        """Empty answer should fail validation."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        question = Question(
            interview_id=interview.id, question="Q?", question_type="tech",
            difficulty="easy", sequence=1,
        )
        db_session.add(question)
        await db_session.commit()

        response = await test_client.post(
            f"/api/v1/interviews/{interview.id}/answers",
            json={"question_id": str(question.id), "answer": ""},
        )

        assert response.status_code == 422


class TestSubmitAnswerEdgeCases:
    @pytest.mark.asyncio
    async def test_submit_answer_invalid_question_id_format(self, test_client, db_session):
        """Passing a non-integer question_id should return 422."""
        interview = Interview()
        db_session.add(interview)
        await db_session.commit()

        response = await test_client.post(
            f"/api/v1/interviews/{interview.id}/answers",
            json={
                "question_id": "not-an-integer",
                "answer": "This is a valid answer.",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_answer_missing_question_id(self, test_client, db_session):
        """Missing question_id should return 422."""
        interview = Interview()
        db_session.add(interview)
        await db_session.commit()

        response = await test_client.post(
            f"/api/v1/interviews/{interview.id}/answers",
            json={"answer": "This answer has no question_id."},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_answer_missing_answer_field(self, test_client, db_session):
        """Missing answer field should return 422."""
        interview = Interview()
        db_session.add(interview)
        await db_session.commit()

        response = await test_client.post(
            f"/api/v1/interviews/{interview.id}/answers",
            json={"question_id": 1},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_answer_invalid_interview_id_format(self, test_client, db_session):
        """Passing a non-integer interview_id should return 422."""
        response = await test_client.post(
            "/api/v1/interviews/not-an-integer/answers",
            json={"question_id": 1, "answer": "Valid answer."},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_answer_whitespace_only(self, test_client, db_session):
        """Submitting only whitespace should fail validation (min_length=1 means stripped empty string)."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        question = Question(
            interview_id=interview.id, question="Q?", question_type="tech",
            difficulty="easy", sequence=1,
        )
        db_session.add(question)
        await db_session.commit()

        response = await test_client.post(
            f"/api/v1/interviews/{interview.id}/answers",
            json={"question_id": question.id, "answer": "   \t\n   "},
        )

        # The endpoint strips the answer, so whitespace-only becomes empty string
        # which should fail Pydantic min_length=1 validation
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_answer_max_length(self, test_client, db_session):
        """Submitting an answer at the max length boundary (5000 chars) should succeed."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        question = Question(
            interview_id=interview.id, question="Q?", question_type="tech",
            difficulty="easy", sequence=1,
        )
        db_session.add(question)
        await db_session.commit()

        long_answer = "A" * 5000

        response = await test_client.post(
            f"/api/v1/interviews/{interview.id}/answers",
            json={"question_id": question.id, "answer": long_answer},
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_submit_answer_exceeds_max_length(self, test_client, db_session):
        """Submitting an answer exceeding 5000 chars should return 422."""
        interview = Interview()
        db_session.add(interview)
        await db_session.commit()

        too_long_answer = "A" * 5001

        response = await test_client.post(
            f"/api/v1/interviews/{interview.id}/answers",
            json={"question_id": 1, "answer": too_long_answer},
        )

        assert response.status_code == 422


class TestEvaluateAnswer:
    @pytest.mark.asyncio
    async def test_evaluate_answer_success(self, test_client, db_session):
        """Evaluating an answer should return scores and feedback."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        jd = JobDescription(interview_id=interview.id, raw_text="Looking for a Python developer with async experience.")
        db_session.add(jd)
        await db_session.flush()

        question = Question(
            interview_id=interview.id, question="What is async/await?",
            question_type="technical", difficulty="medium", sequence=1,
        )
        db_session.add(question)
        await db_session.flush()

        answer = Answer(question_id=question.id, answer="Async/await enables non-blocking code execution.")
        db_session.add(answer)
        await db_session.commit()

        with patch("app.api.endpoints.answers.AnswerEvaluationAgent") as mock_agent_cls:
            mock_agent = mock_agent_cls.return_value
            mock_evaluation = AsyncMock()
            mock_evaluation.technical_score = 9
            mock_evaluation.communication_score = 8
            mock_evaluation.feedback = "Excellent explanation with clear examples."
            mock_agent.evaluate = AsyncMock(return_value=mock_evaluation)

            response = await test_client.post(
                f"/api/v1/interviews/{interview.id}/answers/{answer.id}/evaluate",
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["evaluation"]["technical_score"] == 9
        assert data["evaluation"]["communication_score"] == 8
        assert data["evaluation"]["feedback"] == "Excellent explanation with clear examples."

    @pytest.mark.asyncio
    async def test_evaluate_answer_not_found(self, test_client, db_session):
        """Evaluating a non-existent answer should return 404."""
        interview = Interview()
        db_session.add(interview)
        await db_session.commit()

        response = await test_client.post(
            f"/api/v1/interviews/{interview.id}/answers/99999/evaluate",
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_evaluate_already_evaluated(self, test_client, db_session):
        """A retry returns the saved evaluation without calling the model again."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        jd = JobDescription(interview_id=interview.id, raw_text="A" * 20)
        db_session.add(jd)
        await db_session.flush()

        question = Question(
            interview_id=interview.id, question="Q?", question_type="tech",
            difficulty="easy", sequence=1,
        )
        db_session.add(question)
        await db_session.flush()

        answer = Answer(question_id=question.id, answer="A.")
        db_session.add(answer)
        await db_session.flush()

        evaluation = Evaluation(
            answer_id=answer.id, technical_score=5, communication_score=5,
            feedback="Already evaluated previously.",
        )
        db_session.add(evaluation)
        await db_session.commit()

        with patch("app.api.endpoints.answers.AnswerEvaluationAgent") as mock_agent_cls:
            mock_agent = mock_agent_cls.return_value
            mock_eval = AsyncMock()
            mock_eval.technical_score = 9
            mock_eval.communication_score = 9
            mock_eval.feedback = "Excellent explanation covering key points."
            mock_agent.evaluate = AsyncMock(return_value=mock_eval)

            response = await test_client.post(
                f"/api/v1/interviews/{interview.id}/answers/{answer.id}/evaluate",
            )

        assert response.status_code == 200
        assert response.json()["evaluation"]["technical_score"] == 5
        mock_agent.evaluate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_evaluate_answer_wrong_interview(self, test_client, db_session):
        """Evaluating an answer under the wrong interview should return 404."""
        interview1 = Interview()
        interview2 = Interview()
        db_session.add_all([interview1, interview2])
        await db_session.flush()

        jd = JobDescription(interview_id=interview1.id, raw_text="Job description text")
        db_session.add(jd)
        await db_session.flush()

        question = Question(
            interview_id=interview1.id, question="What is async?",
            question_type="technical", difficulty="medium", sequence=1,
        )
        db_session.add(question)
        await db_session.flush()

        answer = Answer(question_id=question.id, answer="Async is for non-blocking I/O.")
        db_session.add(answer)
        await db_session.commit()

        response = await test_client.post(
            f"/api/v1/interviews/{interview2.id}/answers/{answer.id}/evaluate",
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_evaluate_answer_no_job_description(self, test_client, db_session):
        """Evaluating an answer where the interview has no job description should still succeed (JD is optional context)."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        question = Question(
            interview_id=interview.id, question="Tell me about yourself.",
            question_type="general", difficulty="easy", sequence=1,
        )
        db_session.add(question)
        await db_session.flush()

        answer = Answer(question_id=question.id, answer="I am a software engineer with 5 years experience.")
        db_session.add(answer)
        await db_session.commit()

        with patch("app.api.endpoints.answers.AnswerEvaluationAgent") as mock_agent_cls:
            mock_agent = mock_agent_cls.return_value
            mock_eval = AsyncMock()
            mock_eval.technical_score = 7
            mock_eval.communication_score = 8
            mock_eval.feedback = "Good introduction with relevant experience highlighted."
            mock_agent.evaluate = AsyncMock(return_value=mock_eval)

            response = await test_client.post(
                f"/api/v1/interviews/{interview.id}/answers/{answer.id}/evaluate",
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_evaluate_answer_llm_timeout(self, test_client, db_session):
        """LLM timeout during evaluation should return an appropriate error."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        jd = JobDescription(interview_id=interview.id, raw_text="Looking for Python dev.")
        db_session.add(jd)
        await db_session.flush()

        question = Question(
            interview_id=interview.id, question="Explain decorators.",
            question_type="technical", difficulty="hard", sequence=1,
        )
        db_session.add(question)
        await db_session.flush()

        answer = Answer(question_id=question.id, answer="Decorators wrap functions to extend behavior.")
        db_session.add(answer)
        await db_session.commit()

        with patch("app.api.endpoints.answers.AnswerEvaluationAgent") as mock_agent_cls:
            mock_agent = mock_agent_cls.return_value
            mock_agent.evaluate = AsyncMock(side_effect=Exception("LLM timeout"))

            response = await test_client.post(
                f"/api/v1/interviews/{interview.id}/answers/{answer.id}/evaluate",
            )

        assert response.status_code == 502

    @pytest.mark.asyncio
    async def test_evaluate_answer_invalid_answer_id_format(self, test_client, db_session):
        """Passing a non-integer answer_id should return 422."""
        interview = Interview()
        db_session.add(interview)
        await db_session.commit()

        response = await test_client.post(
            f"/api/v1/interviews/{interview.id}/answers/not-an-integer/evaluate",
        )

        assert response.status_code == 422


class TestAnswerModelRelationships:
    @pytest.mark.asyncio
    async def test_answer_evaluation_relationship(self, db_session):
        """Answer.evaluation should return the associated evaluation."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        question = Question(
            interview_id=interview.id, question="Q?", question_type="tech",
            difficulty="easy", sequence=1,
        )
        db_session.add(question)
        await db_session.flush()

        answer = Answer(question_id=question.id, answer="My answer.")
        db_session.add(answer)
        await db_session.flush()

        evaluation = Evaluation(
            answer_id=answer.id, technical_score=9, communication_score=8,
            feedback="Well structured response.",
        )
        db_session.add(evaluation)
        await db_session.commit()

        # Name the relationship: a plain refresh leaves it unloaded, and a
        # lazy load on an async session raises MissingGreenlet.
        await db_session.refresh(answer, ["evaluation"])
        assert answer.evaluation is not None
        assert answer.evaluation.technical_score == 9


class TestEvaluateAnswerModelFailures:
    """How each OpenRouter failure surfaces to the caller.

    Every branch here saved the answer before the model was called, so the
    messages all promise the answer survived. Two of the branches answer 502
    with different text, which is what the detail assertions pin down — a bare
    status check would pass against the wrong handler.
    """

    @pytest_asyncio.fixture
    async def answered(self, db_session):
        """An interview with one unevaluated answer, ready to evaluate."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        db_session.add(JobDescription(
            interview_id=interview.id, raw_text="Python backend role."
        ))
        question = Question(
            interview_id=interview.id, question="Explain the GIL.",
            question_type="technical", difficulty="hard", sequence=1,
        )
        db_session.add(question)
        await db_session.flush()

        answer = Answer(
            question_id=question.id,
            answer="The GIL serialises bytecode execution per interpreter.",
        )
        db_session.add(answer)
        await db_session.commit()
        return interview, answer

    @staticmethod
    def _evaluate_raising(error):
        """Patch the agent so evaluation raises `error`."""
        agent = patch("app.api.endpoints.answers.AnswerEvaluationAgent")
        mock_cls = agent.start()
        mock_cls.return_value.evaluate = AsyncMock(side_effect=error)
        return agent

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "error, expected_status, expected_detail",
        [
            (
                OpenRouterRateLimitError("429 from provider"),
                429,
                "The model is rate limited right now. Please wait a moment and try again.",
            ),
            (
                OpenRouterTimeoutError("read timeout after 90s"),
                503,
                "Could not reach the evaluation model. Your answer was saved — please try again.",
            ),
            (
                OpenRouterAPIError("upstream 500", 500, "bad gateway"),
                503,
                "Could not reach the evaluation model. Your answer was saved — please try again.",
            ),
            (
                OpenRouterTruncatedError("hit the token budget"),
                502,
                "The evaluation model returned an unusable response. Your answer was saved — please try again.",
            ),
            (
                OpenRouterValidationError("not the shape the schema wants"),
                502,
                "The evaluation model returned an unusable response. Your answer was saved — please try again.",
            ),
        ],
        ids=["rate-limited", "timeout", "api-error", "truncated", "malformed"],
    )
    async def test_model_failure_status_and_message(
        self, test_client, answered, error, expected_status, expected_detail
    ):
        interview, answer = answered

        agent = self._evaluate_raising(error)
        try:
            response = await test_client.post(
                f"/api/v1/interviews/{interview.id}/answers/{answer.id}/evaluate"
            )
        finally:
            agent.stop()

        assert response.status_code == expected_status
        assert response.json()["detail"] == expected_detail

    @pytest.mark.asyncio
    async def test_unexpected_error_uses_the_generic_message(
        self, test_client, answered
    ):
        """A non-OpenRouter failure gets the generic 502, not the model one."""
        interview, answer = answered

        agent = self._evaluate_raising(KeyError("technical_score"))
        try:
            response = await test_client.post(
                f"/api/v1/interviews/{interview.id}/answers/{answer.id}/evaluate"
            )
        finally:
            agent.stop()

        assert response.status_code == 502
        assert response.json()["detail"] == "Evaluation service temporarily unavailable"

    @pytest.mark.asyncio
    async def test_answer_survives_a_failed_evaluation(
        self, test_client, db_session, answered
    ):
        """The 503 promises the answer was saved — check that it was."""
        interview, answer = answered

        agent = self._evaluate_raising(OpenRouterTimeoutError("timeout"))
        try:
            await test_client.post(
                f"/api/v1/interviews/{interview.id}/answers/{answer.id}/evaluate"
            )
        finally:
            agent.stop()

        stored = await db_session.get(Answer, answer.id)
        assert stored is not None
        assert stored.answer.startswith("The GIL serialises")
