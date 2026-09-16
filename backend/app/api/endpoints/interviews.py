import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import  select
from app.db.session import get_db
from app.db.models.interview import Interview
from app.db.models.job_description import JobDescription
from app.db.models.resume import Resume
from app.schemas.interview import InterviewCreate, InterviewResponse, JobDescriptionResponse
from app.db.models.question import Question
from app.schemas.question import QuestionResponse
from app.schemas.interview_result import InterviewResultsResponse
from app.db.models.interview_spec import InterviewSpec
from app.llm.client import OpenRouterClient, get_openrouter_client
from app.services.interview_orchestration import InterviewOrchestrationService
from app.services.interview_finalization import InterviewFinalizationService

router = APIRouter(prefix="/api/v1/interviews", tags=["interviews"])
logger = logging.getLogger(__name__)

@router.post(
    "",
    response_model=InterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new interview session",
    description="Starts a new interview, stores the job description, and links to a resume."
)
async def create_interview(
    payload: InterviewCreate,
    db: AsyncSession = Depends(get_db)
) -> InterviewResponse:
    """
    Creates an Interview and associated JobDescription in a single transaction.
    """
    resume = None
    if payload.resume_id is not None:
        resume_result = await db.execute(select(Resume).where(Resume.id == payload.resume_id))
        resume = resume_result.scalar_one_or_none()
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resume with ID {payload.resume_id} not found"
            )

    new_interview = Interview(status="pending")
    db.add(new_interview)
    await db.flush()  # Assign ID without committing yet

    new_job_desc = JobDescription(
        interview_id=new_interview.id,
        raw_text=payload.job_description
    )
    db.add(new_job_desc)

    if resume is not None:
        # Reuse the stored file and text without moving it out of the original
        # interview. The generation pipeline looks up resumes by interview_id.
        db.add(Resume(
            interview_id=new_interview.id,
            file_path=resume.file_path,
            raw_text=resume.raw_text,
        ))

    # 4. Commit transaction
    await db.commit()
    await db.refresh(new_interview)
    await db.refresh(new_job_desc)

    logger.info(f"Interview {new_interview.id} created with job description {new_job_desc.id}")

    # 5. Return formatted response
    return InterviewResponse(
        id=new_interview.id,
        status=new_interview.status,
        created_at=new_interview.created_at,
        job_description=JobDescriptionResponse.model_validate(new_job_desc)
    )
    
@router.get(
    "/{interview_id}/question",
    response_model=QuestionResponse,
    summary="Get next interview question",
    description="Retrieves the next question in the interview sequence. Use ?last_question_id=ID to get the following one."
)
async def get_next_question(
    interview_id: int,
    last_question_id: int | None = Query(None, gt=0, description="ID of the last answered question to fetch the next one"),
    db: AsyncSession = Depends(get_db),
    llm_client: OpenRouterClient = Depends(get_openrouter_client)
) -> QuestionResponse:
    # 1. Verify interview exists
    interview = (await db.execute(select(Interview).where(Interview.id == interview_id))).scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    last_q = None
    if last_question_id is not None:
        last_q = (await db.execute(select(Question).where(
            Question.id == last_question_id,
            Question.interview_id == interview_id,
        ))).scalar_one_or_none()
        if last_q is None:
            raise HTTPException(status_code=404, detail="Last question ID not found in this interview")

    # 2. If generation failed during upload the interview has no questions at
    #    all. Retry it here so a transient LLM outage does not strand the
    #    interview permanently. Interviews without a resume or job description
    #    have nothing to generate from and keep the plain "no questions" answer.
    orchestration = InterviewOrchestrationService(db, llm_client)
    if (
        await orchestration.count_questions(interview_id) == 0
        and await orchestration.can_generate(interview_id)
    ):
        # Never queue behind an in-flight run: waiting would burn the caller's
        # connection and leave the browser hanging on a request it cannot use.
        if orchestration.is_generating(interview_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Your interview questions are still being prepared. Please try again in a few seconds."
            )

        logger.info(f"Interview {interview_id} has no questions; retrying generation")
        try:
            await orchestration.generate_questions(interview_id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except (asyncio.TimeoutError, TimeoutError):
            logger.error(f"Question generation timed out for interview {interview_id}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Preparing your questions is taking longer than expected. Please try again."
            )
        except Exception as e:
            logger.error(
                f"Question generation retry failed for interview {interview_id}: {e}",
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not reach the interview model. Please try again in a moment."
            )

    # 3. Base query for questions
    stmt = select(Question).where(Question.interview_id == interview_id).order_by(Question.sequence)

    # 4. If last_question_id provided, fetch sequence > that question's sequence
    if last_q is not None:
        stmt = stmt.where(Question.sequence > last_q.sequence)

    result = await db.execute(stmt.limit(1))
    next_question = result.scalar_one_or_none()

    if not next_question:
        raise HTTPException(status_code=404, detail="No more questions available for this interview")

    return QuestionResponse(
        question_id=next_question.id,
        question=next_question.question
    )
    
@router.get(
    "/{interview_id}/results",
    response_model=InterviewResultsResponse,
    summary="Get final interview report",
    description="Retrieves the completed interview assessment with scores and recommendations."
)
async def get_interview_results(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    llm_client: OpenRouterClient = Depends(get_openrouter_client)
) -> InterviewResultsResponse:
    """
    Fetches the final assessment from interview_specs.
    Returns 404 if the interview does not exist.
    Returns partial data while the interview is still in progress.
    """
    interview = (await db.execute(
        select(Interview).where(Interview.id == interview_id)
    )).scalar_one_or_none()

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    spec = (await db.execute(
        select(InterviewSpec).where(InterviewSpec.interview_id == interview_id)
    )).scalar_one_or_none()

    assessment = spec.json_data.get("final_assessment") if spec and spec.json_data else None

    if assessment is None:
        # The assessment is normally written when the last answer is
        # evaluated. If that call failed, build it here instead of leaving a
        # finished interview without a report — the same retry-on-read the
        # question pipeline does above. Returns None while questions remain.
        try:
            assessment = await InterviewFinalizationService(
                db, llm_client
            ).finalize_if_complete(interview_id)
        except Exception as e:
            logger.error(
                f"Final assessment failed for interview {interview_id}: {e}",
                exc_info=True
            )

    response_data = {
        "interview_id": interview.id,
        "status": interview.status,
        "completed_at": None,
        **(assessment or {})  # Spread assessment fields if available
    }
    
    for key in ["strengths", "weaknesses", "recommendations"]:
        if key not in response_data:
            response_data[key] = []

    return InterviewResultsResponse.model_validate(response_data)
