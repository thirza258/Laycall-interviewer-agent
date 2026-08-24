import pytest
from pydantic import ValidationError
from datetime import datetime, timezone

from app.schemas.resume import (
    ResumeCreate,
    ResumeResponse,
    ResumeUploadResponse,
    ResumeListResponse,
    ResumeUpdate,
)
from app.schemas.interview import (
    JobDescriptionCreate,
    InterviewCreate,
    JobDescriptionResponse,
    InterviewResponse,
)
from app.schemas.question import QuestionResponse
from app.schemas.answer import AnswerCreate, AnswerResponse
from app.schemas.agents import (
    JobDescriptionAnalysis,
    ResumeAnalysis,
    GapAnalysis,
    FinalInterviewSpec,
    InterviewQuestion,
    GeneratedQuestions,
    AnswerEvaluation,
    FinalAssessment,
)
from app.schemas.interview_result import InterviewResultsResponse


class TestResumeSchemas:
    def test_resume_create_valid(self):
        rc = ResumeCreate(interview_id=1)
        assert rc.interview_id == 1

    def test_resume_create_invalid_id(self):
        with pytest.raises(ValidationError):
            ResumeCreate(interview_id=0)
        with pytest.raises(ValidationError):
            ResumeCreate(interview_id=-1)

    def test_resume_response_from_attributes(self):
        now = datetime.now(timezone.utc)
        data = {"id": 1, "interview_id": 2, "file_path": "/a/b.pdf", "raw_text": "text", "created_at": now}
        rr = ResumeResponse.model_validate(data)
        assert rr.id == 1
        assert rr.file_path == "/a/b.pdf"

    def test_resume_update(self):
        ru = ResumeUpdate(raw_text="new text")
        assert ru.raw_text == "new text"

        ru_none = ResumeUpdate(raw_text=None)
        assert ru_none.raw_text is None

    def test_resume_list_response(self):
        rl = ResumeListResponse(resumes=[], total=0)
        assert rl.resumes == []
        assert rl.total == 0


class TestInterviewSchemas:
    def test_job_description_create_valid(self):
        jd = JobDescriptionCreate(raw_text="We need a Python developer with 3+ years experience")
        assert len(jd.raw_text) >= 10

    def test_job_description_create_too_short(self):
        with pytest.raises(ValidationError):
            JobDescriptionCreate(raw_text="short")

    def test_interview_create_valid(self):
        ic = InterviewCreate(
            job_description="Looking for a senior backend engineer with cloud experience",
            resume_id=1,
        )
        assert ic.resume_id == 1

    def test_interview_create_invalid_resume_id(self):
        with pytest.raises(ValidationError):
            InterviewCreate(job_description="A" * 20, resume_id=0)

    def test_job_description_response(self):
        now = datetime.now(timezone.utc)
        jdr = JobDescriptionResponse.model_validate({
            "id": 1, "interview_id": 1, "raw_text": "desc", "created_at": now
        })
        assert jdr.raw_text == "desc"


class TestQuestionSchema:
    def test_question_response(self):
        qr = QuestionResponse(question_id=1, question="What is Python?")
        assert qr.question == "What is Python?"


class TestAnswerSchemas:
    def test_answer_create_valid(self):
        ac = AnswerCreate(
            question_id=1,
            answer="Python is a high-level programming language.",
        )
        assert ac.question_id == 1
        assert len(ac.answer) >= 1

    def test_answer_create_empty(self):
        with pytest.raises(ValidationError):
            AnswerCreate(question_id=1, answer="")

    def test_answer_create_too_long(self):
        with pytest.raises(ValidationError):
            AnswerCreate(question_id=1, answer="x" * 5001)


    def test_answer_create_rejects_whitespace_only(self):
        """The answer is stored stripped, so a blank submission must not pass
        validation and land in the database as an empty string."""
        with pytest.raises(ValidationError):
            AnswerCreate(question_id=1, answer="   \t\n  ")

    def test_answer_create_strips_surrounding_whitespace(self):
        assert AnswerCreate(question_id=1, answer="  my answer  ").answer == "my answer"

    def test_answer_create_rejects_non_positive_question_id(self):
        with pytest.raises(ValidationError):
            AnswerCreate(question_id=0, answer="A valid answer.")


