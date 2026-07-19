import json
import pytest
from unittest.mock import AsyncMock

from app.agents.answer_evaluator import AnswerEvaluationAgent
from app.llm.models import LLMResponse
from app.schemas.agents import AnswerEvaluation


class TestAnswerEvaluationAgent:
    @pytest.fixture
    def mock_llm_client(self):
        client = AsyncMock()
        client.generate_completion = AsyncMock()
        return client

    @pytest.fixture
    def agent(self, mock_llm_client):
        return AnswerEvaluationAgent(mock_llm_client)

    @pytest.mark.asyncio
    async def test_evaluate_returns_scores(self, agent, mock_llm_client):
        response_data = {
            "technical_score": 8,
            "communication_score": 7,
            "feedback": "Good answer with clear explanation and relevant examples given.",
        }
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps(response_data), model="test", finish_reason="stop"
        )

        result = await agent.evaluate("What is Python?", "Python is a language.")

        assert isinstance(result, AnswerEvaluation)
        assert result.technical_score == 8
        assert result.communication_score == 7
        assert "Good answer" in result.feedback

    @pytest.mark.asyncio
    async def test_evaluate_includes_question_and_answer_in_prompt(self, agent, mock_llm_client):
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps({
                "technical_score": 5, "communication_score": 5,
                "feedback": "Adequate response but could be more detailed.",
            }),
            model="test", finish_reason="stop",
        )

        await agent.evaluate("Explain decorators", "A decorator wraps a function.")

        call_args = mock_llm_client.generate_completion.call_args[0][0]
        user_content = call_args.messages[-1]["content"]
        assert "Explain decorators" in user_content
        assert "A decorator wraps a function." in user_content

    @pytest.mark.asyncio
    async def test_evaluate_with_context(self, agent, mock_llm_client):
        """When context is provided, it should be included in the prompt."""
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps({
                "technical_score": 9, "communication_score": 8,
                "feedback": "Excellent response covering key job requirements.",
            }),
            model="test", finish_reason="stop",
        )

        context = {"job_description": "We need a Python developer", "focus": "backend"}
        await agent.evaluate("What is async?", "Async allows non-blocking I/O.", context=context)

        call_args = mock_llm_client.generate_completion.call_args[0][0]
        user_content = call_args.messages[-1]["content"]
        assert "ADDITIONAL CONTEXT" in user_content
        assert "Python developer" in user_content

    @pytest.mark.asyncio
    async def test_evaluate_without_context(self, agent, mock_llm_client):
        """Without context, the prompt should not include ADDITIONAL CONTEXT."""
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps({
                "technical_score": 5, "communication_score": 5,
                "feedback": "OK response, could be more specific.",
            }),
            model="test", finish_reason="stop",
        )

        await agent.evaluate("Q", "A", context=None)

        call_args = mock_llm_client.generate_completion.call_args[0][0]
        user_content = call_args.messages[-1]["content"]
        assert "ADDITIONAL CONTEXT" not in user_content

    @pytest.mark.asyncio
    async def test_evaluate_temperature(self, agent, mock_llm_client):
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps({
                "technical_score": 5, "communication_score": 5,
                "feedback": "Adequate but lacks specific examples.",
            }),
            model="test", finish_reason="stop",
        )

        await agent.evaluate("Q", "A")
        call_args = mock_llm_client.generate_completion.call_args[0][0]
        assert call_args.temperature == 0.3
        assert call_args.max_tokens == 400
