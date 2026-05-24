from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Interview(Base):
    __tablename__ = "interviews"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String)
    max_questions = Column(Integer, default=7)
    total_score = Column(Float)
    technical_score = Column(Float)
    communication_score = Column(Float)
    confidence_score = Column(Float)
    sentiment_score = Column(Float)
    summary_feedback = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    questions = relationship("Question", back_populates="interview")


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"))
    question_text = Column(Text)
    expected_answer = Column(Text)
    question_type = Column(String)
    interview = relationship("Interview", back_populates="questions")


class Answer(Base):
    __tablename__ = "answers"
    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    answer_text = Column(Text)
    technical_score = Column(Float)
    communication_score = Column(Float)
    grammar_score = Column(Float)
    confidence_score = Column(Float)
    similarity_score = Column(Float)
    sentiment_score = Column(Float, nullable=True)
    ai_feedback = Column(Text)

    answer_mode = Column(String(16), default="text")
    speech_duration_sec = Column(Float, nullable=True)
    pause_count = Column(Integer, default=0)
    filler_count = Column(Integer, default=0)
    vocabulary_score = Column(Float, nullable=True)
    words_per_minute = Column(Float, nullable=True)
    speech_metrics = Column(JSON, nullable=True)


class Analytics(Base):
    __tablename__ = "analytics"
    id = Column(Integer, primary_key=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    percentile_technical = Column(Float)
    percentile_communication = Column(Float)
    placement_probability = Column(Float)
    candidate_cluster = Column(String)
    trend_score = Column(Float)
    sas_report_path = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
