import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import  select
from app.db.session import get_db
from app.db.models.interview import Interview, InterviewStatus
from app.db.models.job_description import JobDescription
from app.db.models.resume import Resume
from app.schemas.interview import InterviewCreate, InterviewResponse, JobDescriptionResponse
from app.db.models.question import Question
from app.schemas.question import QuestionResponse
from app.schemas.interview_result import InterviewResultsResponse
from app.db.models.interview_spec import InterviewSpec

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
    description="Retrieves the next question in the interview sequence. Use ?last_question_id=UUID to get the following one."
)
async def get_next_question(
    interview_id: int,
    last_question_id: int | None = Query(None, description="ID of the last answered question to fetch the next one"),
    db: AsyncSession = Depends(get_db)
) -> QuestionResponse:
    # 1. Verify interview exists
    interview = (await db.execute(select(Interview).where(Interview.id == interview_id))).scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # 2. Base query for questions
    stmt = select(Question).where(Question.interview_id == interview_id).order_by(Question.sequence)

    # 3. If last_question_id provided, fetch sequence > that question's sequence
    if last_question_id:
        last_q = (await db.execute(select(Question).where(Question.id == last_question_id))).scalar_one_or_none()
        if not last_q:
            raise HTTPException(status_code=404, detail="Last question ID not found")
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
    db: AsyncSession = Depends(get_db)
) -> InterviewResultsResponse:
    """
    Fetches the final assessment from interview_specs.
    Returns 404 if interview not found or not completed.
    Returns partial data if assessment not yet generated.
    """
    # 1. Verify interview exists and is completed
    interview = (await db.execute(
        select(Interview).where(Interview.id == interview_id)
    )).scalar_one_or_none()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    if interview.status != InterviewStatus.COMPLETED:
        pass  # Optional: raise HTTPException(400, detail="Interview not yet completed")

    spec = (await db.execute(
        select(InterviewSpec).where(InterviewSpec.interview_id == interview_id)
    )).scalar_one_or_none()
    
    assessment = spec.json_data.get("final_assessment") if spec and spec.json_data else None

    response_data = {
        "interview_id": interview.id,
        "status": interview.status,
        "completed_at": interview.created_at if interview.status == InterviewStatus.COMPLETED else None,
        **(assessment or {})  # Spread assessment fields if available
    }
    
    for key in ["strengths", "weaknesses", "recommendations"]:
        if key not in response_data:
            response_data[key] = []

    return InterviewResultsResponse.model_validate(response_data)
