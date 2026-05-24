from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    JSON,
    ForeignKey
)

from sqlalchemy.sql import func

from app.database import Base


class StudyDocument(Base):

    __tablename__ = "study_documents"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    filename = Column(String(255), nullable=False)

    total_chunks = Column(Integer, default=0)

    topic_tags = Column(String(500))

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

class ChatHistory(Base):

    __tablename__ = "study_chats"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    question = Column(Text, nullable=False)

    answer = Column(Text, nullable=False)

    sources = Column(JSON, default=list)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class NoteRecord(Base):

    __tablename__ = "study_notes"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    topic = Column(String(255))

    notes = Column(Text, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class QuizRecord(Base):

    __tablename__ = "study_quizzes"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    topic = Column(String(255), nullable=False)

    quiz = Column(Text, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class FlashcardRecord(Base):

    __tablename__ = "study_flashcards"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    topic = Column(String(255), nullable=False)

    flashcards = Column(Text, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class StudyPlanRecord(Base):

    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    plan_type = Column(String(50), default="roadmap")

    topic = Column(String(500), nullable=False)

    content = Column(Text, nullable=False)

    metadata_json = Column(JSON, default=dict)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
