import json
import pytest
from unittest.mock import AsyncMock

from app.agents.resume_analyzer import ResumeAnalysisAgent
from app.llm.models import LLMResponse
from app.schemas.agents import ResumeAnalysis


class TestResumeAnalysisAgent:
    @pytest.fixture
    def mock_llm_client(self):
        client = AsyncMock()
        client.generate_completion = AsyncMock()
        return client

    @pytest.fixture
    def agent(self, mock_llm_client):
        return ResumeAnalysisAgent(mock_llm_client)

    @pytest.mark.asyncio
    async def test_analyze_returns_parsed_result(self, agent, mock_llm_client):
        response_data = {
            "education": ["BSc Computer Science"],
            "skills": ["Python", "React", "Docker"],
            "projects": ["E-commerce platform", "Chat app"],
            "experience": ["Software Engineer at X Corp (2021-2024)"],
        }
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps(response_data), model="test", finish_reason="stop"
        )

        result = await agent.analyze("Resume text here...")

        assert isinstance(result, ResumeAnalysis)
        assert result.education == ["BSc Computer Science"]
        assert result.skills == ["Python", "React", "Docker"]
        assert len(result.projects) == 2

    @pytest.mark.asyncio
    async def test_analyze_sends_correct_prompt(self, agent, mock_llm_client):
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps({
                "education": [], "skills": [],
                "projects": [], "experience": [],
            }),
            model="test", finish_reason="stop",
        )

        await agent.analyze("Resume content")

        call_args = mock_llm_client.generate_completion.call_args[0][0]
        assert call_args.temperature == 0.2
        assert call_args.response_format == {"type": "json_object"}
        assert call_args.max_tokens == 1200

    @pytest.mark.asyncio
    async def test_llm_error_propagates(self, agent, mock_llm_client):
        from app.llm.exceptions import OpenRouterAPIError

        mock_llm_client.generate_completion.side_effect = OpenRouterAPIError(
            message="down", status_code=503
        )
        with pytest.raises(OpenRouterAPIError):
            await agent.analyze("Resume text")
