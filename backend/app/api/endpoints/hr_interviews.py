from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.hr_interview import HrInterview
from app.db.session import get_db
from app.llm.client import OpenRouterClient, get_openrouter_client
from app.schemas.hr_interview import HrInterviewCreate, HrInterviewResponse, HrQuestionCreate
from app.services.hr_interview_service import HrInterviewService

router = APIRouter(prefix="/api/v1/hr-interviews", tags=["HR practice"])


@router.post("", response_model=HrInterviewResponse, status_code=201)
async def create_hr_interview(payload: HrInterviewCreate, db: AsyncSession = Depends(get_db)):
    profile = payload.profile.model_dump()
    existing = await db.get(HrInterview, str(payload.id))
    if existing is None:
        interview = HrInterview(id=str(payload.id), profile=profile)
        db.add(interview)
        try:
            await db.commit()
        except IntegrityError:
            # A retried creation may race the original request.
            await db.rollback()
            existing = await db.get(HrInterview, str(payload.id))
            if existing is None:
                raise
        else:
            await db.refresh(interview)
            return interview
    if existing.profile != profile:
        raise HTTPException(409, "This session ID already belongs to a different candidate profile.")
    return existing


@router.get("/{session_id}", response_model=HrInterviewResponse)
async def get_hr_interview(session_id: UUID, db: AsyncSession = Depends(get_db)):
    interview = await db.get(HrInterview, str(session_id))
    if interview is None:
        raise HTTPException(404, "HR interview not found")
    return interview


@router.post("/{session_id}/questions", response_model=HrInterviewResponse)
async def ask_candidate(
    session_id: UUID, payload: HrQuestionCreate,
    db: AsyncSession = Depends(get_db), llm: OpenRouterClient = Depends(get_openrouter_client),
):
    return await HrInterviewService(db, llm).ask(str(session_id), payload)


@router.post("/{session_id}/finish", response_model=HrInterviewResponse)
async def finish_hr_interview(
    session_id: UUID, db: AsyncSession = Depends(get_db),
    llm: OpenRouterClient = Depends(get_openrouter_client),
):
    return await HrInterviewService(db, llm).finish(str(session_id))
