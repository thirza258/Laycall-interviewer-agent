import pytest
from sqlalchemy import select

from app.db.models.interview import Interview, InterviewStatus
from app.db.models.resume import Resume
from app.db.models.job_description import JobDescription
from app.db.models.interview_spec import InterviewSpec
from app.db.models.question import Question
from app.db.models.answer import Answer
from app.db.models.evaluation import Evaluation


class TestInterviewModel:
    @pytest.mark.asyncio
    async def test_create_interview(self, db_session):
        interview = Interview(status=InterviewStatus.PENDING)
        db_session.add(interview)
        await db_session.commit()
        await db_session.refresh(interview)

        assert interview.id is not None
        assert interview.status == InterviewStatus.PENDING
        assert interview.created_at is not None

    @pytest.mark.asyncio
    async def test_interview_default_status(self, db_session):
        interview = Interview()
        db_session.add(interview)
        await db_session.commit()

        assert interview.status == InterviewStatus.PENDING

    @pytest.mark.asyncio
    async def test_mark_completed(self, db_session):
        interview = Interview(status=InterviewStatus.IN_PROGRESS)
        db_session.add(interview)
        await db_session.commit()

        interview.mark_completed()
        await db_session.commit()

        assert interview.status == InterviewStatus.COMPLETED
        assert interview.is_completed() is True

    @pytest.mark.asyncio
    async def test_is_completed_returns_false_for_pending(self, db_session):
        interview = Interview(status=InterviewStatus.PENDING)
        assert interview.is_completed() is False


class TestResumeModel:
    @pytest.mark.asyncio
    async def test_create_resume(self, db_session):
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        resume = Resume(
            interview_id=interview.id,
            file_path="resumes/1/abc.pdf",
            raw_text="Resume text content",
        )
        db_session.add(resume)
        await db_session.commit()
        await db_session.refresh(resume)

        assert resume.id is not None
        assert resume.interview_id == interview.id
        assert resume.file_path == "resumes/1/abc.pdf"
        assert resume.raw_text == "Resume text content"

    @pytest.mark.asyncio
    async def test_resume_cascade_delete(self, db_session):
        """Deleting an interview should cascade-delete its resumes."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        resume = Resume(interview_id=interview.id, file_path="path/doc.pdf")
        db_session.add(resume)
        await db_session.commit()

        await db_session.delete(interview)
        await db_session.commit()

        result = await db_session.execute(select(Resume).where(Resume.id == resume.id))
        assert result.scalar_one_or_none() is None


class TestJobDescriptionModel:
    @pytest.mark.asyncio
    async def test_create_job_description(self, db_session):
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        jd = JobDescription(interview_id=interview.id, raw_text="We need a Python developer")
        db_session.add(jd)
        await db_session.commit()
        await db_session.refresh(jd)

        assert jd.id is not None
        assert jd.raw_text == "We need a Python developer"
        assert jd.created_at is not None


class TestInterviewSpecModel:
    @pytest.mark.asyncio
    async def test_create_spec_with_jsonb(self, db_session):
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        spec = InterviewSpec(
            interview_id=interview.id,
            json_data={"jd_analysis": {"job_title": "Engineer"}, "questions": []},
        )
        db_session.add(spec)
        await db_session.commit()
        await db_session.refresh(spec)

        assert spec.json_data["jd_analysis"]["job_title"] == "Engineer"
        assert spec.json_data["questions"] == []

    @pytest.mark.asyncio
    async def test_unique_interview_id(self, db_session):
        """An interview should only have one spec (unique constraint)."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        spec1 = InterviewSpec(interview_id=interview.id, json_data={})
        db_session.add(spec1)
        await db_session.commit()

        spec2 = InterviewSpec(interview_id=interview.id, json_data={})
        db_session.add(spec2)

        with pytest.raises(Exception):
            await db_session.commit()
        await db_session.rollback()


