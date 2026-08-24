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


class TestRecoversUsableShapes:
    """Models drift from the requested shape; only unusable answers should fail."""

    def test_extracts_json_from_surrounding_prose(self):
        content = (
            'Sure! Here is the analysis you asked for:\n'
            '{"matched_skills": ["Python"], "missing_skills": []}\n'
            'Let me know if you need more detail.'
        )
        result = parse_and_validate_llm_json(content, GapAnalysis)
        assert result.matched_skills == ["Python"]

    def test_unwraps_a_single_wrapper_key(self):
        content = '{"gap_analysis": {"matched_skills": ["Go"], "focus_areas": ["gRPC"]}}'
        result = parse_and_validate_llm_json(content, GapAnalysis)
        assert result.matched_skills == ["Go"]
        assert result.focus_areas == ["gRPC"]

    def test_wraps_a_bare_array_for_a_single_list_field(self):
        from app.schemas.agents import GeneratedQuestions

        content = json.dumps([
            {"question": "What is a deadlock?", "type": "technical", "difficulty": "medium"},
            {"question": "Tell me about a conflict.", "type": "behavioral", "difficulty": "easy"},
        ])
        result = parse_and_validate_llm_json(content, GeneratedQuestions)
        assert len(result.questions) == 2

    def test_ignores_extra_fields(self):
        content = '{"matched_skills": ["SQL"], "confidence": 0.9, "notes": "n/a"}'
        assert parse_and_validate_llm_json(content, GapAnalysis).matched_skills == ["SQL"]

    def test_rejects_an_upstream_error_object(self):
        """Every GapAnalysis field has a default, so this would otherwise
        validate into an empty analysis and poison the rest of the pipeline."""
        content = '{"error": {"code": 429, "message": "rate limited"}}'
        with pytest.raises(OpenRouterValidationError):
            parse_and_validate_llm_json(content, GapAnalysis)

    def test_rejects_a_refusal_string_in_json(self):
        with pytest.raises(OpenRouterValidationError):
            parse_and_validate_llm_json('"I cannot help with that"', GapAnalysis)

    def test_reports_the_target_model_in_the_error(self):
        with pytest.raises(OpenRouterValidationError, match="GapAnalysis"):
            parse_and_validate_llm_json('{"unrelated": 1}', GapAnalysis)
