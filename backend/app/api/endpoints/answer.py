import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.db.session import get_db
from app.db.models.interview import Interview
from app.db.models.question import Question
from app.db.models.answer import Answer
from app.schemas.answer import AnswerCreate, AnswerResponse

from app.llm.client import OpenRouterClient, get_openrouter_client
from app.agents.answer_evaluator import AnswerEvaluationAgent
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/api/v1/interviews", tags=["answers"])
logger = logging.getLogger(__name__)

@router.post(
    "/{interview_id}/answers",
    response_model=AnswerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit candidate answer",
    description="Records a candidate's answer to a specific interview question."
)
async def submit_answer(
    interview_id: int,
    payload: AnswerCreate,
    db: AsyncSession = Depends(get_db)
) -> AnswerResponse:
    """
    Validates that the interview and question exist, ensures the question
    belongs to the specified interview, and persists the candidate's answer.
    """
    interview_stmt = select(Interview).where(Interview.id == interview_id)
    interview = (await db.execute(interview_stmt)).scalar_one_or_none()
    
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    question_stmt = select(Question).where(
        Question.id == payload.question_id,
        Question.interview_id == interview_id
    )
    question = (await db.execute(question_stmt)).scalar_one_or_none()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Question not found or does not belong to this interview"
        )

    new_answer = Answer(
        question_id=payload.question_id,
        answer=payload.answer.strip()
    )
    db.add(new_answer)
    await db.commit()
    await db.refresh(new_answer)
    
    logger.info(f"Answer submitted: id={new_answer.id}, question={payload.question_id}")
    return AnswerResponse.model_validate(new_answer)

@router.post(
    "/{interview_id}/answers/{answer_id}/evaluate",
    response_model=dict,
    summary="Evaluate candidate answer",
    description="Triggers LLM-based evaluation of a submitted answer."
)
async def evaluate_answer(
    interview_id: int,
    answer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    llm_client: OpenRouterClient = Depends(get_openrouter_client)
):
    """
    Fetches the answer + associated question, runs evaluation agent,
    and persists results to the evaluations table.
    """
    from sqlalchemy import select
    from app.db.models.answer import Answer
    from app.db.models.question import Question
    from app.db.models.job_description import JobDescription
    
    result = await db.execute(
        select(Answer)
        .join(Question)
        .join(JobDescription)
        .where(
            Answer.id == answer_id,
            Question.interview_id == interview_id
        )
    )
    answer = result.scalar_one_or_none()
    
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")

    agent = AnswerEvaluationAgent(llm_client)
    evaluation = await agent.evaluate(
        question_text=answer.question.question,
        answer_text=answer.answer,
        context={
            "job_description": answer.question.interview.job_descriptions[0].raw_text[:500] 
            if answer.question.interview.job_descriptions else None
        }
    )

    eval_service = EvaluationService(db)
    saved_eval = await eval_service.save_evaluation(str(answer_id), evaluation)

    return {
        "status": "success",
        "evaluation": {
            "technical_score": saved_eval.technical_score,
            "communication_score": saved_eval.communication_score,
            "feedback": saved_eval.feedback
        }
    }