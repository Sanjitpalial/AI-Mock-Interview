from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.resume import Resume
from app.models.users import User
from app.routers.auth import get_current_user
from app.services.resume_service import extract_text_from_pdf

router = APIRouter(prefix="/resume", tags=["resume"])


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fast upload: extract PDF text only (no Gemini / embeddings on this path)."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    content = await file.read()
    extracted_text = extract_text_from_pdf(content)
    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="Could not read text from this PDF")

    resume = Resume(
        user_id=current_user.id,
        extracted_text=extracted_text,
        skills=[],
        experience_level="",
        target_role="",
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return {
        "resume_id": resume.id,
        "analysis": {
            "skills": [],
            "experience": "",
            "role": "",
            "message": "Resume saved. Interview questions will use your PDF text.",
        },
    }
