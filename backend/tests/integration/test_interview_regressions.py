"""Regression coverage for resume reuse, navigation and report completeness."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.db.models.answer import Answer
from app.db.models.evaluation import Evaluation
from app.db.models.interview import Interview, InterviewStatus
from app.db.models.interview_spec import InterviewSpec
from app.db.models.job_description import JobDescription
from app.db.models.question import Question
from app.db.models.resume import Resume
from app.services.interview_finalization import InterviewFinalizationService
from app.services.interview_orchestration import InterviewOrchestrationService


async def make_interview(db, question_count=2):
    interview = Interview(status=InterviewStatus.IN_PROGRESS)
    db.add(interview)
    await db.flush()
    questions = [
        Question(interview_id=interview.id, question=f"Question {i}?",
                 question_type="technical", difficulty="medium", sequence=i)
        for i in range(1, question_count + 1)
    ]
    db.add_all(questions)
    await db.commit()
    return interview, questions


async def add_answer(db, question, text, evaluated=True):
    answer = Answer(question_id=question.id, answer=text)
    db.add(answer)
    await db.flush()
    if evaluated:
        db.add(Evaluation(answer_id=answer.id, technical_score=8,
                          communication_score=9, feedback="Clear reasoning with concrete examples."))
    await db.commit()
    return answer


async def test_reused_resume_is_available_to_the_new_pipeline(
    test_client, db_session, fake_llm_client
):
    original, _ = await make_interview(db_session, 0)
    resume = Resume(interview_id=original.id, file_path="resumes/original/cv.pdf",
                    raw_text="Python developer with five years of experience.")
    db_session.add(resume)
    await db_session.commit()

    response = await test_client.post("/api/v1/interviews", json={
        "job_description": "Hiring an experienced Python developer.", "resume_id": resume.id,
    })
    assert response.status_code == 201
    interview_id = response.json()["id"]
    service = InterviewOrchestrationService(db_session, fake_llm_client)
    assert await service.can_generate(interview_id)
    assert await service.generate_questions(interview_id) == 2
    await db_session.refresh(resume)
    assert resume.interview_id == original.id


async def test_question_cursor_cannot_skip_using_another_interview(test_client, db_session):
    interview, _ = await make_interview(db_session)
    _, foreign_questions = await make_interview(db_session)
    response = await test_client.get(f"/api/v1/interviews/{interview.id}/question",
                                     params={"last_question_id": foreign_questions[0].id})
    assert response.status_code == 404


@pytest.mark.parametrize("text", [" " * 20, "     short     "])
async def test_job_description_is_validated_after_trimming(test_client, text):
    response = await test_client.post("/api/v1/interviews", json={"job_description": text})
    assert response.status_code == 422


async def test_upload_retry_uses_the_latest_resume(db_session, fake_llm_client):
    interview, _ = await make_interview(db_session, 0)
    db_session.add(JobDescription(interview_id=interview.id, raw_text="Python developer"))
    db_session.add(Resume(interview_id=interview.id, file_path="old.pdf", raw_text="Old resume"))
    await db_session.flush()
    db_session.add(Resume(interview_id=interview.id, file_path="new.pdf", raw_text="Updated resume"))
    await db_session.commit()

    service = InterviewOrchestrationService(db_session, fake_llm_client)
    assert await service.generate_questions(interview.id) == 2
    request = fake_llm_client.generate_completion.await_args_list[1].args[0]
    assert request.messages[-1]["content"] == "Updated resume"


async def test_report_waits_for_every_evaluation(test_client, db_session, fake_llm_client):
    interview, questions = await make_interview(db_session)
    await add_answer(db_session, questions[0], "First answer")
    final_answer = await add_answer(db_session, questions[1], "Last answer", evaluated=False)

    response = await test_client.get(f"/api/v1/interviews/{interview.id}/results")
    assert response.json()["overall_score"] is None
    assert response.json()["status"] == "in_progress"
    fake_llm_client.generate_completion.assert_not_awaited()

    response = await test_client.post(
        f"/api/v1/interviews/{interview.id}/answers/{final_answer.id}/evaluate"
    )
    assert response.status_code == 200
    response = await test_client.get(f"/api/v1/interviews/{interview.id}/results")
    assert response.json()["status"] == "completed"
    assert response.json()["overall_score"] == 82


async def test_report_uses_each_questions_latest_answer(db_session, fake_llm_client):
    interview, questions = await make_interview(db_session)
    await add_answer(db_session, questions[0], "Superseded answer")
    await add_answer(db_session, questions[0], "Revised answer")
    await add_answer(db_session, questions[1], "Second answer")

    await InterviewFinalizationService(db_session, fake_llm_client).finalize_if_complete(interview.id)
    prompt = fake_llm_client.generate_completion.await_args.args[0].messages[-1]["content"]
    assert "Revised answer" in prompt
    assert "Second answer" in prompt
    assert "Superseded answer" not in prompt


async def test_unevaluated_revision_does_not_use_its_old_evaluation(db_session, fake_llm_client):
    interview, questions = await make_interview(db_session, 1)
    await add_answer(db_session, questions[0], "Old answer")
    await add_answer(db_session, questions[0], "New answer", evaluated=False)
    result = await InterviewFinalizationService(db_session, fake_llm_client).finalize_if_complete(interview.id)
    assert result is None
    assert interview.status == InterviewStatus.IN_PROGRESS
    fake_llm_client.generate_completion.assert_not_awaited()


async def test_failed_review_does_not_mark_interview_complete(db_session, fake_llm_client):
    interview, questions = await make_interview(db_session, 1)
    await add_answer(db_session, questions[0], "My answer")
    fake_llm_client.generate_completion.side_effect = RuntimeError("Model unavailable")
    with pytest.raises(RuntimeError, match="Model unavailable"):
        await InterviewFinalizationService(db_session, fake_llm_client).finalize_if_complete(interview.id)
    await db_session.refresh(interview)
    assert interview.status == InterviewStatus.IN_PROGRESS
    assert (await db_session.execute(select(InterviewSpec))).scalar_one_or_none() is None


async def test_report_completion_time_is_not_the_interview_start(test_client, db_session):
    interview, questions = await make_interview(db_session, 1)
    interview.created_at = datetime.now(timezone.utc) - timedelta(days=1)
    await add_answer(db_session, questions[0], "An evaluated answer")

    response = await test_client.get(f"/api/v1/interviews/{interview.id}/results")
    completed_at = datetime.fromisoformat(response.json()["completed_at"])
    assert completed_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc) - timedelta(minutes=1)


async def test_retrying_evaluation_returns_the_saved_result(test_client, db_session, fake_llm_client):
    interview, questions = await make_interview(db_session)
    answer = await add_answer(db_session, questions[0], "An evaluated answer")
    response = await test_client.post(
        f"/api/v1/interviews/{interview.id}/answers/{answer.id}/evaluate"
    )
    assert response.status_code == 200
    assert response.json()["evaluation"]["technical_score"] == 8
    fake_llm_client.generate_completion.assert_not_awaited()


@pytest.mark.parametrize("status", [InterviewStatus.COMPLETED, InterviewStatus.ARCHIVED])
async def test_closed_interviews_reject_new_answers_and_resumes(test_client, db_session, status):
    interview, questions = await make_interview(db_session, 1)
    interview.status = status
    await db_session.commit()
    response = await test_client.post(f"/api/v1/interviews/{interview.id}/answers", json={
        "question_id": questions[0].id, "answer": "A new answer",
    })
    assert response.status_code == 409
    response = await test_client.post("/api/v1/resumes", data={"interview_id": interview.id},
                                     files={"file": ("resume.pdf", b"invalid PDF", "application/pdf")})
    assert response.status_code == 409
    assert (await db_session.execute(select(Answer))).scalar_one_or_none() is None
    assert (await db_session.execute(select(Resume))).scalar_one_or_none() is None


async def test_unreadable_resume_is_rejected_before_storage(test_client, db_session, fake_llm_client):
    interview, _ = await make_interview(db_session, 0)
    with patch("app.api.endpoints.resumes.upload_to_minio") as upload:
        response = await test_client.post("/api/v1/resumes", data={"interview_id": interview.id},
                                         files={"file": ("resume.pdf", b"invalid PDF", "application/pdf")})
    assert response.status_code == 422
    assert "No readable text" in response.json()["detail"]
    upload.assert_not_called()
    fake_llm_client.generate_completion.assert_not_awaited()
    assert (await db_session.execute(select(Resume))).scalar_one_or_none() is None
