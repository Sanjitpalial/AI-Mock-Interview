import logging

"""
app/routers/study.py
───────────────────────────────────────────────────────────────────
Study Assistant Router.

Keeps ALL original endpoints from collaborator's code unchanged.
Adds new Study Planner Agent endpoints.

Storage : PostgreSQL  (via SQLAlchemy — replaces MongoDB)
Vectors : ChromaDB    (via rag_agent.py)
LLM     : Groq        (via rag_agent.py + study_planner_agent.py)
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.services.resume_service import extract_text_from_pdf
from app.services.groq_client import require_groq_key, verify_groq_connection
from app.models.users import User
from app.routers.auth import get_current_user

from app.models.study import (
    StudyDocument,
    ChatHistory,
    NoteRecord,
    QuizRecord,
    FlashcardRecord,
    StudyPlanRecord,
)

from app.agents.rag_agent import (
    store_pdf_chunks,
    delete_pdf_chunks,
    get_chunk_count,
    list_pdf_sources,
    ask_doubt,
    generate_notes,
    generate_quiz,
    generate_flashcards,
    clear_memory,
)
from app.agents.study_planner_agent import (
    generate_study_plan,
    generate_topic_roadmap,
    generate_career_roadmap,
    generate_weak_area_plan,
    generate_post_interview_plan,
)

router = APIRouter(prefix="/study", tags=["study"])
logger = logging.getLogger(__name__)


def _current_uid(current_user: User = Depends(get_current_user)) -> int:
    return current_user.id


def _require_groq() -> None:
    try:
        require_groq_key()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _study_http_error(exc: Exception, action: str) -> HTTPException:
    logger.exception("%s failed", action)
    msg = str(exc).strip() or type(exc).__name__
    if "GROQ_API_KEY" in msg or "API key" in msg.lower():
        return HTTPException(status_code=503, detail=msg)
    if "rate" in msg.lower() or "quota" in msg.lower():
        return HTTPException(status_code=429, detail=msg)
    if "No text chunks" in msg or "upload a PDF" in msg.lower():
        return HTTPException(status_code=400, detail=msg)
    return HTTPException(status_code=502, detail=f"{action} failed: {msg}")


from app.config import settings as app_settings

from app.schemas.study import (
    QuestionRequest,
    QuizRequest,
    FlashcardRequest,
    NotesRequest,
    RoadmapRequest,
    StudyPlanRequest,
    WeakAreaPlanRequest,
    CareerRoadmapRequest,
    PostInterviewPlanRequest,
)

# ═════════════════════════════════════════════════════════════════════════════
# 1. HOME
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/")
def home():
    groq_ok = False
    try:
        require_groq_key()
        groq_ok = True
    except ValueError:
        pass
    return {
        "message": "Study Assistant Running",
        "database": "PostgreSQL",
        "vector_db": "ChromaDB",
        "groq_configured": groq_ok,
        "chroma_dir": app_settings.CHROMA_STUDY_DIR,
    }


@router.get("/status")
def study_status():
    try:
        require_groq_key()
    except ValueError as exc:
        return {"ok": False, "groq_configured": False, "groq_working": False, "detail": str(exc)}
    try:
        verify_groq_connection()
        return {"ok": True, "groq_configured": True, "groq_working": True}
    except ValueError as exc:
        return {
            "ok": False,
            "groq_configured": True,
            "groq_working": False,
            "detail": str(exc),
        }


# ═════════════════════════════════════════════════════════════════════════════
# 2. UPLOAD PDF
#    Mirrors collaborator's /upload-pdf — exact same response shape
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/upload-pdf")
async def upload_pdf(
    file   : UploadFile = File(...),
    user_id: int = Depends(_current_uid),
    db     : Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")

    text = extract_text_from_pdf(contents)
    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="No text found in PDF. It may be a scanned image — use a text-based PDF.",
        )

    record = StudyDocument(
        user_id=user_id,
        filename=file.filename,
        total_chunks=0,
    )
    db.add(record)
    try:
        db.flush()
        total_chunks = store_pdf_chunks(user_id, str(record.id), file.filename, text)
        if total_chunks == 0:
            raise HTTPException(status_code=400, detail="Could not index PDF content")
        record.total_chunks = total_chunks
        db.commit()
        db.refresh(record)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"PDF indexing failed: {exc}") from exc

    return {
        "message": "PDF processed successfully",
        "file_name": file.filename,
        "filename": file.filename,
        "total_chunks": total_chunks,
        "record_id": record.id,
        "document_id": record.id,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 3. LIST UPLOADED PDFs
#    Mirrors collaborator's /uploaded-pdfs
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/uploaded-pdfs")
async def uploaded_pdfs(
    user_id: int = Depends(_current_uid),
    db     : Session = Depends(get_db),
):
    # ── Query PostgreSQL (replaces: collection.get() + metadata loop) ─────────
    records = (
        db.query(StudyDocument)
        .filter(StudyDocument.user_id == user_id)
        .order_by(StudyDocument.created_at.desc())
        .all()
    )

    return {
        "uploaded_pdfs": [
            {
                "id"          : r.id,
                "file_name"   : r.filename,
                "total_chunks": r.total_chunks,
                "uploaded_at" : r.created_at,
            }
            for r in records
        ],
        "total_pdfs": len(records),
    }


# ═════════════════════════════════════════════════════════════════════════════
# 4. DELETE PDF
#    Mirrors collaborator's /delete-pdf/{pdf_name}
# ═════════════════════════════════════════════════════════════════════════════

@router.delete("/delete-pdf/{pdf_name}")
async def delete_pdf(
    pdf_name: str,
    user_id: int = Depends(_current_uid),
    db      : Session = Depends(get_db),
):
    deleted_chunks = delete_pdf_chunks(user_id, pdf_name)

    removed = (
        db.query(StudyDocument)
        .filter(
            StudyDocument.filename == pdf_name,
            StudyDocument.user_id == user_id,
        )
        .delete(synchronize_session=False)
    )
    db.commit()

    if deleted_chunks == 0 and removed == 0:
        raise HTTPException(status_code=404, detail=f"{pdf_name} not found")

    return {
        "message": f"{pdf_name} deleted successfully.",
        "deleted_chunks": deleted_chunks,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 5. ASK QUESTION  (RAG)
#    Mirrors collaborator's /ask-question — same response shape
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/ask-question")
async def ask_question(
    data   : QuestionRequest,
    user_id: int = Depends(_current_uid),
    db     : Session = Depends(get_db),
):
    _require_groq()

    try:
        result = ask_doubt(user_id, data.question, data.pdf_name)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise _study_http_error(exc, "Ask question") from exc

    answer = result.get("answer") or "No answer generated."
    sources = result.get("sources") or []

    if "Groq request failed" in answer or "GROQ_API_KEY" in answer:
        raise HTTPException(status_code=503, detail=answer)

    record_id = None
    try:
        record = ChatHistory(
            user_id=user_id,
            question=data.question,
            answer=answer,
            sources=sources,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        record_id = record.id
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to save chat history")

    return {
        "id": record_id,
        "question": data.question,
        "answer": answer,
        "sources": sources,
        "retrieved_chunks": result.get("chunks") or [],
    }


# ═════════════════════════════════════════════════════════════════════════════
# 6. GET CHAT HISTORY
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/chat-history")
def get_chat_history(
    limit  : int = 20,
    user_id: int = Depends(_current_uid),
    db     : Session = Depends(get_db),
):
    records = (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == user_id)
        .order_by(ChatHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "question": r.question,
            "answer": r.answer,
            "sources": r.sources or [],
            "asked_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


# ═════════════════════════════════════════════════════════════════════════════
# 7. GENERATE NOTES
#    Mirrors collaborator's /generate-notes
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/generate-notes")
async def generate_notes_endpoint(
    data   : NotesRequest = NotesRequest(),
    user_id: int = Depends(_current_uid),
    db     : Session = Depends(get_db),
):
    _require_groq()
    try:
        notes = generate_notes(
            user_id,
            pdf_name=data.pdf_name,
            specification=data.specification,
        )
    except Exception as exc:
        raise _study_http_error(exc, "Generate notes") from exc

    if notes.startswith("Please upload") or notes.startswith("No text chunks"):
        raise HTTPException(status_code=400, detail=notes)
    if notes.startswith("Groq request failed") or notes.startswith("GROQ_API_KEY"):
        raise HTTPException(status_code=503, detail=notes)

    label = (data.specification or "").strip() or (
        f"Full PDF: {data.pdf_name}" if data.pdf_name else "All PDFs"
    )
    try:
        record = NoteRecord(user_id=user_id, topic=label, notes=notes)
        db.add(record)
        db.commit()
        db.refresh(record)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to save notes record")
        return {
            "generated_notes": notes,
            "record_id": None,
            "pdf_name": data.pdf_name,
            "specification": data.specification,
            "scope": label,
            "warning": f"Notes generated but not saved to database: {exc}",
        }

    return {
        "generated_notes": notes,
        "record_id": record.id,
        "pdf_name": data.pdf_name,
        "specification": data.specification,
        "scope": label,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 8. NOTES HISTORY
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/notes-history")
def get_notes_history(
    limit  : int = 10,
    user_id: int = Depends(_current_uid),
    db     : Session = Depends(get_db),
):
    rows = (
        db.query(NoteRecord)
        .filter(NoteRecord.user_id == user_id)
        .order_by(NoteRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {"id": r.id, "topic": r.topic, "notes": r.notes, "created_at": r.created_at}
        for r in rows
    ]


# ═════════════════════════════════════════════════════════════════════════════
# 9. GENERATE QUIZ
#    Mirrors collaborator's /generate-quiz
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/generate-quiz")
async def generate_quiz_endpoint(
    data   : QuizRequest,
    user_id: int = Depends(_current_uid),
    db     : Session = Depends(get_db),
):
    _require_groq()
    try:
        quiz = generate_quiz(
            user_id,
            pdf_name=data.pdf_name,
            specification=data.specification,
            num_questions=data.num_questions,
        )
    except Exception as exc:
        raise _study_http_error(exc, "Generate quiz") from exc

    if quiz.startswith("Please upload") or quiz.startswith("No text chunks"):
        raise HTTPException(status_code=400, detail=quiz)
    if quiz.startswith("Groq request failed") or quiz.startswith("GROQ_API_KEY"):
        raise HTTPException(status_code=503, detail=quiz)

    label = (data.specification or "").strip() or (
        f"Full PDF: {data.pdf_name}" if data.pdf_name else "All PDFs"
    )
    try:
        record = QuizRecord(user_id=user_id, topic=label, quiz=quiz)
        db.add(record)
        db.commit()
        db.refresh(record)
        record_id = record.id
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to save quiz record")
        record_id = None

    return {
        "topic": label,
        "quiz": quiz,
        "record_id": record_id,
        "pdf_name": data.pdf_name,
        "specification": data.specification,
        "scope": label,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 10. QUIZ HISTORY
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/quiz-history")
def get_quiz_history(
    limit  : int = 10,
    user_id: int = Depends(_current_uid),
    db     : Session = Depends(get_db),
):
    rows = (
        db.query(QuizRecord)
        .filter(QuizRecord.user_id == user_id)
        .order_by(QuizRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {"id": r.id, "topic": r.topic, "quiz": r.quiz, "created_at": r.created_at}
        for r in rows
    ]


# ═════════════════════════════════════════════════════════════════════════════
# 11. GENERATE FLASHCARDS
#     Mirrors collaborator's /generate-flashcards
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/generate-flashcards")
async def generate_flashcards_endpoint(
    data   : FlashcardRequest,
    user_id: int = Depends(_current_uid),
    db     : Session = Depends(get_db),
):
    _require_groq()
    try:
        flashcards = generate_flashcards(
            user_id,
            pdf_name=data.pdf_name,
            specification=data.specification,
            num_cards=data.num_cards,
        )
    except Exception as exc:
        raise _study_http_error(exc, "Generate flashcards") from exc

    if flashcards.startswith("Please upload") or flashcards.startswith("No text chunks"):
        raise HTTPException(status_code=400, detail=flashcards)
    if flashcards.startswith("Groq request failed") or flashcards.startswith("GROQ_API_KEY"):
        raise HTTPException(status_code=503, detail=flashcards)

    label = (data.specification or "").strip() or (
        f"Full PDF: {data.pdf_name}" if data.pdf_name else "All PDFs"
    )
    try:
        record = FlashcardRecord(user_id=user_id, topic=label, flashcards=flashcards)
        db.add(record)
        db.commit()
        db.refresh(record)
        record_id = record.id
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to save flashcard record")
        record_id = None

    return {
        "topic": label,
        "flashcards": flashcards,
        "record_id": record_id,
        "pdf_name": data.pdf_name,
        "specification": data.specification,
        "scope": label,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 12. GENERATE ROADMAP  (collaborator's original endpoint)
#     Mirrors collaborator's /generate-roadmap
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/generate-roadmap")
async def generate_roadmap(
    data   : RoadmapRequest,
    user_id: int = Depends(_current_uid),
    db     : Session = Depends(get_db),
):
    _require_groq()
    try:
        roadmap = generate_topic_roadmap(data.topic)
    except Exception as exc:
        raise _study_http_error(exc, "Generate roadmap") from exc

    if roadmap.startswith("Groq request failed") or roadmap.startswith("GROQ_API_KEY"):
        raise HTTPException(status_code=503, detail=roadmap)

    try:
        record = StudyPlanRecord(
            user_id=user_id,
            plan_type="roadmap",
            topic=data.topic,
            content=roadmap,
            metadata_json={"topic": data.topic},
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        record_id = record.id
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to save roadmap record")
        record_id = None

    return {
        "topic": data.topic,
        "roadmap": roadmap,
        "record_id": record_id,
    }


# ═════════════════════════════════════════════════════════════════════════════
# ── NEW STUDY PLANNER AGENT ENDPOINTS ────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

# ═════════════════════════════════════════════════════════════════════════════
# 13. WEEK-BY-WEEK STUDY PLAN  ← study_planner_agent
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/study-plan")
async def create_study_plan(
    data   : StudyPlanRequest,
    user_id: int = Depends(_current_uid),
    db     : Session = Depends(get_db),
):
    plan = generate_study_plan(data.goal, data.current_level, data.weeks_available)

    record = StudyPlanRecord(
        user_id     = user_id,
        plan_type   = "study_plan",
        topic       = f"[STUDY PLAN] {data.goal}",
        content     = plan,
        metadata_json = {
            "goal"           : data.goal,
            "current_level"  : data.current_level,
            "weeks_available": data.weeks_available,
        },
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "goal"           : data.goal,
        "current_level"  : data.current_level,
        "weeks_available": data.weeks_available,
        "study_plan"     : plan,
        "record_id"      : record.id,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 14. CAREER ROADMAP  ← study_planner_agent
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/career-roadmap")
async def career_roadmap_endpoint(
    data   : CareerRoadmapRequest,
    user_id: int = Depends(_current_uid),
    db     : Session = Depends(get_db),
):
    roadmap = generate_career_roadmap(data.role, data.current_skills, data.experience)

    record = StudyPlanRecord(
        user_id     = user_id,
        plan_type   = "career",
        topic       = f"[CAREER] {data.role}",
        content     = roadmap,
        metadata_json = {
            "role"          : data.role,
            "current_skills": data.current_skills,
            "experience"    : data.experience,
        },
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "target_role"   : data.role,
        "current_skills": data.current_skills,
        "experience"    : data.experience,
        "career_roadmap": roadmap,
        "record_id"     : record.id,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 15. WEAK AREA PLAN  ← study_planner_agent + connects to SAS/interview scores
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/weak-area-plan")
async def weak_area_plan_endpoint(
    data   : WeakAreaPlanRequest,
    user_id: int = Depends(_current_uid),
    db     : Session = Depends(get_db),
):
    plan = generate_weak_area_plan(data.weak_topics, data.role)

    record = StudyPlanRecord(
        user_id     = user_id,
        plan_type   = "weak_area",
        topic       = f"[WEAK AREAS] {data.role}: {', '.join(data.weak_topics)}",
        content     = plan,
        metadata_json = {
            "role"       : data.role,
            "weak_topics": data.weak_topics,
        },
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "role"            : data.role,
        "weak_topics"     : data.weak_topics,
        "improvement_plan": plan,
        "record_id"       : record.id,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 16. POST-INTERVIEW IMPROVEMENT PLAN  ← study_planner_agent
#     Called automatically after interview completion
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/post-interview-plan")
async def post_interview_plan_endpoint(
    data   : PostInterviewPlanRequest,
    user_id: int = Depends(_current_uid),
    db     : Session = Depends(get_db),
):
    plan = generate_post_interview_plan(
        role                = data.role,
        technical_score     = data.technical_score,
        communication_score = data.communication_score,
        confidence_score    = data.confidence_score,
        weak_topics         = data.weak_topics,
    )

    record = StudyPlanRecord(
        user_id     = user_id,
        plan_type   = "post_interview",
        topic       = f"[POST INTERVIEW] {data.role}",
        content     = plan,
        metadata_json = {
            "role"               : data.role,
            "technical_score"    : data.technical_score,
            "communication_score": data.communication_score,
            "confidence_score"   : data.confidence_score,
            "weak_topics"        : data.weak_topics,
        },
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "role"            : data.role,
        "scores"          : {
            "technical"    : data.technical_score,
            "communication": data.communication_score,
            "confidence"   : data.confidence_score,
        },
        "improvement_plan": plan,
        "record_id"       : record.id,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 17. PLAN HISTORY  (all plan types)
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/plan-history")
def get_plan_history(
    plan_type: Optional[str] = None,   # roadmap / study_plan / weak_area / career / post_interview
    limit    : int = 10,
    user_id: int = Depends(_current_uid),
    db       : Session = Depends(get_db),
):
    query = db.query(StudyPlanRecord).filter(StudyPlanRecord.user_id == user_id)
    if plan_type:
        query = query.filter(StudyPlanRecord.plan_type == plan_type)

    records = query.order_by(StudyPlanRecord.created_at.desc()).limit(limit).all()

    return [
        {
            "id"        : r.id,
            "plan_type" : r.plan_type,
            "topic"     : r.topic,
            "content"   : r.content,
            "metadata"  : r.metadata_json,
            "created_at": r.created_at,
        }
        for r in records
    ]


# ═════════════════════════════════════════════════════════════════════════════
# 18. CLEAR CONVERSATION MEMORY
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/clear-memory")
def clear_conversation_memory(user_id: int = Depends(_current_uid)):
    clear_memory(user_id)
    return {"message": "Conversation memory cleared ✅"}


# ═════════════════════════════════════════════════════════════════════════════
# 19. STATS
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/stats")
def get_stats(
    user_id: int = Depends(_current_uid),
    db     : Session = Depends(get_db),
):
    def _count(model):
        return db.query(model).filter(model.user_id == user_id).count()

    return {
        "chroma_chunks"      : get_chunk_count(user_id),
        "pdfs_uploaded"      : _count(StudyDocument),
        "questions_asked"    : _count(ChatHistory),
        "notes_generated"    : _count(NoteRecord),
        "quizzes_generated"  : _count(QuizRecord),
        "flashcards_generated": _count(FlashcardRecord),
        "plans_generated"    : _count(StudyPlanRecord),
    }