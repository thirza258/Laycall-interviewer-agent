import json
import pytest
from unittest.mock import AsyncMock

from app.agents.question_generator import QuestionGeneratorAgent
from app.llm.models import LLMResponse
from app.schemas.agents import FinalInterviewSpec


class TestQuestionGeneratorAgent:
    @pytest.fixture
    def mock_llm_client(self):
        client = AsyncMock()
        client.generate_completion = AsyncMock()
        return client

    @pytest.fixture
    def agent(self, mock_llm_client):
        return QuestionGeneratorAgent(mock_llm_client)

    @pytest.fixture
    def spec(self):
        return FinalInterviewSpec(
            target_role="Backend Engineer",
            difficulty="intermediate",
            required_skills=["Python", "FastAPI", "PostgreSQL"],
            focus_areas=["API Design", "Database Optimization"],
            candidate_strengths=["Python", "Problem solving"],
            candidate_gaps=["PostgreSQL", "System Design"],
        )

    @pytest.mark.asyncio
    async def test_generate_returns_list_of_dicts(self, agent, mock_llm_client, spec):
        questions = [
            {"question": "Explain REST principles", "type": "technical", "difficulty": "easy"},
            {"question": "How do you optimize a query?", "type": "technical", "difficulty": "medium"},
            {"question": "Design a URL shortener", "type": "system_design", "difficulty": "hard"},
        ]
        response_data = {"questions": questions}
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps(response_data), model="test", finish_reason="stop"
        )

        result = await agent.generate(spec)

        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["question"] == "Explain REST principles"
        assert result[0]["type"] == "technical"
        assert result[0]["difficulty"] == "easy"

    @pytest.mark.asyncio
    async def test_generate_sets_higher_temperature(self, agent, mock_llm_client, spec):
        """Question generation should use higher temperature for creativity."""
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps({"questions": []}), model="test", finish_reason="stop"
        )

        await agent.generate(spec)

        call_args = mock_llm_client.generate_completion.call_args[0][0]
        assert call_args.temperature == 0.7
        assert call_args.max_tokens == 4000
        # Verify spec data is included in the prompt
        user_content = call_args.messages[-1]["content"]
        assert "Backend Engineer" in user_content
        assert "API Design" in user_content

    @pytest.mark.asyncio
    async def test_generate_includes_focus_areas(self, agent, mock_llm_client, spec):
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps({"questions": []}), model="test", finish_reason="stop"
        )

        await agent.generate(spec)

        call_args = mock_llm_client.generate_completion.call_args[0][0]
        user_content = call_args.messages[-1]["content"]
        assert "Database Optimization" in user_content
        assert "PostgreSQL" in user_content
