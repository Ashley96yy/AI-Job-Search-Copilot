import json
import re
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_skill import JobSkill
from app.models.raw_job import RawJob
from app.models.user_profile import UserProfile
from app.services.skill_extraction import extract_skills_from_text


ROLE_KEYWORDS = {
    "ai_ml": ["ai", "ml", "machine learning", "data scientist"],
    "analytics_adjacent": ["analytics", "operations", "strategy"],
    "data_analytics": ["data analyst", "analytics", "business intelligence", "bi"],
    "data_engineering": ["data engineer", "etl", "pipeline"],
    "engineering": ["engineer", "software"],
    "finance_accounting": ["finance", "financial", "accounting"],
    "product": ["product analyst", "product"],
    "risk_compliance": ["risk", "fraud", "compliance", "aml"],
    "sales_gtm": ["sales", "gtm", "revenue"],
}

DOMAIN_KEYWORDS = {
    "ai_ml": ["machine learning", "artificial intelligence", "llm", "modeling"],
    "analytics_adjacent": ["analytics", "business analysis", "operations", "strategy"],
    "data_analytics": ["data analytics", "data analysis", "business intelligence", "dashboard"],
    "data_engineering": ["data engineering", "data pipeline", "etl", "spark", "airflow", "dbt"],
    "finance_accounting": ["finance", "financial", "accounting", "quantitative finance"],
    "product": ["product analytics", "product analysis", "product management"],
    "risk_compliance": ["risk", "compliance", "fraud", "aml", "credit"],
}

BAY_AREA_ALIASES = (
    "bay area",
    "sf bay area",
    "san francisco bay area",
    "silicon valley",
)

BAY_AREA_LOCATIONS = (
    "san francisco",
    "south san francisco",
    "palo alto",
    "san jose",
    "san josé",
    "mountain view",
    "sunnyvale",
    "santa clara",
    "redwood city",
    "menlo park",
    "san mateo",
    "foster city",
    "cupertino",
    "oakland",
    "berkeley",
    "fremont",
    "burlingame",
    "millbrae",
    "emeryville",
    "hayward",
    "pleasanton",
    "dublin",
    "walnut creek",
)

DEFAULT_USER_ID = 1


@dataclass(frozen=True)
class FitScoreResult:
    fit_score: int
    match_level: str
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    matched_required_skills: list[str] = field(default_factory=list)
    missing_required_skills: list[str] = field(default_factory=list)
    matched_preferred_skills: list[str] = field(default_factory=list)
    missing_preferred_skills: list[str] = field(default_factory=list)
    fit_breakdown: list[dict[str, object]] = field(default_factory=list)
    fit_notes: list[str] = field(default_factory=list)


def get_latest_profile(db: Session) -> Optional[UserProfile]:
    return db.scalar(
        select(UserProfile)
        .where(UserProfile.user_id == DEFAULT_USER_ID)
        .order_by(UserProfile.updated_at.desc())
        .limit(1)
    )


def get_job_skills_by_job_id(db: Session, job_ids: list[int]) -> dict[int, list[JobSkill]]:
    if not job_ids:
        return {}

    rows = list(
        db.scalars(
            select(JobSkill)
            .where(JobSkill.raw_job_id.in_(job_ids))
            .order_by(JobSkill.category, JobSkill.skill)
        ).all()
    )
    skills_by_job_id: dict[int, list[JobSkill]] = {job_id: [] for job_id in job_ids}

    for skill in rows:
        skills_by_job_id.setdefault(skill.raw_job_id, []).append(skill)

    return skills_by_job_id


