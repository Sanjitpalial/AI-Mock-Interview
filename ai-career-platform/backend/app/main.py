from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.langsmith_config

from app.database import engine, Base

from app.models.users import User

from app.models.resume import Resume

from app.models.study import (
    ChatHistory,
    StudyDocument,
    NoteRecord,
    QuizRecord,
    FlashcardRecord,
    StudyPlanRecord,
)

from app.models.interview import (
    Interview,
    Question,
    Answer,
    Analytics,
)

from app.routers import (
    auth,
    resume,
    interview,
    profile,
    study,
)
from app.database_migrations import run_migrations

Base.metadata.create_all(bind=engine)
run_migrations()

app = FastAPI(
    title="AI Career Platform"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(resume.router)
app.include_router(interview.router)
app.include_router(study.router)


@app.get("/")
def home():

    return {
        "message": "AI Career Platform Backend Running"
    }