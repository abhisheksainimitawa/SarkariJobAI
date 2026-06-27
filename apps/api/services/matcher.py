from datetime import date
from jobai_schema import JobCriteria, UserProfile

QUAL_ORDER = ["10th", "12th", "diploma", "graduate", "postgraduate", "phd"]
QUAL_EQUIVALENCE: dict[str, str] = {
    "b.e": "graduate", "b.tech": "graduate", "b.sc(it)": "graduate",
    "bca": "graduate", "b.com": "graduate", "b.a": "graduate",
    "m.tech": "postgraduate", "m.e": "postgraduate", "mca": "postgraduate",
}


def _qual_level_index(level: str) -> int:
    return QUAL_ORDER.index(level) if level in QUAL_ORDER else -1


def _effective_age_max(criteria: JobCriteria, profile: UserProfile) -> int:
    base = criteria.age.max
    relaxation = criteria.age.relaxations.get(profile.category, 0)
    if profile.is_pwd:
        relaxation = max(relaxation, criteria.age.relaxations.get("PwD", 0))
    if profile.is_ex_serviceman:
        relaxation = max(relaxation, criteria.age.relaxations.get("ExServicemen", 0))
    return base + relaxation


def check_eligibility(profile: UserProfile, criteria: JobCriteria) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    # Age check
    age_max = _effective_age_max(criteria, profile)
    if profile.age < criteria.age.min:
        reasons.append(f"Age {profile.age} is below minimum {criteria.age.min}")
    elif profile.age > age_max:
        reasons.append(f"Age {profile.age} exceeds maximum {age_max} for {profile.category}")

    # Category check
    if "any" not in criteria.categories_allowed and profile.category not in criteria.categories_allowed:
        reasons.append(f"Category {profile.category} not in {criteria.categories_allowed}")

    # Gender check
    if "any" not in criteria.gender and profile.gender not in criteria.gender:
        reasons.append(f"Gender {profile.gender} not eligible")

    # Domicile check
    allowed_states = criteria.domicile.get("states", ["any"])
    if "any" not in allowed_states and profile.state not in allowed_states:
        reasons.append(f"Domicile {profile.state} not in eligible states")

    # Qualification check
    profile_idx = _qual_level_index(profile.qualification_level)
    qual_ok = False
    for q in criteria.qualifications:
        req_idx = _qual_level_index(q.level)
        if profile_idx >= req_idx:
            if q.fields == ["any"] or any(f.lower() in profile.qualification_fields for f in q.fields):
                if q.min_percentage is None or (
                    profile.qualification_percentage and profile.qualification_percentage >= q.min_percentage
                ):
                    qual_ok = True
                    break
    if criteria.qualifications and not qual_ok:
        reasons.append("Qualification does not meet requirements")

    # Exams check
    missing_exams = set(criteria.required_exams) - set(profile.exams_cleared)
    if missing_exams:
        reasons.append(f"Missing required exams: {', '.join(missing_exams)}")

    # Experience check
    if profile.experience_years < criteria.experience.years_min:
        reasons.append(
            f"Experience {profile.experience_years}yr < required {criteria.experience.years_min}yr"
        )

    is_eligible = len(reasons) == 0
    return is_eligible, reasons
