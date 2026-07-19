import json
import pytest
from unittest.mock import AsyncMock

from app.agents.gap_analysis_agent import GapAnalysisAgent
from app.llm.models import LLMResponse
from app.schemas.agents import JobDescriptionAnalysis, ResumeAnalysis, GapAnalysis


class TestGapAnalysisAgent:
    @pytest.fixture
    def mock_llm_client(self):
        client = AsyncMock()
        client.generate_completion = AsyncMock()
        return client

    @pytest.fixture
    def agent(self, mock_llm_client):
        return GapAnalysisAgent(mock_llm_client)

    @pytest.fixture
    def jd_analysis(self):
        return JobDescriptionAnalysis(
            job_title="Engineer", company="ACME",
            required_skills=["Python", "Docker"],
            preferred_skills=["Kubernetes"],
            responsibilities=["Build APIs"],
        )

    @pytest.fixture
    def resume_analysis(self):
        return ResumeAnalysis(
            education=["BSc"], skills=["Python"],
            projects=["App"], experience=["2yr"],
        )

    @pytest.mark.asyncio
    async def test_analyze_returns_gap_result(self, agent, mock_llm_client, jd_analysis, resume_analysis):
        response_data = {
            "matched_skills": ["Python"],
            "missing_skills": ["Docker", "Kubernetes"],
            "strengths": ["Strong Python background"],
            "focus_areas": ["Containerization", "Orchestration"],
        }
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps(response_data), model="test", finish_reason="stop"
        )

        result = await agent.analyze(jd_analysis, resume_analysis)

        assert isinstance(result, GapAnalysis)
        assert result.matched_skills == ["Python"]
        assert "Docker" in result.missing_skills

    @pytest.mark.asyncio
    async def test_analyze_includes_both_analyses_in_prompt(self, agent, mock_llm_client, jd_analysis, resume_analysis):
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps({
                "matched_skills": [], "missing_skills": [],
                "strengths": [], "focus_areas": [],
            }),
            model="test", finish_reason="stop",
        )

        await agent.analyze(jd_analysis, resume_analysis)

        call_args = mock_llm_client.generate_completion.call_args[0][0]
        user_content = call_args.messages[-1]["content"]
        assert "Engineer" in user_content
        assert "BSc" in user_content
        assert call_args.temperature == 0.2
        assert call_args.max_tokens == 600
