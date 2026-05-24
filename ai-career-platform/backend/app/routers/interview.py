import json
import logging
from statistics import mean
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.interview import Interview, Question, Answer, Analytics
from app.models.resume import Resume
from app.routers.auth import get_current_user
from app.models.users import User
from app.agents.interview_agent import interview_graph, InterviewState
from app.services.interview_analysis import run_interview_analysis
from app.config import settings
from app.services.speech_service import analyze_speech
from app.schemas.interview import (
    StartInterviewRequest,
    SubmitAnswerRequest,
    NextQuestionRequest,
    InterviewHistoryResponse,
    DashboardResponse,
    InterviewDetailResponse,
    QuestionDetailResponse,
    AnswerDetailResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interview", tags=["interview"])


def _role_context(req: StartInterviewRequest) -> str:
    parts = [req.role.strip()]
    if req.company and req.company.strip():
        parts.append(f"target company: {req.company.strip()}")
    if req.interview_type and req.interview_type.strip():
        parts.append(f"interview style: {req.interview_type.strip()}")
    return " · ".join(parts)


def _ensure_interview_owner(
    db: Session,
    interview_id: int,
    user_id: int,
) -> Interview:
    interview = (
        db.query(Interview)
        .filter(Interview.id == interview_id, Interview.user_id == user_id)
        .first()
    )
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview


def _finalize_interview_scores(db: Session, interview: Interview) -> None:
    q_ids = [
        q.id
        for q in db.query(Question)
        .filter(Question.interview_id == interview.id)
        .all()
    ]
    if not q_ids:
        return
    answers = db.query(Answer).filter(Answer.question_id.in_(q_ids)).all()
    scored = [a for a in answers if a.technical_score is not None]
    if not scored:
        return

    def _avg(field):
        vals = [
            float(getattr(a, field) or 0)
            for a in scored
            if getattr(a, field, None) is not None
        ]
        return mean(vals) if vals else 0.0

    interview.technical_score = _avg("technical_score")
    interview.communication_score = _avg("communication_score")
    interview.confidence_score = _avg("confidence_score")
    sentiment_vals = [
        float(a.sentiment_score)
        for a in scored
        if getattr(a, "sentiment_score", None) is not None
    ]
    interview.sentiment_score = (
        mean(sentiment_vals) if sentiment_vals else _avg("grammar_score")
    )
    interview.total_score = mean(
        [
            interview.technical_score,
            interview.communication_score,
            interview.confidence_score,
            interview.sentiment_score,
        ]
    )


def _scores_for_json(scores: dict) -> dict:
    out = dict(scores)
    for k, v in list(out.items()):
        if hasattr(v, "item"):
            out[k] = float(v.item())
        elif isinstance(v, (float, int)) and k != "feedback":
            out[k] = float(v)
    return out


def _question_history(db: Session, interview_id: int) -> list:
    questions = (
        db.query(Question)
        .filter(Question.interview_id == interview_id)
        .order_by(Question.id.asc())
        .all()
    )
    history = []
    for q in questions:
        ans = db.query(Answer).filter(Answer.question_id == q.id).first()
        history.append(
            {
                "question": q.question_text or "",
                "answer": ans.answer_text if ans else "Not answered",
            }
        )
    return history


def _invoke_question(
    resume_text: str,
    role: str,
    history: list,
    question_count: int,
    max_questions: int,
) -> str:
    state: InterviewState = {
        "resume_text": resume_text[:4000],
        "role": role,
        "question_history": history,
        "current_question": None,
        "question_count": question_count,
        "max_questions": max_questions,
    }
    try:
        result = interview_graph.invoke(state)
    except Exception as exc:
        logger.exception("Interview graph failed")
        msg = str(exc).strip() or type(exc).__name__
        if "GOOGLE_API_KEY" in msg or "API key" in msg.lower():
            raise HTTPException(status_code=503, detail=msg) from exc
        raise HTTPException(
            status_code=502,
            detail=f"Question generation failed: {msg}. "
            "Set GEMINI_MODEL=gemini-2.0-flash in backend/.env and verify GOOGLE_API_KEY.",
        ) from exc

    text = (result.get("current_question") or "").strip()
    if not text:
        raise HTTPException(
            status_code=502,
            detail="Interview agent returned an empty question. Check GOOGLE_API_KEY and GEMINI_MODEL.",
        )
    return text


def _create_next_question(
    db: Session,
    interview: Interview,
    resume: Resume,
) -> dict:
    questions = (
        db.query(Question)
        .filter(Question.interview_id == interview.id)
        .order_by(Question.id.asc())
        .all()
    )
    max_q = interview.max_questions or 7
    if len(questions) >= max_q:
        return {"done": True}

    last_q = questions[-1]
    if not db.query(Answer).filter(Answer.question_id == last_q.id).first():
        raise HTTPException(
            status_code=400,
            detail="Submit an answer for the current question first",
        )

    history = _question_history(db, interview.id)
    text = _invoke_question(
        resume.extracted_text or "",
        interview.role or "",
        history,
        len(questions),
        max_q,
    )

    question = Question(
        interview_id=interview.id,
        question_text=text,
        question_type="technical",
    )
    db.add(question)
    db.flush()

    return {
        "done": False,
        "interview_id": interview.id,
        "question_id": question.id,
        "question": text,
        "question_number": len(questions) + 1,
        "total_questions": max_q,
    }


@router.get("/history", response_model=List[InterviewHistoryResponse])
def list_interview_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(Interview)
        .filter(Interview.user_id == current_user.id)
        .order_by(Interview.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        InterviewHistoryResponse(
            interview_id=r.id,
            role=r.role or "",
            total_score=r.total_score,
            technical_score=r.technical_score,
            communication_score=r.communication_score,
            confidence_score=r.confidence_score,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows
    ]


@router.get("/dashboard", response_model=DashboardResponse)
def interview_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interviews = (
        db.query(Interview)
        .filter(Interview.user_id == current_user.id)
        .all()
    )
    total = len(interviews)
    scored = [i for i in interviews if i.total_score is not None]
    avg = mean([s.total_score for s in scored]) if scored else 0.0

    weak: list[str] = []
    strong: list[str] = []
    if scored:
        tech = mean([s.technical_score or 0 for s in scored])
        comm = mean([s.communication_score or 0 for s in scored])
        conf = mean([s.confidence_score or 0 for s in scored])
        if tech < 0.65:
            weak.append("Technical depth")
        else:
            strong.append("Technical accuracy")
        if comm < 0.65:
            weak.append("Communication clarity")
        else:
            strong.append("Communication")
        if conf < 0.65:
            weak.append("Confidence / structure")
        else:
            strong.append("Confidence")

    if not weak:
        weak = ["Complete more interviews to personalize insights"]
    if not strong:
        strong = ["Keep practicing — strengths will surface here"]

    return DashboardResponse(
        total_interviews=total,
        average_score=float(avg),
        weak_topics=weak[:5],
        strong_topics=strong[:5],
    )


@router.post("/start")
async def start_interview(
    req: StartInterviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not settings.GOOGLE_API_KEY.strip():
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_API_KEY is not set. Add it to backend/.env to use the interview agent.",
        )

    resume = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .first()
    )
    if not resume:
        raise HTTPException(status_code=400, detail="Upload a resume first")

    role_context = _role_context(req)

    interview = Interview(
        user_id=current_user.id,
        role=role_context,
        max_questions=req.num_questions,
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    text = _invoke_question(
        resume.extracted_text or "",
        role_context,
        [],
        0,
        req.num_questions,
    )

    question = Question(
        interview_id=interview.id,
        question_text=text,
        question_type="technical",
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    return {
        "interview_id": interview.id,
        "question_id": question.id,
        "question": text,
        "question_number": 1,
        "total_questions": req.num_questions,
    }


def _persist_answer_fast(
    db: Session,
    req: SubmitAnswerRequest,
    speech_analysis: dict,
    mode: str,
) -> None:
    """Save answer + speech only; AI scores run after interview via /analyze."""
    row = Answer(
        question_id=req.question_id,
        answer_text=req.answer_text,
        technical_score=None,
        communication_score=None,
        grammar_score=None,
        confidence_score=None,
        similarity_score=None,
        sentiment_score=None,
        ai_feedback=None,
        answer_mode=mode,
        speech_duration_sec=speech_analysis.get("duration_sec"),
        pause_count=int(speech_analysis.get("pause_count") or 0),
        filler_count=int(speech_analysis.get("filler_count") or 0),
        vocabulary_score=float(speech_analysis.get("vocabulary_score") or 0),
        words_per_minute=speech_analysis.get("words_per_minute"),
        speech_metrics=speech_analysis,
    )
    savepoint = db.begin_nested()
    try:
        db.add(row)
        db.flush()
    except Exception as exc:
        logger.warning("Full answer save failed (%s), retrying core columns", exc)
        savepoint.rollback()
        db.add(
            Answer(
                question_id=req.question_id,
                answer_text=req.answer_text,
            )
        )
        db.flush()


@router.post("/answer")
async def submit_answer(
    req: SubmitAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        interview = _ensure_interview_owner(db, req.interview_id, current_user.id)

        question = (
            db.query(Question)
            .filter(
                Question.id == req.question_id,
                Question.interview_id == interview.id,
            )
            .first()
        )
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        existing = db.query(Answer).filter(Answer.question_id == req.question_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="This question was already answered")

        speech_input = req.speech_metrics
        mode = "text"
        duration_sec = None
        pause_count = 0
        if speech_input:
            mode = (speech_input.answer_mode or "text").lower()
            duration_sec = speech_input.duration_sec
            pause_count = speech_input.pause_count or 0

        speech_analysis = analyze_speech(
            req.answer_text,
            duration_sec=duration_sec,
            pause_count=pause_count,
            answer_mode=mode,
        )

        _persist_answer_fast(db, req, speech_analysis, mode)

        total_asked = (
            db.query(Question)
            .filter(Question.interview_id == interview.id)
            .count()
        )
        max_q = interview.max_questions or 7
        done = total_asked >= max_q

        next_payload: Optional[dict] = None
        next_error: Optional[str] = None

        if not done:
            resume = (
                db.query(Resume)
                .filter(Resume.user_id == current_user.id)
                .order_by(Resume.created_at.desc())
                .first()
            )
            if not resume:
                raise HTTPException(status_code=400, detail="Upload a resume first")
            try:
                next_payload = _create_next_question(db, interview, resume)
            except HTTPException:
                raise
            except Exception as exc:
                logger.exception("Next question after answer failed")
                next_error = str(exc)

        db.commit()

        body = {
            "saved": True,
            "speech_analysis": speech_analysis,
            "interview_complete": done,
            "ready_for_analysis": done,
        }
        if next_payload and not next_payload.get("done"):
            body["next_question"] = {
                "question_id": next_payload["question_id"],
                "question": next_payload["question"],
                "question_number": next_payload["question_number"],
                "total_questions": next_payload["total_questions"],
            }
        elif next_error and not done:
            body["interview_complete"] = True
            body["next_question_error"] = (
                f"Could not load the next question: {next_error}. Your answer was saved."
            )

        return body

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("submit_answer failed")
        db.rollback()
        msg = str(exc).strip() or type(exc).__name__
        if "column" in msg.lower() and "does not exist" in msg.lower():
            raise HTTPException(
                status_code=500,
                detail="Database is missing columns. Restart the backend to apply migrations.",
            ) from exc
        raise HTTPException(status_code=500, detail=f"Failed to submit answer: {msg}") from exc


@router.post("/{interview_id}/analyze")
async def analyze_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run AI evaluation, sentiment, speech review, and summary after all answers are in."""
    interview = _ensure_interview_owner(db, interview_id, current_user.id)

    max_q = interview.max_questions or 7
    q_count = (
        db.query(Question).filter(Question.interview_id == interview.id).count()
    )
    if q_count < max_q:
        raise HTTPException(
            status_code=400,
            detail=f"Complete all {max_q} questions before analysis ({q_count}/{max_q} done).",
        )

    try:
        result = await run_interview_analysis(db, interview)
        _finalize_interview_scores(db, interview)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("analyze_interview failed")
        db.rollback()
        msg = str(exc).strip() or type(exc).__name__
        raise HTTPException(
            status_code=500,
            detail=f"Interview analysis failed: {msg}",
        ) from exc

    summary = result.get("summary") or {}
    questions_out = []
    for item in result.get("questions", []):
        questions_out.append(
            {
                "question_id": item["question_id"],
                "question": item["question"],
                "answer": item["answer"],
                "scores": _scores_for_json(item["scores"]),
                "speech_analysis": item["speech_analysis"],
                "overall_percent": item["overall_percent"],
            }
        )

    return {
        "interview_id": interview.id,
        "average_score": result.get("average_score", 0),
        "interview_scores": {
            "technical": interview.technical_score,
            "communication": interview.communication_score,
            "confidence": interview.confidence_score,
            "sentiment": interview.sentiment_score,
            "total": interview.total_score,
        },
        "summary": summary,
        "questions": questions_out,
    }


@router.post("/next")
async def next_question(
    body: NextQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Legacy endpoint — prefer next_question in POST /answer response."""
    if not settings.GOOGLE_API_KEY.strip():
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_API_KEY is not set. Add it to backend/.env for question generation.",
        )

    interview = _ensure_interview_owner(db, body.interview_id, current_user.id)

    resume = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .first()
    )
    if not resume:
        raise HTTPException(status_code=400, detail="Upload a resume first")

    try:
        payload = _create_next_question(db, interview, resume)
        db.commit()
        return payload
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("next_question failed")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Could not generate next question: {exc}",
        ) from exc


@router.delete("/{interview_id}")
def delete_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = _ensure_interview_owner(db, interview_id, current_user.id)

    question_ids = [
        q.id
        for q in db.query(Question)
        .filter(Question.interview_id == interview.id)
        .all()
    ]
    if question_ids:
        db.query(Answer).filter(Answer.question_id.in_(question_ids)).delete(
            synchronize_session=False
        )
    db.query(Question).filter(Question.interview_id == interview.id).delete(
        synchronize_session=False
    )
    db.query(Analytics).filter(Analytics.interview_id == interview.id).delete(
        synchronize_session=False
    )
    db.delete(interview)
    db.commit()

    return {"message": "Interview deleted", "interview_id": interview_id}


@router.get("/{interview_id}", response_model=InterviewDetailResponse)
def get_interview_detail(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = _ensure_interview_owner(db, interview_id, current_user.id)

    questions = (
        db.query(Question)
        .filter(Question.interview_id == interview.id)
        .order_by(Question.id.asc())
        .all()
    )

    q_details: list[QuestionDetailResponse] = []
    for q in questions:
        ans = db.query(Answer).filter(Answer.question_id == q.id).first()
        answer_detail = None
        if ans:
            answer_detail = AnswerDetailResponse(
                answer_id=ans.id,
                answer_text=ans.answer_text or "",
                answer_mode=getattr(ans, "answer_mode", None) or "text",
                technical_score=ans.technical_score,
                communication_score=ans.communication_score,
                grammar_score=ans.grammar_score,
                confidence_score=ans.confidence_score,
                similarity_score=ans.similarity_score,
                ai_feedback=ans.ai_feedback,
                speech_duration_sec=getattr(ans, "speech_duration_sec", None),
                pause_count=getattr(ans, "pause_count", None),
                filler_count=getattr(ans, "filler_count", None),
                vocabulary_score=getattr(ans, "vocabulary_score", None),
                words_per_minute=getattr(ans, "words_per_minute", None),
                speech_metrics=getattr(ans, "speech_metrics", None),
                sentiment_score=getattr(ans, "sentiment_score", None),
            )
        q_details.append(
            QuestionDetailResponse(
                question_id=q.id,
                question_text=q.question_text or "",
                question_type=q.question_type,
                answer=answer_detail,
            )
        )

    return InterviewDetailResponse(
        interview_id=interview.id,
        role=interview.role or "",
        max_questions=interview.max_questions,
        total_score=interview.total_score,
        technical_score=interview.technical_score,
        communication_score=interview.communication_score,
        confidence_score=interview.confidence_score,
        created_at=interview.created_at.isoformat() if interview.created_at else "",
        questions=q_details,
    )
