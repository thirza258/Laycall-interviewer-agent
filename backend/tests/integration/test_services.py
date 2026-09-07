"""Service-layer tests against a real database session.

These used to be mock-based unit tests. A mocked session cannot catch the
failure that mattered most here: writing into `spec.json_data` in place, which
SQLAlchemy never flushed, so every analysis after the first was silently lost.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.db.models.answer import Answer
from app.db.models.evaluation import Evaluation
from app.db.models.interview import Interview, InterviewStatus
from app.db.models.interview_spec import InterviewSpec
from app.db.models.job_description import JobDescription
from app.db.models.question import Question
from app.db.models.resume import Resume
from app.schemas.agents import (
    AnswerEvaluation,
    FinalInterviewSpec,
    GapAnalysis,
    JobDescriptionAnalysis,
    ResumeAnalysis,
)
from app.services.evaluation_service import EvaluationService
from app.services.interview_completion_service import InterviewCompletionService
from app.services.interview_finalization import InterviewFinalizationService
from app.services.interview_orchestration import InterviewOrchestrationService
from app.services.interview_spec_service import InterviewSpecService
from app.services.resume_extraction import ResumeExtractionService


async def _interview(db, status=InterviewStatus.PENDING) -> Interview:
    interview = Interview(status=status)
    db.add(interview)
    await db.flush()
    return interview


async def _question(db, interview_id: int, sequence: int) -> Question:
    question = Question(
        interview_id=interview_id,
        question=f"Question {sequence}?",
        question_type="technical",
        difficulty="medium",
        sequence=sequence,
    )
    db.add(question)
    await db.flush()
    return question


async def _answer(db, question_id: int, text: str = "An answer.") -> Answer:
    answer = Answer(question_id=question_id, answer=text)
    db.add(answer)
    await db.flush()
    return answer


async def _evaluation(db, answer_id: int, technical=8, communication=7) -> Evaluation:
    evaluation = Evaluation(
        answer_id=answer_id,
        technical_score=technical,
        communication_score=communication,
        feedback="Clear reasoning, could use a concrete example.",
    )
    db.add(evaluation)
    await db.flush()
    return evaluation


class TestInterviewSpecService:
    async def test_creates_spec_row_for_new_interview(self, db_session):
        interview = await _interview(db_session)
        service = InterviewSpecService(db_session)

        result = await service._upsert_spec(interview.id, "test_key", {"data": "value"})

        assert result["test_key"] == {"data": "value"}
        stored = (await db_session.execute(
            select(InterviewSpec).where(InterviewSpec.interview_id == interview.id)
        )).scalar_one()
        assert stored.json_data == {"test_key": {"data": "value"}}

    async def test_successive_saves_are_persisted(self, db_session):
        """Regression: in-place json_data writes must reach the database.

        Every save after the first used to be dropped, which left the interview
        spec, the question set and the final assessment permanently empty.
        """
        interview = await _interview(db_session)
        service = InterviewSpecService(db_session)

        await service.save_jd_analysis(
            interview.id,
            JobDescriptionAnalysis(job_title="Dev", company="Acme", required_skills=["Python"]),
        )
        await service.save_resume_analysis(
            interview.id, ResumeAnalysis(skills=["Python", "SQL"])
        )
        await service.save_gap_analysis(
            interview.id, GapAnalysis(matched_skills=["Python"], missing_skills=["Go"])
        )
        await service.save_final_spec(
            interview.id, FinalInterviewSpec(target_role="Dev", difficulty="mid")
        )
        await service.save_questions(
            interview.id, [{"question": "Q1", "type": "technical", "difficulty": "easy"}]
        )

        # Read through a brand-new identity map: this is what the next request
        # would see.
        db_session.expunge_all()
        stored = (await db_session.execute(
            select(InterviewSpec).where(InterviewSpec.interview_id == interview.id)
        )).scalar_one()

        assert set(stored.json_data) == {
            "jd_analysis", "resume_analysis", "gap_analysis", "final_spec", "questions",
        }
        assert stored.json_data["jd_analysis"]["job_title"] == "Dev"
        assert stored.json_data["gap_analysis"]["missing_skills"] == ["Go"]
        assert stored.json_data["questions"][0]["question"] == "Q1"

    async def test_second_save_keeps_earlier_keys(self, db_session):
        interview = await _interview(db_session)
        service = InterviewSpecService(db_session)

        await service._upsert_spec(interview.id, "existing_key", "old_value")
        result = await service._upsert_spec(interview.id, "new_key", "new_value")

        assert result == {"existing_key": "old_value", "new_key": "new_value"}

    async def test_one_spec_row_per_interview(self, db_session):
        interview = await _interview(db_session)
        service = InterviewSpecService(db_session)

        await service._upsert_spec(interview.id, "a", 1)
        await service._upsert_spec(interview.id, "b", 2)

        rows = (await db_session.execute(
            select(InterviewSpec).where(InterviewSpec.interview_id == interview.id)
        )).scalars().all()
        assert len(rows) == 1


class TestInterviewCompletionService:
    async def test_all_questions_answered_marks_interview_complete(self, db_session):
        interview = await _interview(db_session, InterviewStatus.IN_PROGRESS)
        for i in (1, 2, 3):
            question = await _question(db_session, interview.id, i)
            await _answer(db_session, question.id)
        await db_session.commit()

        is_complete, summary = await InterviewCompletionService(db_session).check_and_update(
            interview.id
        )

        assert is_complete is True
        assert summary["total_questions"] == 3
        assert summary["answered_count"] == 3
        assert summary["completion_percentage"] == 100.0
        assert summary["status_updated"] is True
        assert interview.status == InterviewStatus.COMPLETED

    async def test_partially_answered_interview_is_not_complete(self, db_session):
        interview = await _interview(db_session, InterviewStatus.IN_PROGRESS)
        questions = [await _question(db_session, interview.id, i) for i in (1, 2, 3, 4, 5)]
        for question in questions[:2]:
            await _answer(db_session, question.id)
        await db_session.commit()

        is_complete, summary = await InterviewCompletionService(db_session).check_and_update(
            interview.id
        )

        assert is_complete is False
        assert summary["completion_percentage"] == 40.0
        assert interview.status == InterviewStatus.IN_PROGRESS

    async def test_repeated_answers_to_one_question_do_not_complete_it(self, db_session):
        """Counting answer rows would call a two-question interview finished
        after the candidate answered the first question twice."""
        interview = await _interview(db_session, InterviewStatus.IN_PROGRESS)
        first = await _question(db_session, interview.id, 1)
        await _question(db_session, interview.id, 2)
        await _answer(db_session, first.id, "First attempt.")
        await _answer(db_session, first.id, "Second attempt.")
        await db_session.commit()

        is_complete, summary = await InterviewCompletionService(db_session).check_and_update(
            interview.id
        )

        assert is_complete is False
        assert summary["answered_count"] == 1
        assert summary["completion_percentage"] == 50.0

    async def test_interview_without_questions_is_not_complete(self, db_session):
        interview = await _interview(db_session)
        await db_session.commit()

        is_complete, summary = await InterviewCompletionService(db_session).check_and_update(
            interview.id
        )

        assert is_complete is False
        assert summary["total_questions"] == 0
        assert summary["completion_percentage"] == 0

    async def test_already_completed_interview_is_not_updated_twice(self, db_session):
        interview = await _interview(db_session, InterviewStatus.COMPLETED)
        question = await _question(db_session, interview.id, 1)
        await _answer(db_session, question.id)
        await db_session.commit()

        is_complete, summary = await InterviewCompletionService(db_session).check_and_update(
            interview.id
        )

        assert is_complete is True
        assert summary["status_updated"] is False


class TestEvaluationService:
    async def test_saves_evaluation(self, db_session):
        interview = await _interview(db_session)
        question = await _question(db_session, interview.id, 1)
        answer = await _answer(db_session, question.id)
        await db_session.commit()

        saved = await EvaluationService(db_session).save_evaluation(
            answer.id,
            AnswerEvaluation(
                technical_score=9,
                communication_score=8,
                feedback="Precise answer that covered the trade-offs well.",
            ),
        )

        assert saved.id is not None
        assert saved.answer_id == answer.id
        assert saved.technical_score == 9

    async def test_duplicate_evaluation_raises(self, db_session):
        interview = await _interview(db_session)
        question = await _question(db_session, interview.id, 1)
        answer = await _answer(db_session, question.id)
        await _evaluation(db_session, answer.id)
        await db_session.commit()

        with pytest.raises(ValueError, match="already exists"):
            await EvaluationService(db_session).save_evaluation(
                answer.id,
                AnswerEvaluation(
                    technical_score=5,
                    communication_score=5,
                    feedback="A second evaluation for the same answer.",
                ),
            )


class TestResumeExtractionService:
    @staticmethod
    def _docx(tmp_path, text: str) -> str:
        from docx import Document

        path = tmp_path / "resume.docx"
        document = Document()
        document.add_paragraph(text)
        document.save(path)
        return str(path)

    async def test_extracts_and_saves_raw_text(self, db_session, tmp_path):
        interview = await _interview(db_session)
        resume = Resume(interview_id=interview.id, file_path="resumes/1/resume.docx")
        db_session.add(resume)
        await db_session.commit()

        local_copy = self._docx(tmp_path, "Jane Doe — Backend Engineer")

        with patch(
            "app.services.resume_extraction.MinIOClient.download_to_temp",
            return_value=local_copy,
        ) as download:
            text = await ResumeExtractionService(db_session).extract_and_save(resume.id)

        download.assert_called_once_with("resumes/1/resume.docx")
        assert "Jane Doe" in text
        await db_session.refresh(resume)
        assert "Backend Engineer" in resume.raw_text

    async def test_removes_the_temporary_file(self, db_session, tmp_path):
        interview = await _interview(db_session)
        resume = Resume(interview_id=interview.id, file_path="resumes/1/resume.docx")
        db_session.add(resume)
        await db_session.commit()

        local_copy = self._docx(tmp_path, "Some resume text")

        with patch(
            "app.services.resume_extraction.MinIOClient.download_to_temp",
            return_value=local_copy,
        ):
            await ResumeExtractionService(db_session).extract_and_save(resume.id)

        assert not (tmp_path / "resume.docx").exists()

    async def test_unparsable_file_leaves_raw_text_unset(self, db_session, tmp_path):
        interview = await _interview(db_session)
        resume = Resume(interview_id=interview.id, file_path="resumes/1/resume.docx")
        db_session.add(resume)
        await db_session.commit()

        broken = tmp_path / "resume.docx"
        broken.write_bytes(b"not really a docx")

        with patch(
            "app.services.resume_extraction.MinIOClient.download_to_temp",
            return_value=str(broken),
        ):
            text = await ResumeExtractionService(db_session).extract_and_save(resume.id)

        assert text == ""
        await db_session.refresh(resume)
        assert resume.raw_text is None

    async def test_missing_resume_raises(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await ResumeExtractionService(db_session).extract_and_save(99999)


class TestInterviewFinalizationService:
    async def test_returns_none_while_questions_remain(self, db_session, fake_llm_client):
        interview = await _interview(db_session, InterviewStatus.IN_PROGRESS)
        first = await _question(db_session, interview.id, 1)
        await _question(db_session, interview.id, 2)
        answer = await _answer(db_session, first.id)
        await _evaluation(db_session, answer.id)
        await db_session.commit()

        service = InterviewFinalizationService(db_session, fake_llm_client)
        assert await service.finalize_if_complete(interview.id) is None
        fake_llm_client.generate_completion.assert_not_awaited()

    async def test_generates_and_stores_the_assessment(self, db_session, fake_llm_client):
        interview = await _interview(db_session, InterviewStatus.IN_PROGRESS)
        for i in (1, 2):
            question = await _question(db_session, interview.id, i)
            answer = await _answer(db_session, question.id, f"Answer {i}")
            await _evaluation(db_session, answer.id)
        await db_session.commit()

        assessment = await InterviewFinalizationService(
            db_session, fake_llm_client
        ).finalize_if_complete(interview.id)

        assert assessment["overall_score"] == 82
        assert interview.status == InterviewStatus.COMPLETED

        db_session.expunge_all()
        stored = (await db_session.execute(
            select(InterviewSpec).where(InterviewSpec.interview_id == interview.id)
        )).scalar_one()
        assert stored.json_data["final_assessment"]["overall_score"] == 82

    async def test_is_idempotent(self, db_session, fake_llm_client):
        interview = await _interview(db_session, InterviewStatus.IN_PROGRESS)
        question = await _question(db_session, interview.id, 1)
        answer = await _answer(db_session, question.id)
        await _evaluation(db_session, answer.id)
        await db_session.commit()

        service = InterviewFinalizationService(db_session, fake_llm_client)
        first = await service.finalize_if_complete(interview.id)
        second = await service.finalize_if_complete(interview.id)

        assert first == second
        fake_llm_client.generate_completion.assert_awaited_once()

    async def test_only_evaluated_answers_reach_the_agent_in_order(
        self, db_session, fake_llm_client
    ):
        """The agent zips questions, answers and evaluations together, so an
        answer without an evaluation must drop out of all three lists."""
        interview = await _interview(db_session, InterviewStatus.IN_PROGRESS)
        first = await _question(db_session, interview.id, 1)
        second = await _question(db_session, interview.id, 2)
        third = await _question(db_session, interview.id, 3)

        first_answer = await _answer(db_session, first.id, "Answer one")
        await _evaluation(db_session, first_answer.id, technical=3, communication=4)
        # The second answer is never evaluated.
        await _answer(db_session, second.id, "Answer two")
        third_answer = await _answer(db_session, third.id, "Answer three")
        await _evaluation(db_session, third_answer.id, technical=9, communication=10)
        await db_session.commit()

        with patch(
            "app.services.interview_finalization.FinalReviewAgent"
        ) as agent_cls:
            agent = agent_cls.return_value
            agent.generate_assessment = AsyncMock(
                return_value=type(
                    "Assessment",
                    (),
                    {"overall_score": 50, "model_dump": lambda self: {"overall_score": 50}},
                )()
            )
            await InterviewFinalizationService(
                db_session, fake_llm_client
            ).finalize_if_complete(interview.id)

        kwargs = agent.generate_assessment.await_args.kwargs
        assert [q["question"] for q in kwargs["questions"]] == ["Question 1?", "Question 3?"]
        assert [a["answer"] for a in kwargs["answers"]] == ["Answer one", "Answer three"]
        assert [e["technical_score"] for e in kwargs["evaluations"]] == [3, 9]

    async def test_passes_the_stored_spec_as_job_context(self, db_session, fake_llm_client):
        interview = await _interview(db_session, InterviewStatus.IN_PROGRESS)
        question = await _question(db_session, interview.id, 1)
        answer = await _answer(db_session, question.id)
        await _evaluation(db_session, answer.id)
        db_session.add(JobDescription(interview_id=interview.id, raw_text="Backend role"))
        await db_session.commit()
        await InterviewSpecService(db_session).save_final_spec(
            interview.id,
            FinalInterviewSpec(
                target_role="Staff Engineer", difficulty="senior", required_skills=["Go"]
            ),
        )

        await InterviewFinalizationService(
            db_session, fake_llm_client
        ).finalize_if_complete(interview.id)

        request = fake_llm_client.generate_completion.await_args.args[0]
        prompt = request.messages[-1]["content"]
        assert "Staff Engineer" in prompt
        assert "Go" in prompt

    async def test_complete_interview_without_evaluations_is_skipped(
        self, db_session, fake_llm_client
    ):
        interview = await _interview(db_session, InterviewStatus.IN_PROGRESS)
        question = await _question(db_session, interview.id, 1)
        await _answer(db_session, question.id)
        await db_session.commit()

        assessment = await InterviewFinalizationService(
            db_session, fake_llm_client
        ).finalize_if_complete(interview.id)

        assert assessment is None
        fake_llm_client.generate_completion.assert_not_awaited()


class TestInterviewSpecServiceRecovery:
    async def test_spec_row_with_null_json_data_is_repaired(self, db_session):
        """A spec row can predate its json_data column being populated.

        Writing a key straight into None raises TypeError, which would fail
        every save for that interview from then on. The service resets the
        column to an empty object first.
        """
        interview = await _interview(db_session)
        db_session.add(InterviewSpec(interview_id=interview.id, json_data=None))
        await db_session.commit()

        result = await InterviewSpecService(db_session)._upsert_spec(
            interview.id, "questions", [{"question": "Q1"}]
        )

        assert result["questions"] == [{"question": "Q1"}]
        stored = (await db_session.execute(
            select(InterviewSpec).where(InterviewSpec.interview_id == interview.id)
        )).scalar_one()
        assert stored.json_data == {"questions": [{"question": "Q1"}]}


class TestResumeExtractionFailures:
    async def test_extraction_failure_rolls_back_and_reraises(
        self, db_session, tmp_path
    ):
        """A failure mid-extraction must not leave a half-written session.

        `extract_text_from_file_path` swallows parse errors itself, so this
        covers the harder case: something after the download raising, where
        the service has to roll back rather than commit a partial update.
        """
        interview = await _interview(db_session)
        resume = Resume(interview_id=interview.id, file_path="resumes/1/cv.pdf")
        db_session.add(resume)
        await db_session.commit()

        local_copy = tmp_path / "cv.pdf"
        local_copy.write_bytes(b"%PDF-1.4")

        with patch(
            "app.services.resume_extraction.MinIOClient.download_to_temp",
            return_value=str(local_copy),
        ), patch(
            "app.services.resume_extraction.extract_text_from_file_path",
            side_effect=RuntimeError("parser crashed"),
        ), patch.object(
            db_session, "rollback", wraps=db_session.rollback
        ) as rollback:
            with pytest.raises(RuntimeError, match="parser crashed"):
                await ResumeExtractionService(db_session).extract_and_save(resume.id)

        # Asserted on the call, not on raw_text: this failure lands before the
        # UPDATE, so raw_text stays None whether or not the service rolls back.
        # The rollback still matters — it is what stops a later failure from
        # committing a half-written session.
        rollback.assert_awaited_once()
        await db_session.refresh(resume)
        assert resume.raw_text is None
        # The temp file is still cleaned up on the failing path.
        assert not local_copy.exists()


class TestInterviewOrchestrationInputChecks:
    async def test_cannot_generate_without_resume_text(self, db_session, fake_llm_client):
        """A job description alone is not enough to build an interview from."""
        interview = await _interview(db_session)
        db_session.add_all([
            JobDescription(interview_id=interview.id, raw_text="Backend engineer."),
            Resume(interview_id=interview.id, file_path="resumes/1/cv.pdf", raw_text=None),
        ])
        await db_session.commit()

        service = InterviewOrchestrationService(db_session, fake_llm_client)
        assert await service.can_generate(interview.id) is False

    async def test_can_generate_with_both_inputs(self, db_session, fake_llm_client):
        interview = await _interview(db_session)
        db_session.add_all([
            JobDescription(interview_id=interview.id, raw_text="Backend engineer."),
            Resume(
                interview_id=interview.id, file_path="resumes/1/cv.pdf",
                raw_text="Five years of Python.",
            ),
        ])
        await db_session.commit()

        service = InterviewOrchestrationService(db_session, fake_llm_client)
        assert await service.can_generate(interview.id) is True

    async def test_pipeline_rejects_a_missing_interview(self, db_session, fake_llm_client):
        service = InterviewOrchestrationService(db_session, fake_llm_client)

        with pytest.raises(ValueError, match="Interview 99999 not found"):
            await service._run_pipeline(99999)

    async def test_pipeline_rejects_a_missing_job_description(
        self, db_session, fake_llm_client
    ):
        interview = await _interview(db_session)
        await db_session.commit()
        service = InterviewOrchestrationService(db_session, fake_llm_client)

        with pytest.raises(ValueError, match="No job description found"):
            await service._run_pipeline(interview.id)

    async def test_pipeline_rejects_a_missing_resume(self, db_session, fake_llm_client):
        interview = await _interview(db_session)
        db_session.add(
            JobDescription(interview_id=interview.id, raw_text="Backend engineer.")
        )
        await db_session.commit()
        service = InterviewOrchestrationService(db_session, fake_llm_client)

        with pytest.raises(ValueError, match="No resume found"):
            await service._run_pipeline(interview.id)
