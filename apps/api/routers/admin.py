from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
import hashlib

from deps import get_db
from models.job import Job

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(__import__("sqlalchemy").text("SELECT 1"))
    return {"status": "ok"}


@router.post("/upload-job", status_code=201)
async def upload_job(
    file: UploadFile = File(...),
    source_name: str = "manual",
    title: str = "Uploaded Job",
    organization: str = "Unknown",
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()

    job = Job(
        id=uuid4(),
        source_name=source_name,
        source_job_id=content_hash[:16],
        title=title,
        organization=organization,
        raw_text=content.decode("utf-8", errors="replace"),
        content_hash=content_hash,
        status="pending_extraction",
    )
    db.add(job)
    await db.commit()
    return {"id": str(job.id), "status": "pending_extraction"}
