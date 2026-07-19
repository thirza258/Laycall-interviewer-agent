from pydantic import BaseModel, Field

class JobDescriptionAnalysis(BaseModel):
    job_title: str = Field(..., description="Extracted job title")
    company: str = Field(..., description="Extracted company name")
    required_skills: list[str] = Field(default=[], description="Must-have technical/soft skills")
    preferred_skills: list[str] = Field(default=[], description="Nice-to-have skills")
    responsibilities: list[str] = Field(default=[], description="Key role responsibilities")

class ResumeAnalysis(BaseModel):
    education: list[str] = Field(default=[], description="Degrees, institutions, graduation years")
    skills: list[str] = Field(default=[], description="Technical, tools, and soft skills")
    projects: list[str] = Field(default=[], description="Notable projects with brief context")
    experience: list[str] = Field(default=[], description="Work history with roles and achievements")
    
class GapAnalysis(BaseModel):
    matched_skills: list[str] = Field(
        default=[], 
        description="Skills present in both the resume and job description"
    )
    missing_skills: list[str] = Field(
        default=[], 
        description="Required or preferred skills from JD that are absent in the resume"
    )
    strengths: list[str] = Field(
        default=[], 
        description="Areas where candidate exceeds requirements or demonstrates strong expertise"
    )
    focus_areas: list[str] = Field(
        default=[], 
        description="Topics or skills to probe during the interview due to gaps or ambiguity"
    )
    
class FinalInterviewSpec(BaseModel):
    target_role: str = Field(..., description="Target job title/role")
    difficulty: str = Field(..., description="Interview difficulty level (e.g., junior, mid, senior, expert)")
    required_skills: list[str] = Field(default=[], description="Core skills to assess")
    focus_areas: list[str] = Field(default=[], description="Areas to focus on during interview")
    candidate_strengths: list[str] = Field(default=[], description="Candidate's strong points")
    candidate_gaps: list[str] = Field(default=[], description="Areas where candidate lacks experience")

class InterviewQuestion(BaseModel):
    question: str = Field(..., description="The interview question text")
    type: str = Field(..., description="Category (e.g., technical, behavioral, system_design, cultural_fit)")
    difficulty: str = Field(..., description="Difficulty (easy, medium, hard)")

class GeneratedQuestions(BaseModel):
    # OpenAI's json_object mode requires a top-level object, so we wrap the array
    questions: list[InterviewQuestion] = Field(..., description="List of generated interview questions")
    
class AnswerEvaluation(BaseModel):
    technical_score: int = Field(
        ..., 
        ge=0, le=10, 
        description="Score 0-10 for technical accuracy and correctness"
    )
    communication_score: int = Field(
        ..., 
        ge=0, le=10, 
        description="Score 0-10 for clarity, structure, and articulation"
    )
    feedback: str = Field(
        ..., 
        min_length=20,
        description="Constructive, actionable feedback for the candidate"
    )
    
class FinalAssessment(BaseModel):
    overall_score: int = Field(
        ..., 
        ge=0, le=100, 
        description="Weighted overall score (0-100)"
    )
    technical_score: int = Field(
        ..., 
        ge=0, le=100, 
        description="Aggregated technical competency score"
    )
    communication_score: int = Field(
        ..., 
        ge=0, le=100, 
        description="Aggregated communication effectiveness score"
    )
    strengths: list[str] = Field(
        default=[], 
        description="Key candidate strengths observed during interview"
    )
    weaknesses: list[str] = Field(
        default=[], 
        description="Areas where candidate struggled or showed gaps"
    )
    recommendations: list[str] = Field(
        default=[], 
        description="Actionable next steps or hiring recommendations"
    )