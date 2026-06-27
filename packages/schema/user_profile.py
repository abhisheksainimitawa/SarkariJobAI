from pydantic import BaseModel
from datetime import date
from typing import Literal


class PhysicalMeasurements(BaseModel):
    height_cm: float | None = None
    chest_cm: float | None = None
    vision_left: str | None = None
    vision_right: str | None = None


class UserProfile(BaseModel):
    dob: date
    category: Literal["Gen", "OBC", "SC", "ST", "EWS"]
    gender: Literal["male", "female", "other"]
    state: str
    qualification_level: Literal["10th", "12th", "diploma", "graduate", "postgraduate", "phd"]
    qualification_fields: list[str] = []
    qualification_percentage: float | None = None
    exams_cleared: list[str] = []
    experience_years: int = 0
    experience_domain: str | None = None
    is_pwd: bool = False
    is_ex_serviceman: bool = False
    physical: PhysicalMeasurements = PhysicalMeasurements()

    @property
    def age(self) -> int:
        today = date.today()
        return today.year - self.dob.year - (
            (today.month, today.day) < (self.dob.month, self.dob.day)
        )
