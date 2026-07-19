import json
import pytest
from unittest.mock import AsyncMock

from app.agents.spec_builder import SpecBuilderAgent
from app.llm.models import LLMResponse
from app.schemas.agents import (
    JobDescriptionAnalysis,
    ResumeAnalysis,
    GapAnalysis,
    FinalInterviewSpec,
)


class TestSpecBuilderAgent:
    @pytest.fixture
    def mock_llm_client(self):
        client = AsyncMock()
        client.generate_completion = AsyncMock()
        return client

    @pytest.fixture
    def agent(self, mock_llm_client):
        return SpecBuilderAgent(mock_llm_client)

    @pytest.fixture
    def jd_analysis(self):
        return JobDescriptionAnalysis(
            job_title="Backend Engineer", company="ACME",
            required_skills=["Python", "PostgreSQL"],
            preferred_skills=["Redis"],
            responsibilities=["Build APIs"],
        )

    @pytest.fixture
    def resume_analysis(self):
        return ResumeAnalysis(
            education=["BSc"], skills=["Python"],
            projects=["Web app"], experience=["2yr at X"],
        )

    @pytest.fixture
    def gap_analysis(self):
        return GapAnalysis(
            matched_skills=["Python"], missing_skills=["PostgreSQL"],
            strengths=["Fast learner"], focus_areas=["Databases"],
        )

    @pytest.mark.asyncio
    async def test_build_returns_spec(self, agent, mock_llm_client, jd_analysis, resume_analysis, gap_analysis):
        response_data = {
            "target_role": "Backend Engineer",
            "difficulty": "intermediate",
            "required_skills": ["Python", "PostgreSQL"],
            "focus_areas": ["Databases", "API Design"],
            "candidate_strengths": ["Python"],
            "candidate_gaps": ["PostgreSQL"],
        }
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps(response_data), model="test", finish_reason="stop"
        )

        result = await agent.build(jd_analysis, resume_analysis, gap_analysis)

        assert isinstance(result, FinalInterviewSpec)
        assert result.target_role == "Backend Engineer"
        assert result.difficulty == "intermediate"
        assert "Python" in result.candidate_strengths
        assert "PostgreSQL" in result.candidate_gaps

    @pytest.mark.asyncio
    async def test_build_sets_temperature(self, agent, mock_llm_client, jd_analysis, resume_analysis, gap_analysis):
        mock_llm_client.generate_completion.return_value = LLMResponse(
            content=json.dumps({
                "target_role": "Dev", "difficulty": "easy",
                "required_skills": [], "focus_areas": [],
                "candidate_strengths": [], "candidate_gaps": [],
            }),
            model="test", finish_reason="stop",
        )

        await agent.build(jd_analysis, resume_analysis, gap_analysis)

        call_args = mock_llm_client.generate_completion.call_args[0][0]
        assert call_args.temperature == 0.2
        assert call_args.max_tokens == 600
