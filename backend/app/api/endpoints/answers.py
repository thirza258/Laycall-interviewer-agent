import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.db.session import get_db
from app.db.models.interview import Interview, InterviewStatus
from app.db.models.evaluation import Evaluation
from app.db.models.question import Question
from app.db.models.answer import Answer
from app.schemas.answer import AnswerCreate, AnswerResponse

from app.llm.client import OpenRouterClient, get_openrouter_client
from app.llm.exceptions import (
    OpenRouterAPIError,
    OpenRouterError,
    OpenRouterRateLimitError,
    OpenRouterTimeoutError,
)
from app.agents.answer_evaluator import AnswerEvaluationAgent
from app.services.evaluation_service import EvaluationService
from app.services.interview_finalization import InterviewFinalizationService

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

    if interview.status in (InterviewStatus.COMPLETED, InterviewStatus.ARCHIVED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This interview is already closed")

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
        answer=payload.answer,  # AnswerCreate strips and rejects blank input
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
    answer_id: int,
    db: AsyncSession = Depends(get_db),
    llm_client: OpenRouterClient = Depends(get_openrouter_client)
):
    """
    Fetches the answer + associated question, runs evaluation agent,
    and persists results to the evaluations table.
    """
    result = await db.execute(
        select(Answer)
        .join(Answer.question)
        .options(
            joinedload(Answer.evaluation),
            joinedload(Answer.question)
            .joinedload(Question.interview)
            .joinedload(Interview.job_descriptions)
        )
        .where(
            Answer.id == answer_id,
            Question.interview_id == interview_id
        )
    )
    # unique() is mandatory here: joined eager loading against a collection
    # (Interview.job_descriptions) makes SQLAlchemy refuse to return rows
    # otherwise, which turned every evaluation into a 500.
    answer = result.unique().scalar_one_or_none()

    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")

    if answer.evaluation is not None:
        return await _evaluation_response(interview_id, answer.evaluation, db, llm_client)

    agent = AnswerEvaluationAgent(llm_client)
    try:
        evaluation = await agent.evaluate(
            question_text=answer.question.question,
            answer_text=answer.answer,
            context={
                "job_description": answer.question.interview.job_descriptions[0].raw_text[:500]
                if answer.question.interview.job_descriptions else None
            }
        )
    except OpenRouterRateLimitError as e:
        logger.warning(f"Rate limited while evaluating answer {answer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The model is rate limited right now. Please wait a moment and try again."
        )
    except (OpenRouterTimeoutError, OpenRouterAPIError) as e:
        logger.error(f"Could not reach the model while evaluating answer {answer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not reach the evaluation model. Your answer was saved — please try again."
        )
    except OpenRouterError as e:
        # Truncated, empty or malformed completion: the call reached the model
        # but the answer is unusable.
        logger.error(f"Unusable model response while evaluating answer {answer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The evaluation model returned an unusable response. Your answer was saved — please try again."
        )
    except Exception as e:
        logger.error(f"LLM evaluation failed for answer {answer_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Evaluation service temporarily unavailable"
        )

    eval_service = EvaluationService(db)
    try:
        saved_eval = await eval_service.save_evaluation(answer_id, evaluation)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

    return await _evaluation_response(interview_id, saved_eval, db, llm_client)


async def _evaluation_response(
    interview_id: int,
    saved_eval: Evaluation,
    db: AsyncSession,
    llm_client: OpenRouterClient,
) -> dict:
    # With every question answered and evaluated, build the final report.
    # Best effort: the evaluation is already saved, and GET /results retries
    # this, so a failure here must not turn a good evaluation into an error.
    try:
        await InterviewFinalizationService(db, llm_client).finalize_if_complete(interview_id)
    except Exception as e:
        logger.error(
            f"Final assessment failed for interview {interview_id}: {e}",
            exc_info=True
        )

    return {
        "status": "success",
        "evaluation": {
            "technical_score": saved_eval.technical_score,
            "communication_score": saved_eval.communication_score,
            "feedback": saved_eval.feedback
        }
    }
