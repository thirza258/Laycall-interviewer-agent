import json
import pytest
from unittest.mock import AsyncMock

from app.agents.job_description_parser import JobDescriptionParserAgent
from app.llm.models import LLMResponse
from app.schemas.agents import JobDescriptionAnalysis


class TestJobDescriptionParserAgent:
    @pytest.fixture
    def mock_llm_client(self):
        client = AsyncMock()
        client.generate_completion = AsyncMock()
        return client

    @pytest.fixture
    def agent(self, mock_llm_client):
        return JobDescriptionParserAgent(mock_llm_client)

    @pytest.mark.asyncio
    async def test_analyze_returns_parsed_result(self, agent, mock_llm_client):
        response_data = {
            "job_title": "Senior Backend Engineer",
            "company": "Tech Corp",
            "required_skills": ["Python", "FastAPI", "PostgreSQL"],
            "preferred_skills": ["Docker", "Kubernetes"],
            "responsibilities": ["Design APIs", "Mentor juniors"],
        }
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps(response_data), model="test", finish_reason="stop"
        )

        result = await agent.analyze("We need a backend engineer...")

        assert isinstance(result, JobDescriptionAnalysis)
        assert result.job_title == "Senior Backend Engineer"
        assert result.required_skills == ["Python", "FastAPI", "PostgreSQL"]
        assert result.preferred_skills == ["Docker", "Kubernetes"]

    @pytest.mark.asyncio
    async def test_analyze_sends_correct_prompt(self, agent, mock_llm_client):
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps({
                "job_title": "Dev", "company": "Co",
                "required_skills": [], "preferred_skills": [],
                "responsibilities": [],
            }),
            model="test", finish_reason="stop",
        )

        await agent.analyze("Job description text here")

        call_args = mock_llm_client.generate_completion.call_args[0][0]
        assert call_args.temperature == 0.1
        assert call_args.response_format == {"type": "json_object"}
        assert call_args.max_tokens == 800
        assert "Job description text here" in call_args.messages[-1]["content"]

    @pytest.mark.asyncio
    async def test_empty_job_description(self, agent, mock_llm_client):
        """Agent should still make the LLM call with empty text."""
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps({
                "job_title": "Unknown", "company": "Unknown",
                "required_skills": [], "preferred_skills": [],
                "responsibilities": [],
            }),
            model="test", finish_reason="stop",
        )
        result = await agent.analyze("")
        assert isinstance(result, JobDescriptionAnalysis)
        assert result.job_title == "Unknown"
