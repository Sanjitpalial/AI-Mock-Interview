from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class ProfileResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: Optional[str] = None
    bio: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    target_role: Optional[str] = None
    years_experience: Optional[str] = None
    education: Optional[str] = None
    skills: Optional[List[str]] = None

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    phone: Optional[str] = Field(None, max_length=32)
    bio: Optional[str] = Field(None, max_length=5000)
    headline: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=128)
    linkedin_url: Optional[str] = Field(None, max_length=512)
    github_url: Optional[str] = Field(None, max_length=512)
    portfolio_url: Optional[str] = Field(None, max_length=512)
    target_role: Optional[str] = Field(None, max_length=128)
    years_experience: Optional[str] = Field(None, max_length=32)
    education: Optional[str] = Field(None, max_length=5000)
    skills: Optional[List[str]] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)