def parse_profile_skills(profile: UserProfile) -> set[str]:
    profile_skills: set[str] = set()
    extracted_skills_loaded = False

    if profile.extracted_skills_json:
        try:
            data = json.loads(profile.extracted_skills_json)
            profile_skills.update(
                normalize_skill(item["skill"]) for item in data if item.get("skill")
            )
            extracted_skills_loaded = True
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    if not extracted_skills_loaded:
        profile_skills.update(
            normalize_skill(item.skill)
            for item in extract_skills_from_text(profile.resume_text or "")
        )

    if profile.manual_skills_json:
        try:
            data = json.loads(profile.manual_skills_json)
            profile_skills.update(
                normalize_skill(item["skill"]) for item in data if item.get("skill")
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    return profile_skills


def normalize_skill(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def match_level(score: int) -> str:
    if score >= 80:
        return "Strong Match"
    if score >= 65:
        return "Good Match"
    if score >= 50:
        return "Stretch Match"
    return "Low Match"


def calculate_fit_score(
    job: RawJob,
    job_skills: list[JobSkill],
    profile: Optional[UserProfile],
) -> Optional[FitScoreResult]:
    if not profile:
        return None

    if not job.career_eligible:
        reason = job.career_eligibility_reason or "Outside the selected experience range."
        return FitScoreResult(
            fit_score=0,
            match_level="Not Eligible",
            missing_skills=sorted({skill.skill for skill in job_skills}),
            fit_breakdown=build_ineligible_breakdown(reason),
            fit_notes=[reason, "Excluded before skill-based fit scoring."],
        )

    profile_skills = parse_profile_skills(profile)
    technical_skills = [skill for skill in job_skills if skill.category != "soft_skills"]
    required_skills = sorted(
        {skill.skill for skill in technical_skills if skill.requirement_level == "required"}
    )
    preferred_skills = sorted(
        {skill.skill for skill in technical_skills if skill.requirement_level == "preferred"}
    )

    matched_required, missing_required = partition_skills(required_skills, profile_skills)
    matched_preferred, missing_preferred = partition_skills(preferred_skills, profile_skills)

    required_score = weighted_skill_score(matched_required, required_skills, 40, 20)
    preferred_score = weighted_skill_score(matched_preferred, preferred_skills, 15, 8)
    domain_score = calculate_domain_score(job, profile)
    interest_score = calculate_role_interest_score(job, profile)
    location_score = calculate_location_score(job, profile)
    seniority_score = calculate_seniority_score(job)
    total_score = min(
        100,
        required_score
        + preferred_score
        + domain_score
        + seniority_score
        + location_score
        + interest_score,
    )

    breakdown = [
        score_dimension(
            "required_skills",
            "Required skills",
            required_score,
            40,
            skill_score_explanation(matched_required, required_skills, "required"),
        ),
        score_dimension(
            "preferred_skills",
            "Preferred skills",
            preferred_score,
            15,
            skill_score_explanation(matched_preferred, preferred_skills, "preferred"),
        ),
        score_dimension(
            "domain",
            "Domain match",
            domain_score,
            15,
            domain_score_explanation(job, domain_score),
        ),
        score_dimension(
            "seniority",
            "Seniority",
            seniority_score,
            15,
            f"Classified as {job.seniority or 'unknown'}; "
            f"required experience: {job.required_experience_years if job.required_experience_years is not None else 'not specified'}.",
        ),
        score_dimension(
            "location",
            "Location / work mode",
            location_score,
            10,
            location_score_explanation(job, profile, location_score),
        ),
        score_dimension(
            "interest",
            "Role interest",
            interest_score,
            5,
            interest_score_explanation(job, profile, interest_score),
        ),
    ]
    notes = [dimension["explanation"] for dimension in breakdown]
    matched_skills = sorted(set(matched_required + matched_preferred))
    missing_skills = sorted(set(missing_required + missing_preferred))

    return FitScoreResult(
        fit_score=total_score,
        match_level=match_level(total_score),
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        matched_required_skills=matched_required,
        missing_required_skills=missing_required,
        matched_preferred_skills=matched_preferred,
        missing_preferred_skills=missing_preferred,
        fit_breakdown=breakdown,
        fit_notes=notes,
    )


def partition_skills(
    skills: list[str],
    profile_skills: set[str],
) -> tuple[list[str], list[str]]:
    matched = [skill for skill in skills if normalize_skill(skill) in profile_skills]
    missing = [skill for skill in skills if normalize_skill(skill) not in profile_skills]
    return matched, missing


def weighted_skill_score(
    matched_skills: list[str],
    all_skills: list[str],
    max_score: int,
    neutral_score: int,
) -> int:
    if not all_skills:
        return neutral_score
    return round(max_score * len(matched_skills) / len(all_skills))


def skill_score_explanation(
    matched_skills: list[str],
    all_skills: list[str],
    requirement_level: str,
) -> str:
    if not all_skills:
        return f"No explicit {requirement_level} technical skills were detected; neutral score applied."
    return f"Matched {len(matched_skills)} of {len(all_skills)} {requirement_level} technical skills."


def score_dimension(
    key: str,
    label: str,
    score: int,
    max_score: int,
    explanation: str,
) -> dict[str, object]:
    return {
        "key": key,
        "label": label,
        "score": score,
        "max_score": max_score,
        "explanation": explanation,
    }


def build_ineligible_breakdown(reason: str) -> list[dict[str, object]]:
    dimensions = [
        ("required_skills", "Required skills", 40),
        ("preferred_skills", "Preferred skills", 15),
        ("domain", "Domain match", 15),
        ("seniority", "Seniority", 15),
        ("location", "Location / work mode", 10),
        ("interest", "Role interest", 5),
    ]
    return [
        score_dimension(key, label, 0, max_score, reason)
        for key, label, max_score in dimensions
    ]


def calculate_role_interest_score(job: RawJob, profile: UserProfile) -> int:
    target_roles = (profile.target_roles or "").lower()
    if not target_roles:
        return 3

    role_keywords = ROLE_KEYWORDS.get(job.role_category or "", [])
    title = (job.normalized_title or job.title or "").lower()

    if any(keyword in target_roles for keyword in role_keywords):
        return 5

    target_tokens = [
        token.strip()
        for token in re.split(r"[,/;|]", target_roles)
        if token.strip()
    ]
    if any(token in title for token in target_tokens):
        return 5

    if job.role_category and job.role_category.replace("_", " ") in target_roles:
        return 5

    return 0


def calculate_domain_score(job: RawJob, profile: UserProfile) -> int:
    role_category = job.role_category or ""
    domain_keywords = DOMAIN_KEYWORDS.get(role_category, [])
    if not domain_keywords:
        return 7

    profile_text = " ".join(
        [
            profile.resume_text or "",
            profile.target_roles or "",
            profile.work_experience_json or "",
            profile.domain_experience_json or "",
        ]
    ).lower()
    matched_domains = [keyword for keyword in domain_keywords if keyword in profile_text]

    if len(matched_domains) >= 2:
        return 15
    if matched_domains:
        return 10
    return 0


def domain_score_explanation(job: RawJob, score: int) -> str:
    category = (job.role_category or "unknown").replace("_", " ")
    if score == 15:
        return f"Strong profile evidence for the {category} domain."
    if score > 0:
        return f"Partial or neutral profile evidence for the {category} domain."
    return f"No clear profile evidence for the {category} domain."


def calculate_location_score(job: RawJob, profile: UserProfile) -> int:
    if not profile.target_locations:
        return 5

    return 10 if location_match_reason(job, profile) else 0


def location_match_reason(job: RawJob, profile: UserProfile) -> Optional[str]:
    target_locations = (profile.target_locations or "").lower()
    if not target_locations:
        return None

    location_text = " ".join(
        [
            job.normalized_location or "",
            job.location or "",
            job.country or "",
            job.work_mode or "",
        ]
    ).lower()

    if "remote" in target_locations and job.work_mode == "remote":
        return "Remote work matches the saved profile preference."

    if (
        re.search(r"\b(?:us|usa|united states)\b", target_locations)
        and job.is_us_based
    ):
        return "US location matches the saved profile preference."

    target_is_bay_area = any(alias in target_locations for alias in BAY_AREA_ALIASES)
    job_is_bay_area = any(
        term in location_text for term in BAY_AREA_ALIASES + BAY_AREA_LOCATIONS
    )
    if target_is_bay_area and job_is_bay_area:
        return "Job location is within the Bay Area preference."

    job_uses_bay_area_alias = any(alias in location_text for alias in BAY_AREA_ALIASES)
    target_uses_bay_area_city = any(
        city in target_locations for city in BAY_AREA_LOCATIONS
    )
    if job_uses_bay_area_alias and target_uses_bay_area_city:
        return "Bay Area job region includes the saved city preference."

    target_tokens = [
        token.strip()
        for token in re.split(r"[,/;|]", target_locations)
        if token.strip()
    ]

    if any(token in location_text for token in target_tokens):
        return "Job location matches a saved location preference."

    return None


def location_score_explanation(
    job: RawJob,
    profile: UserProfile,
    score: int,
) -> str:
    if score == 10:
        return location_match_reason(job, profile) or "Location preference matched."
    if not profile.target_locations:
        return "No target location is saved; neutral score applied."
    return f"No clear match for {job.normalized_location or job.location or 'the listed location'}."


def interest_score_explanation(
    job: RawJob,
    profile: UserProfile,
    score: int,
) -> str:
    if score == 5:
        return "Role category or title matches a saved target role."
    if not profile.target_roles:
        return "No target roles are saved; neutral score applied."
    return "Role category and title do not clearly match the saved target roles."


def calculate_seniority_score(job: RawJob) -> int:
    seniority = job.seniority or "unknown"

    if seniority in {"intern", "entry", "junior"}:
        return 15
    if seniority == "unknown":
        return 10
    if seniority == "mid":
        return 8
    if seniority == "senior":
        return 2
    if seniority == "lead":
        return 0

    return 5