class TestAgentSchemas:
    def test_job_description_analysis(self):
        jda = JobDescriptionAnalysis(
            job_title="Engineer", company="ACME",
            required_skills=["Python"], preferred_skills=["Go"],
            responsibilities=["Build stuff"],
        )
        assert jda.job_title == "Engineer"
        assert jda.required_skills == ["Python"]

    def test_resume_analysis(self):
        ra = ResumeAnalysis(
            education=["BSc CS"], skills=["Python", "SQL"],
            projects=["Portfolio"], experience=["2yr at X Corp"],
        )
        assert "Python" in ra.skills

    def test_gap_analysis(self):
        ga = GapAnalysis(
            matched_skills=["Python"], missing_skills=["Java"],
            strengths=["Fast learner"], focus_areas=["Java", "System Design"],
        )
        assert ga.matched_skills == ["Python"]

    def test_final_interview_spec(self):
        spec = FinalInterviewSpec(
            target_role="Backend Engineer", difficulty="intermediate",
            required_skills=["Python"], focus_areas=["API Design"],
            candidate_strengths=["Python"], candidate_gaps=["Java"],
        )
        assert spec.difficulty == "intermediate"

    def test_interview_question(self):
        iq = InterviewQuestion(question="Explain OOP", type="technical", difficulty="medium")
        assert iq.type == "technical"

    def test_generated_questions(self):
        gq = GeneratedQuestions(questions=[
            InterviewQuestion(question="Q1", type="technical", difficulty="easy"),
            InterviewQuestion(question="Q2", type="behavioral", difficulty="medium"),
        ])
        assert len(gq.questions) == 2

    def test_answer_evaluation_valid(self):
        ae = AnswerEvaluation(
            technical_score=8, communication_score=7,
            feedback="Good answer with clear examples and proper terminology.",
        )
        assert ae.technical_score == 8
        assert ae.communication_score == 7

    def test_answer_evaluation_score_bounds(self):
        """Scores must be 0-10."""
        AnswerEvaluation(technical_score=0, communication_score=0, feedback="x" * 20)
        AnswerEvaluation(technical_score=10, communication_score=10, feedback="x" * 20)

        with pytest.raises(ValidationError):
            AnswerEvaluation(technical_score=-1, communication_score=5, feedback="x" * 20)
        with pytest.raises(ValidationError):
            AnswerEvaluation(technical_score=11, communication_score=5, feedback="x" * 20)

    def test_answer_evaluation_feedback_too_short(self):
        with pytest.raises(ValidationError):
            AnswerEvaluation(technical_score=5, communication_score=5, feedback="short")

    def test_final_assessment(self):
        fa = FinalAssessment(
            overall_score=85, technical_score=80, communication_score=90,
            strengths=["Good problem solving"], weaknesses=["Nervous"],
            recommendations=["Practice system design"],
        )
        assert fa.overall_score == 85

    def test_final_assessment_score_bounds(self):
        with pytest.raises(ValidationError):
            FinalAssessment(overall_score=101, technical_score=80, communication_score=90,
                            strengths=[], weaknesses=[], recommendations=[])

        with pytest.raises(ValidationError):
            FinalAssessment(overall_score=80, technical_score=101, communication_score=90,
                            strengths=[], weaknesses=[], recommendations=[])


class TestInterviewResultSchema:
    def test_interview_results_response(self):
        irr = InterviewResultsResponse(
            interview_id=1, status="completed", overall_score=85,
            technical_score=80, communication_score=90,
            strengths=["Python"], weaknesses=["Java"],
            recommendations=["Study more"],
        )
        assert irr.overall_score == 85
        assert irr.strengths == ["Python"]
