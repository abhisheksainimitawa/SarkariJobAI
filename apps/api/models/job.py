from sqlalchemy import Column, String, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone
import uuid

from .user import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_name = Column(String, nullable=False)
    source_job_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    organization = Column(String, nullable=False)
    raw_text = Column(Text, nullable=True)
    content_hash = Column(String, nullable=True, index=True)
    apply_url = Column(String, nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="pending_extraction", index=True)
    criteria = Column(JSON, nullable=True)
    r2_key = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
