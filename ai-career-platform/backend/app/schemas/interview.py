from pydantic import BaseModel, Field
from typing import Optional, List


# =========================
# START INTERVIEW REQUEST
# =========================

class StartInterviewRequest(BaseModel):

    role: str

    num_questions: int = Field(default=7, ge=1, le=20)

    company: Optional[str] = None

    interview_type: Optional[str] = None


# =========================
# START INTERVIEW RESPONSE
# =========================

class StartInterviewResponse(BaseModel):

    interview_id: int

    question_id: int

    question: str

    question_number: int

    total_questions: int


# =========================
# SUBMIT ANSWER REQUEST
# =========================

class SpeechMetricsInput(BaseModel):
    duration_sec: Optional[float] = None
    pause_count: int = 0
    answer_mode: str = "text"


class SubmitAnswerRequest(BaseModel):

    interview_id: int

    question_id: int

    answer_text: str

    speech_metrics: Optional[SpeechMetricsInput] = None


class NextQuestionRequest(BaseModel):

    interview_id: int


# =========================
# EVALUATION RESPONSE
# =========================

class EvaluationResponse(BaseModel):

    technical_accuracy: float

    communication: float

    confidence: float

    grammar: float

    similarity_score: float

    feedback: List[str]

    correct_answer_hint: Optional[str] = None


# =========================
# ANSWER SUBMISSION RESPONSE
# =========================

class SubmitAnswerResponse(BaseModel):

    scores: EvaluationResponse

    next_question: Optional[str] = None


# =========================
# INTERVIEW HISTORY RESPONSE
# =========================

class InterviewHistoryResponse(BaseModel):

    interview_id: int

    role: str

    total_score: Optional[float] = None

    technical_score: Optional[float] = None

    communication_score: Optional[float] = None

    confidence_score: Optional[float] = None

    created_at: str


# =========================
# DASHBOARD RESPONSE
# =========================

class DashboardResponse(BaseModel):

    total_interviews: int

    average_score: float

    weak_topics: List[str]

    strong_topics: List[str]


class AnswerDetailResponse(BaseModel):
    answer_id: int
    answer_text: str
    answer_mode: Optional[str] = "text"
    technical_score: Optional[float] = None
    communication_score: Optional[float] = None
    grammar_score: Optional[float] = None
    confidence_score: Optional[float] = None
    similarity_score: Optional[float] = None
    ai_feedback: Optional[str] = None
    speech_duration_sec: Optional[float] = None
    pause_count: Optional[int] = None
    filler_count: Optional[int] = None
    vocabulary_score: Optional[float] = None
    words_per_minute: Optional[float] = None
    speech_metrics: Optional[dict] = None
    sentiment_score: Optional[float] = None


class QuestionDetailResponse(BaseModel):
    question_id: int
    question_text: str
    question_type: Optional[str] = None
    answer: Optional[AnswerDetailResponse] = None


class InterviewDetailResponse(BaseModel):
    interview_id: int
    role: str
    max_questions: Optional[int] = None
    total_score: Optional[float] = None
    technical_score: Optional[float] = None
    communication_score: Optional[float] = None
    confidence_score: Optional[float] = None
    created_at: str
    questions: List[QuestionDetailResponse] = []