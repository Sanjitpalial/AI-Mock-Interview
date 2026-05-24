"""Lightweight schema patches for existing PostgreSQL databases (create_all does not alter tables)."""

import logging
from sqlalchemy import inspect, text

from app.database import engine

logger = logging.getLogger(__name__)

USER_COLUMNS = {
    "phone": "ALTER TABLE users ADD COLUMN phone VARCHAR(32)",
    "bio": "ALTER TABLE users ADD COLUMN bio TEXT",
    "headline": "ALTER TABLE users ADD COLUMN headline VARCHAR(255)",
    "location": "ALTER TABLE users ADD COLUMN location VARCHAR(128)",
    "linkedin_url": "ALTER TABLE users ADD COLUMN linkedin_url VARCHAR(512)",
    "github_url": "ALTER TABLE users ADD COLUMN github_url VARCHAR(512)",
    "portfolio_url": "ALTER TABLE users ADD COLUMN portfolio_url VARCHAR(512)",
    "target_role": "ALTER TABLE users ADD COLUMN target_role VARCHAR(128)",
    "years_experience": "ALTER TABLE users ADD COLUMN years_experience VARCHAR(32)",
    "education": "ALTER TABLE users ADD COLUMN education TEXT",
    "skills": "ALTER TABLE users ADD COLUMN skills JSON",
}

INTERVIEW_COLUMNS = {
    "max_questions": "ALTER TABLE interviews ADD COLUMN max_questions INTEGER DEFAULT 7",
    "summary_feedback": "ALTER TABLE interviews ADD COLUMN summary_feedback TEXT",
}

ANSWER_COLUMNS = {
    "sentiment_score": "ALTER TABLE answers ADD COLUMN sentiment_score FLOAT",
    "answer_mode": "ALTER TABLE answers ADD COLUMN answer_mode VARCHAR(16) DEFAULT 'text'",
    "speech_duration_sec": "ALTER TABLE answers ADD COLUMN speech_duration_sec FLOAT",
    "pause_count": "ALTER TABLE answers ADD COLUMN pause_count INTEGER DEFAULT 0",
    "filler_count": "ALTER TABLE answers ADD COLUMN filler_count INTEGER DEFAULT 0",
    "vocabulary_score": "ALTER TABLE answers ADD COLUMN vocabulary_score FLOAT",
    "words_per_minute": "ALTER TABLE answers ADD COLUMN words_per_minute FLOAT",
    "speech_metrics": "ALTER TABLE answers ADD COLUMN speech_metrics JSON",
}


def _add_missing_columns(table: str, column_ddls: dict) -> None:
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns(table)}
    with engine.begin() as conn:
        for col, ddl in column_ddls.items():
            if col not in existing:
                try:
                    conn.execute(text(ddl))
                    logger.info("Added column %s.%s", table, col)
                except Exception as exc:
                    logger.warning("Could not add %s.%s: %s", table, col, exc)


def run_migrations() -> None:
    _add_missing_columns("users", USER_COLUMNS)
    _add_missing_columns("interviews", INTERVIEW_COLUMNS)
    _add_missing_columns("answers", ANSWER_COLUMNS)
