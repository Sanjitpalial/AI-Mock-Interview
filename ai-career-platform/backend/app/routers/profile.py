from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.users import User
from app.routers.auth import get_current_user
from app.schemas.users import ProfileResponse, ProfileUpdate, PasswordChange
from app.services.auth_service import verify_password, hash_password

router = APIRouter(prefix="/profile", tags=["profile"])


def _user_to_profile(user: User) -> ProfileResponse:
    skills = user.skills
    if skills is not None and not isinstance(skills, list):
        skills = list(skills) if skills else []
    return ProfileResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        bio=user.bio,
        headline=user.headline,
        location=user.location,
        linkedin_url=user.linkedin_url,
        github_url=user.github_url,
        portfolio_url=user.portfolio_url,
        target_role=user.target_role,
        years_experience=user.years_experience,
        education=user.education,
        skills=skills,
    )


@router.get("", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return _user_to_profile(current_user)


@router.patch("", response_model=ProfileResponse)
def update_profile(
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        if key == "skills" and value is not None:
            value = [str(s).strip() for s in value if str(s).strip()]
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return _user_to_profile(user)


@router.post("/change-password")
def change_password(
    body: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user or not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"message": "Password updated"}
