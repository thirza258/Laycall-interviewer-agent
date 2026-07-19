import json
import pytest
from unittest.mock import AsyncMock

from app.agents.final_review_agent import FinalReviewAgent
from app.llm.models import LLMResponse
from app.schemas.agents import FinalAssessment


class TestFinalReviewAgent:
    @pytest.fixture
    def mock_llm_client(self):
        client = AsyncMock()
        client.generate_completion = AsyncMock()
        return client

    @pytest.fixture
    def agent(self, mock_llm_client):
        return FinalReviewAgent(mock_llm_client)

    @pytest.fixture
    def questions(self):
        return [
            {"question": "What is Python?", "type": "technical", "difficulty": "easy"},
            {"question": "Explain async/await", "type": "technical", "difficulty": "medium"},
        ]

    @pytest.fixture
    def answers(self):
        return [
            {"answer": "Python is a programming language."},
            {"answer": "async/await enables non-blocking execution."},
        ]

    @pytest.fixture
    def evaluations(self):
        return [
            {"technical_score": 8, "communication_score": 7, "feedback": "Good"},
            {"technical_score": 6, "communication_score": 8, "feedback": "OK"},
        ]

    @pytest.mark.asyncio
    async def test_generate_assessment_returns_result(self, agent, mock_llm_client, questions, answers, evaluations):
        response_data = {
            "overall_score": 75,
            "technical_score": 70,
            "communication_score": 80,
            "strengths": ["Good basics", "Clear communication"],
            "weaknesses": ["Lacks depth in async"],
            "recommendations": ["Study advanced Python", "Practice system design"],
        }
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps(response_data), model="test", finish_reason="stop"
        )

        result = await agent.generate_assessment(questions, answers, evaluations)

        assert isinstance(result, FinalAssessment)
        assert result.overall_score == 75
        assert result.technical_score == 70
        assert result.communication_score == 80
        assert len(result.strengths) == 2
        assert len(result.weaknesses) == 2

    @pytest.mark.asyncio
    async def test_generate_includes_job_context(self, agent, mock_llm_client, questions, answers, evaluations):
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps({
                "overall_score": 50, "technical_score": 50, "communication_score": 50,
                "strengths": [], "weaknesses": [], "recommendations": [],
            }),
            model="test", finish_reason="stop",
        )

        job_context = {"target_role": "Backend Developer", "required_skills": ["Python"]}
        await agent.generate_assessment(questions, answers, evaluations, job_context=job_context)

        call_args = mock_llm_client.generate_completion.call_args[0][0]
        user_content = call_args.messages[-1]["content"]
        assert "Backend Developer" in user_content
        assert "Python" in user_content

    @pytest.mark.asyncio
    async def test_generate_truncates_long_content(self, agent, mock_llm_client, questions, answers, evaluations):
        """Long questions and answers should be truncated."""
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps({
                "overall_score": 50, "technical_score": 50, "communication_score": 50,
                "strengths": [], "weaknesses": [], "recommendations": [],
            }),
            model="test", finish_reason="stop",
        )

        long_answer = [{"answer": "x" * 500}]
        await agent.generate_assessment(questions, long_answer, evaluations)

        call_args = mock_llm_client.generate_completion.call_args[0][0]
        user_content = call_args.messages[-1]["content"]
        # Should be truncated to 300 chars
        assert len("x" * 300) < 500

    @pytest.mark.asyncio
    async def test_generate_sets_temperature(self, agent, mock_llm_client, questions, answers, evaluations):
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps({
                "overall_score": 50, "technical_score": 50, "communication_score": 50,
                "strengths": [], "weaknesses": [], "recommendations": [],
            }),
            model="test", finish_reason="stop",
        )

        await agent.generate_assessment(questions, answers, evaluations)

        call_args = mock_llm_client.generate_completion.call_args[0][0]
        assert call_args.temperature == 0.2
        assert call_args.max_tokens == 800

    @pytest.mark.asyncio
    async def test_generate_handles_empty_lists(self, agent, mock_llm_client):
        """Should work with empty questions/answers/evaluations."""
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps({
                "overall_score": 0, "technical_score": 0, "communication_score": 0,
                "strengths": ["N/A"], "weaknesses": ["No questions answered"],
                "recommendations": ["Complete the interview"],
            }),
            model="test", finish_reason="stop",
        )

        result = await agent.generate_assessment([], [], [])
        assert isinstance(result, FinalAssessment)
