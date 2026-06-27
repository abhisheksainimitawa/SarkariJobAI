from sqlalchemy import Column, String, Boolean, Date, Float, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase
import uuid


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)

    # Profile fields
    dob = Column(Date, nullable=True)
    category = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    state = Column(String, nullable=True)
    qualification_level = Column(String, nullable=True)
    qualification_fields = Column(JSON, default=list)
    qualification_percentage = Column(Float, nullable=True)
    exams_cleared = Column(JSON, default=list)
    experience_years = Column(Integer, default=0)
    experience_domain = Column(String, nullable=True)
    is_pwd = Column(Boolean, default=False)
    is_ex_serviceman = Column(Boolean, default=False)
    physical = Column(JSON, default=dict)

    is_active = Column(Boolean, default=True)
