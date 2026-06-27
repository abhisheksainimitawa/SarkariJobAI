from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import date

from deps import get_db, get_current_user
from models.user import User

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    dob: date | None = None
    category: str | None = None
    gender: str | None = None
    state: str | None = None
    qualification_level: str | None = None
    qualification_fields: list[str] | None = None
    qualification_percentage: float | None = None
    exams_cleared: list[str] | None = None
    experience_years: int | None = None
    experience_domain: str | None = None
    is_pwd: bool | None = None
    is_ex_serviceman: bool | None = None
    physical: dict | None = None


@router.get("")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "dob": current_user.dob,
        "category": current_user.category,
        "gender": current_user.gender,
        "state": current_user.state,
        "qualification_level": current_user.qualification_level,
        "qualification_fields": current_user.qualification_fields or [],
        "qualification_percentage": current_user.qualification_percentage,
        "exams_cleared": current_user.exams_cleared or [],
        "experience_years": current_user.experience_years or 0,
        "experience_domain": current_user.experience_domain,
        "is_pwd": current_user.is_pwd or False,
        "is_ex_serviceman": current_user.is_ex_serviceman or False,
        "physical": current_user.physical or {},
    }


@router.put("")
async def update_profile(
    body: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    await db.commit()
    return {"message": "Profile updated"}
