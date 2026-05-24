from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load from backend/.env — unknown keys are ignored (extra='ignore')."""

    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    GOOGLE_API_KEY: str = Field(
        default="",
        validation_alias="GOOGLE_API_KEY",
    )
    

    GEMINI_MODEL: str = "gemini-2.0-flash"

    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_STUDY_DIR: str = "./chroma_study_db"

    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "ai-career-platform"

    # Study Assistant (Groq) — https://console.groq.com/keys
    GROQ_API_KEY: str = Field(default="")
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    SAS_HOST: Optional[str] = None
    SAS_PORT: Optional[int] = None
    SAS_USER: Optional[str] = None
    SAS_PASSWORD: Optional[str] = None
    SAS_DATABASE: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
