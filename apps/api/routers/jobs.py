from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from deps import get_db, get_current_user
from models.user import User
from models.job import Job
from jobai_schema import JobCriteria, UserProfile
from services.matcher import check_eligibility

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _build_profile(user: User) -> UserProfile | None:
    if not user.dob or not user.category or not user.qualification_level:
        return None
    return UserProfile(
        dob=user.dob,
        category=user.category,
        gender=user.gender or "male",
        state=user.state or "",
        qualification_level=user.qualification_level,
        qualification_fields=user.qualification_fields or [],
        qualification_percentage=user.qualification_percentage,
        exams_cleared=user.exams_cleared or [],
        experience_years=user.experience_years or 0,
        experience_domain=user.experience_domain,
        is_pwd=user.is_pwd or False,
        is_ex_serviceman=user.is_ex_serviceman or False,
    )


@router.get("")
async def get_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = _build_profile(current_user)
    if not profile:
        return {"jobs": [], "message": "Complete your profile to see eligible jobs", "total": 0}

    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Job)
        .where(Job.status == "active")
        .where((Job.deadline == None) | (Job.deadline > now))
        .order_by(Job.published_at.desc())
    )
    all_jobs = result.scalars().all()

    eligible = []
    for job in all_jobs:
        if not job.criteria:
            continue
        try:
            criteria = JobCriteria.model_validate(job.criteria)
            is_eligible, reasons = check_eligibility(profile, criteria)
            if is_eligible:
                eligible.append({
                    "id": str(job.id),
                    "title": job.title,
                    "organization": job.organization,
                    "source_name": job.source_name,
                    "apply_url": job.apply_url,
                    "deadline": job.deadline.isoformat() if job.deadline else None,
                    "published_at": job.published_at.isoformat(),
                })
        except Exception:
            continue

    total = len(eligible)
    start = (page - 1) * page_size
    return {"jobs": eligible[start: start + page_size], "total": total, "page": page}
