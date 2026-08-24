"""One pass through the whole product, with the LLM and object storage stubbed.

Every module has its own tests; this one checks that they still work together:
interview creation, resume upload and text extraction, the five-agent question
pipeline, question delivery, answer submission, evaluation, completion
detection and the final report.
"""

from io import BytesIO
from unittest.mock import patch

from sqlalchemy import select

from app.db.models.interview import InterviewStatus
from app.db.models.interview_spec import InterviewSpec
from app.db.models.question import Question

JOB_DESCRIPTION = (
    "We are hiring a senior backend engineer with deep Python and FastAPI "
    "experience to own our interview platform."
)


def _resume_docx() -> bytes:
    from docx import Document

    document = Document()
    document.add_paragraph("Jane Doe — Senior Backend Engineer")
    document.add_paragraph("Python, FastAPI, PostgreSQL. 6 years of experience.")
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


class TestFullInterviewFlow:
    async def test_interview_runs_from_upload_to_final_report(self, test_client, db_session):
        # 1. Create the interview and store the job description.
        response = await test_client.post(
            "/api/v1/interviews", json={"job_description": JOB_DESCRIPTION}
        )
        assert response.status_code == 201
        interview_id = response.json()["id"]
        assert response.json()["status"] == "pending"

        # 2. Upload a resume. Only object storage is stubbed — the docx is
        #    parsed for real and the question pipeline runs on the fake model.
        with patch(
            "app.api.endpoints.resumes.upload_to_minio",
            return_value=(f"resumes/{interview_id}/jane.docx", "http://storage/jane.docx"),
        ):
            response = await test_client.post(
                "/api/v1/resumes",
                files={
                    "file": (
                        "jane.docx",
                        _resume_docx(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
                data={"interview_id": str(interview_id)},
            )

        assert response.status_code == 201
        upload = response.json()
        assert upload["generation_error"] is None
        assert upload["questions_generated"] == 2
        assert "Jane Doe" in upload["resume"]["raw_text"]

        # 3. Every pipeline stage persisted its analysis.
        spec = (await db_session.execute(
            select(InterviewSpec).where(InterviewSpec.interview_id == interview_id)
        )).scalar_one()
        assert set(spec.json_data) == {
            "jd_analysis", "resume_analysis", "gap_analysis", "final_spec", "questions",
        }

        questions = (await db_session.execute(
            select(Question)
            .where(Question.interview_id == interview_id)
            .order_by(Question.sequence)
        )).scalars().all()
        assert [q.sequence for q in questions] == [1, 2]

        # 4. Answer and evaluate the first question.
        response = await test_client.get(f"/api/v1/interviews/{interview_id}/question")
        assert response.status_code == 200
        first = response.json()
        assert first["question"] == "Explain async/await."

        response = await test_client.post(
            f"/api/v1/interviews/{interview_id}/answers",
            json={"question_id": first["question_id"], "answer": "It suspends on I/O."},
        )
        assert response.status_code == 201
        first_answer_id = response.json()["id"]

        response = await test_client.post(
            f"/api/v1/interviews/{interview_id}/answers/{first_answer_id}/evaluate"
        )
        assert response.status_code == 200
        assert response.json()["evaluation"]["technical_score"] == 8

        # 5. Halfway through there is no report yet.
        response = await test_client.get(f"/api/v1/interviews/{interview_id}/results")
        assert response.status_code == 200
        assert response.json()["overall_score"] is None
        assert response.json()["status"] == InterviewStatus.IN_PROGRESS

        # 6. Answer and evaluate the second question.
        response = await test_client.get(
            f"/api/v1/interviews/{interview_id}/question",
            params={"last_question_id": first["question_id"]},
        )
        assert response.status_code == 200
        second = response.json()
        assert second["question"] == "Describe a hard bug you fixed."

        response = await test_client.post(
            f"/api/v1/interviews/{interview_id}/answers",
            json={"question_id": second["question_id"], "answer": "A race in a job queue."},
        )
        second_answer_id = response.json()["id"]
        response = await test_client.post(
            f"/api/v1/interviews/{interview_id}/answers/{second_answer_id}/evaluate"
        )
        assert response.status_code == 200

        # 7. The interview is complete and the report is there.
        response = await test_client.get(f"/api/v1/interviews/{interview_id}/results")
        assert response.status_code == 200
        results = response.json()
        assert results["status"] == InterviewStatus.COMPLETED
        assert results["overall_score"] == 82
        assert results["technical_score"] == 8
        assert results["strengths"] == ["Clear communicator"]
        assert results["weaknesses"] == ["Limited Kubernetes exposure"]
        assert results["recommendations"] == ["Proceed to the system design round"]
        assert results["completed_at"] is not None

        # 8. There are no questions left to ask.
        response = await test_client.get(
            f"/api/v1/interviews/{interview_id}/question",
            params={"last_question_id": second["question_id"]},
        )
        assert response.status_code == 404

    async def test_results_recover_when_the_final_review_was_never_run(
        self, test_client, db_session, fake_llm_client
    ):
        """A GET rebuilds the report if evaluating the last answer failed to."""
        response = await test_client.post(
            "/api/v1/interviews", json={"job_description": JOB_DESCRIPTION}
        )
        interview_id = response.json()["id"]

        with patch(
            "app.api.endpoints.resumes.upload_to_minio",
            return_value=(f"resumes/{interview_id}/jane.docx", "http://storage/jane.docx"),
        ):
            await test_client.post(
                "/api/v1/resumes",
                files={"file": ("jane.docx", _resume_docx(), "application/octet-stream")},
                data={"interview_id": str(interview_id)},
            )

        questions = (await db_session.execute(
            select(Question).where(Question.interview_id == interview_id)
        )).scalars().all()

        # Answer and evaluate everything, but with finalization disabled — the
        # state an interview lands in when that call fails.
        with patch("app.api.endpoints.answers.InterviewFinalizationService") as disabled:
            disabled.return_value.finalize_if_complete.side_effect = RuntimeError("model down")
            for question in questions:
                response = await test_client.post(
                    f"/api/v1/interviews/{interview_id}/answers",
                    json={"question_id": question.id, "answer": "An answer worth scoring."},
                )
                assert response.status_code == 201
                answer_id = response.json()["id"]
                response = await test_client.post(
                    f"/api/v1/interviews/{interview_id}/answers/{answer_id}/evaluate"
                )
                assert response.status_code == 200

        response = await test_client.get(f"/api/v1/interviews/{interview_id}/results")

        assert response.status_code == 200
        assert response.json()["overall_score"] == 82
        assert response.json()["status"] == InterviewStatus.COMPLETED
