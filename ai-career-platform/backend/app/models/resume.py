from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Text
from sqlalchemy.sql import func
from app.database import Base


class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    extracted_text = Column(Text)
    skills = Column(JSON)
    experience_level = Column(String)
    target_role = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
