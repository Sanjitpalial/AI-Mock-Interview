from sqlalchemy import Column, Integer, String, Text, JSON
from app.database import Base


class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column("password", String, nullable=False)

    phone = Column(String(32), nullable=True)
    bio = Column(Text, nullable=True)
    headline = Column(String(255), nullable=True)
    location = Column(String(128), nullable=True)
    linkedin_url = Column(String(512), nullable=True)
    github_url = Column(String(512), nullable=True)
    portfolio_url = Column(String(512), nullable=True)
    target_role = Column(String(128), nullable=True)
    years_experience = Column(String(32), nullable=True)
    education = Column(Text, nullable=True)
    skills = Column(JSON, nullable=True)
