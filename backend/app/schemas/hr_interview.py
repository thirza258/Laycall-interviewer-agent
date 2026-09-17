from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Skill = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
FeedbackText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
MAX_TURNS = 30


class CandidateProfile(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)] = "Alex Morgan"
    role: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
    level: Literal["junior", "mid", "senior"] = "mid"
    skills: list[Skill] = Field(min_length=1, max_length=12)
    background: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] = ""

    @field_validator("skills")
    @classmethod
    def unique_skills(cls, skills: list[str]) -> list[str]:
        seen = set()
        unique = []
        for skill in skills:
            if skill.casefold() not in seen:
                seen.add(skill.casefold())
                unique.append(skill)
        return unique


class HrInterviewCreate(BaseModel):
    # A client may reuse this ID after a lost creation response.
    id: UUID = Field(default_factory=uuid4)
    profile: CandidateProfile


class HrQuestionCreate(BaseModel):
    request_id: UUID
    expected_turn_count: int = Field(ge=0, le=MAX_TURNS)
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class CandidateReply(BaseModel):
    answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=6000)]


class HrTurn(BaseModel):
    request_id: UUID
    question: str
    answer: str
    created_at: datetime


class InterviewerFeedback(BaseModel):
    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=20, max_length=2500)]
    question_quality: int = Field(ge=0, le=10)
    follow_up_quality: int = Field(ge=0, le=10)
    strengths: list[FeedbackText] = Field(min_length=1, max_length=5)
    improvements: list[FeedbackText] = Field(min_length=1, max_length=5)
    covered_skills: list[Skill] = Field(max_length=12)
    suggested_questions: list[FeedbackText] = Field(min_length=1, max_length=5)


class HrInterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile: CandidateProfile
    status: Literal["in_progress", "completed"]
    turns: list[HrTurn]
    feedback: InterviewerFeedback | None = None
    created_at: datetime
    max_turns: int = MAX_TURNS
