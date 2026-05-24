from pydantic import BaseModel, Field
from typing import Optional


class QuestionRequest(BaseModel):

    question: str

    pdf_name: Optional[str] = None


class PdfContentRequest(BaseModel):
    """Scope content from uploaded PDF(s). pdf_name optional; specification optional (whole PDF if empty)."""

    pdf_name: Optional[str] = None
    specification: Optional[str] = None


class QuizRequest(PdfContentRequest):
    num_questions: int = Field(default=5, ge=3, le=20)


class FlashcardRequest(PdfContentRequest):
    num_cards: int = Field(default=5, ge=3, le=20)


class NotesRequest(PdfContentRequest):
    pass


class RoadmapRequest(BaseModel):

    topic: str


class StudyPlanRequest(BaseModel):

    goal: str

    current_level: str = "Intermediate"

    weeks_available: int = 4


class WeakAreaPlanRequest(BaseModel):

    weak_topics: list[str]

    role: str = "Software Engineer"


class CareerRoadmapRequest(BaseModel):

    role: str

    current_skills: list[str] = []

    experience: str = "Intermediate"


class PostInterviewPlanRequest(BaseModel):

    role: str

    technical_score: float

    communication_score: float

    confidence_score: float

    weak_topics: Optional[list[str]] = None