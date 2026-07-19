import pytest
from unittest.mock import patch, AsyncMock

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
                "question_id": "550e8400-e29b-41d4-a716-446655440000",
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

        with patch("app.api.endpoints.answer.AnswerEvaluationAgent") as mock_agent_cls:
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
        """Re-evaluating an already evaluated answer should return an error."""
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

        with patch("app.api.endpoints.answer.AnswerEvaluationAgent") as mock_agent_cls:
            mock_agent = mock_agent_cls.return_value
            mock_eval = AsyncMock()
            mock_eval.technical_score = 9
            mock_eval.communication_score = 9
            mock_eval.feedback = "Excellent explanation covering key points."
            mock_agent.evaluate = AsyncMock(return_value=mock_eval)

            response = await test_client.post(
                f"/api/v1/interviews/{interview.id}/answers/{answer.id}/evaluate",
            )

        assert response.status_code == 400


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

        await db_session.refresh(answer)
        assert answer.evaluation is not None
        assert answer.evaluation.technical_score == 9
