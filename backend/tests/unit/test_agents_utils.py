import json
import pytest

from app.agents.utils import parse_and_validate_llm_json
from app.llm.exceptions import OpenRouterValidationError
from app.schemas.agents import GapAnalysis


class TestParseAndValidateLLMJson:
    def test_parses_plain_json(self):
        content = '{"matched_skills": ["a"], "missing_skills": ["b"], "strengths": ["c"], "focus_areas": ["d"]}'
        result = parse_and_validate_llm_json(content, GapAnalysis)
        assert result.matched_skills == ["a"]
        assert result.missing_skills == ["b"]

    def test_strips_markdown_code_fence(self):
        content = '```json\n{"matched_skills": ["a"], "missing_skills": ["b"], "strengths": ["c"], "focus_areas": ["d"]}\n```'
        result = parse_and_validate_llm_json(content, GapAnalysis)
        assert isinstance(result, GapAnalysis)

    def test_strips_markdown_without_language(self):
        content = '```\n{"matched_skills": ["a"], "missing_skills": ["b"], "strengths": ["c"], "focus_areas": ["d"]}\n```'
        result = parse_and_validate_llm_json(content, GapAnalysis)
        assert isinstance(result, GapAnalysis)

    def test_raises_on_invalid_json(self):
        content = "not valid json at all"
        with pytest.raises(OpenRouterValidationError):
            parse_and_validate_llm_json(content, GapAnalysis)

    def test_raises_on_wrong_schema(self):
        content = '{"wrong_field": "value"}'
        with pytest.raises(OpenRouterValidationError):
            parse_and_validate_llm_json(content, GapAnalysis)

    def test_handles_empty_string(self):
        with pytest.raises(OpenRouterValidationError):
            parse_and_validate_llm_json("", GapAnalysis)

    def test_handles_nested_json(self):
        """Should work with nested structures."""
        from app.schemas.agents import FinalInterviewSpec

        content = json.dumps({
            "target_role": "Engineer",
            "difficulty": "hard",
            "required_skills": ["Python"],
            "focus_areas": ["API"],
            "candidate_strengths": ["Django"],
            "candidate_gaps": ["Go"],
        })
        result = parse_and_validate_llm_json(content, FinalInterviewSpec)
        assert result.target_role == "Engineer"
