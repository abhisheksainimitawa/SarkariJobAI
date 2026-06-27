from pydantic import BaseModel, Field
from typing import Literal


class AgeRule(BaseModel):
    min: int = 18
    max: int = 45
    relaxations: dict[str, int] = Field(default_factory=lambda: {
        "SC": 5, "ST": 5, "OBC": 3, "PwD": 10, "ExServicemen": 5
    })
    as_of_date: str | None = None


class QualificationRule(BaseModel):
    level: Literal["10th", "12th", "diploma", "graduate", "postgraduate", "phd", "any"]
    fields: list[str] = ["any"]
    min_percentage: float | None = None


class PhysicalStandards(BaseModel):
    applies_to: list[str] = []
    height_cm_min: dict[str, int] = Field(default_factory=dict)
    chest_cm_min: int | None = None
    vision: str | None = None


class ExperienceRule(BaseModel):
    years_min: int = 0
    domain: str | None = None


class JobCriteria(BaseModel):
    age: AgeRule = Field(default_factory=AgeRule)
    qualifications: list[QualificationRule] = Field(default_factory=list)
    gender: list[str] = ["any"]
    categories_allowed: list[str] = ["Gen", "OBC", "SC", "ST", "EWS"]
    domicile: dict[str, list[str]] = Field(default_factory=lambda: {"states": ["any"]})
    physical_standards: PhysicalStandards = Field(default_factory=PhysicalStandards)
    required_exams: list[str] = Field(default_factory=list)
    experience: ExperienceRule = Field(default_factory=ExperienceRule)
    job_type: str = "civil"
    nationality: list[str] = ["Indian"]
    free_text_clauses: list[str] = Field(default_factory=list)
    low_confidence_fields: list[str] = Field(default_factory=list)
    extraction_confidence: dict[str, float] = Field(default_factory=dict)