class TestQuestionModel:
    @pytest.mark.asyncio
    async def test_create_question(self, db_session):
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        question = Question(
            interview_id=interview.id,
            question="What is Python?",
            question_type="technical",
            difficulty="easy",
            sequence=1,
        )
        db_session.add(question)
        await db_session.commit()
        await db_session.refresh(question)

        assert question.id is not None
        assert question.question_type == "technical"
        assert question.difficulty == "easy"
        assert question.sequence == 1

    @pytest.mark.asyncio
    async def test_questions_ordered_by_sequence(self, db_session):
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        q1 = Question(interview_id=interview.id, question="Q1", question_type="tech", difficulty="easy", sequence=2)
        q2 = Question(interview_id=interview.id, question="Q2", question_type="tech", difficulty="easy", sequence=1)
        db_session.add_all([q1, q2])
        await db_session.commit()

        result = await db_session.execute(
            select(Question).where(Question.interview_id == interview.id).order_by(Question.sequence)
        )
        questions = result.scalars().all()
        assert questions[0].sequence == 1
        assert questions[1].sequence == 2


class TestAnswerModel:
    @pytest.mark.asyncio
    async def test_create_answer(self, db_session):
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        question = Question(
            interview_id=interview.id, question="Q?", question_type="tech",
            difficulty="easy", sequence=1,
        )
        db_session.add(question)
        await db_session.flush()

        answer = Answer(question_id=question.id, answer="This is my answer.")
        db_session.add(answer)
        await db_session.commit()
        await db_session.refresh(answer)

        assert answer.id is not None
        assert answer.answer == "This is my answer."
        assert answer.created_at is not None


class TestEvaluationModel:
    @pytest.mark.asyncio
    async def test_create_evaluation(self, db_session):
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        question = Question(
            interview_id=interview.id, question="Q?", question_type="tech",
            difficulty="easy", sequence=1,
        )
        db_session.add(question)
        await db_session.flush()

        answer = Answer(question_id=question.id, answer="My answer.")
        db_session.add(answer)
        await db_session.flush()

        evaluation = Evaluation(
            answer_id=answer.id,
            technical_score=8,
            communication_score=7,
            feedback="Good job explaining your reasoning.",
        )
        db_session.add(evaluation)
        await db_session.commit()
        await db_session.refresh(evaluation)

        assert evaluation.id is not None
        assert evaluation.technical_score == 8
        assert evaluation.communication_score == 7

    @pytest.mark.asyncio
    async def test_score_constraints(self, db_session):
        """Scores must be between 0 and 10 (DB constraint)."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        question = Question(
            interview_id=interview.id, question="Q?", question_type="tech",
            difficulty="easy", sequence=1,
        )
        db_session.add(question)
        await db_session.flush()

        answer = Answer(question_id=question.id, answer="A.")
        db_session.add(answer)
        await db_session.flush()

        evaluation = Evaluation(
            answer_id=answer.id,
            technical_score=11,
            communication_score=0,
            feedback="Invalid score.",
        )
        db_session.add(evaluation)

        with pytest.raises(Exception):
            await db_session.commit()
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_unique_answer_id(self, db_session):
        """An answer should only have one evaluation (unique constraint)."""
        interview = Interview()
        db_session.add(interview)
        await db_session.flush()

        question = Question(
            interview_id=interview.id, question="Q?", question_type="tech",
            difficulty="easy", sequence=1,
        )
        db_session.add(question)
        await db_session.flush()

        answer = Answer(question_id=question.id, answer="A.")
        db_session.add(answer)
        await db_session.flush()

        eval1 = Evaluation(answer_id=answer.id, technical_score=5, communication_score=5, feedback="First.")
        db_session.add(eval1)
        await db_session.commit()

        eval2 = Evaluation(answer_id=answer.id, technical_score=8, communication_score=8, feedback="Second.")
        db_session.add(eval2)

        with pytest.raises(Exception):
            await db_session.commit()
        await db_session.rollback()
