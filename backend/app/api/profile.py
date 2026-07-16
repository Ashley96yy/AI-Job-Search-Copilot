import json
from io import BytesIO
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pypdf import PdfReader
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.job_skill import JobSkill
from app.models.raw_job import RawJob
from app.models.resume_version import ResumeVersion
from app.models.user_profile import UserProfile
from app.schemas.profile import (
    DomainExperienceItem,
    EducationItem,
    ProfileSkill,
    ProfileFromResumeVersion,
    SkillGapByRole,
    SkillGapItem,
    SkillGapSummary,
    UserProfileRead,
    UserProfileSkillUpdate,
    UserProfileUpsert,
    WorkExperienceItem,
)
from app.services.fit_score import normalize_skill, parse_profile_skills
from app.services.profile_parser import parse_profile_sections
from app.services.skill_extraction import extract_skills_from_text


router = APIRouter(prefix="/profile", tags=["profile"])

MAX_RESUME_FILE_SIZE_BYTES = 5 * 1024 * 1024
SUPPORTED_RESUME_EXTENSIONS = {".pdf", ".txt", ".md"}
SOFT_SKILL_CATEGORY = "soft_skills"
DEFAULT_USER_ID = 1


def _serialize_skills(resume_text: str) -> str:
    skills = extract_skills_from_text(resume_text)
    return json.dumps(
        [{"skill": item.skill, "category": item.category} for item in skills],
        sort_keys=True,
    )


def _serialize_profile_skills(skills: list[ProfileSkill]) -> str:
    return json.dumps(
        [{"skill": item.skill, "category": item.category} for item in skills],
        sort_keys=True,
    )


def _deserialize_skills(value: Optional[str]) -> list[ProfileSkill]:
    if not value:
        return []

    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []

    return [ProfileSkill.model_validate(item) for item in data]


def _deserialize_json_list(value: Optional[str], model):
    if not value:
        return []

    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []

    return [model.model_validate(item) for item in data]


def _to_read_model(profile: UserProfile) -> UserProfileRead:
    return UserProfileRead.model_validate(profile).model_copy(
        update={
            "extracted_skills": _deserialize_skills(profile.extracted_skills_json),
            "manual_skills": _deserialize_skills(profile.manual_skills_json),
            "work_experience": _deserialize_json_list(
                profile.work_experience_json,
                WorkExperienceItem,
            ),
            "education": _deserialize_json_list(profile.education_json, EducationItem),
            "domain_experience": _deserialize_json_list(
                profile.domain_experience_json,
                DomainExperienceItem,
            ),
        }
    )


def _file_extension(filename: Optional[str]) -> str:
    if not filename or "." not in filename:
        return ""

    return f".{filename.rsplit('.', maxsplit=1)[-1].lower()}"


def _extract_text_from_resume_file(filename: Optional[str], content: bytes) -> str:
    extension = _file_extension(filename)

    if extension not in SUPPORTED_RESUME_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_RESUME_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported resume file type. Upload one of: {supported}.",
        )

    if extension in {".txt", ".md"}:
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1")

    try:
        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from this PDF. Try uploading a text-based PDF or paste the resume text.",
        ) from exc


def _save_profile(
    db: Session,
    resume_text: str,
    name: Optional[str],
    target_roles: Optional[str],
    target_locations: Optional[str],
    source_resume_version_id: Optional[int] = None,
) -> UserProfile:
    profile = db.scalar(
        select(UserProfile)
        .where(UserProfile.user_id == DEFAULT_USER_ID)
        .order_by(UserProfile.updated_at.desc())
        .limit(1)
    )

    if not profile:
        profile = UserProfile(user_id=DEFAULT_USER_ID, resume_text=resume_text)
        db.add(profile)

    profile.name = name
    profile.resume_text = resume_text
    profile.target_roles = target_roles
    profile.target_locations = target_locations
    profile.source_resume_version_id = source_resume_version_id
    profile.extracted_skills_json = _serialize_skills(resume_text)
    parsed_sections = parse_profile_sections(resume_text)
    profile.work_experience_json = json.dumps(parsed_sections["work_experience"])
    profile.education_json = json.dumps(parsed_sections["education"])
    profile.domain_experience_json = json.dumps(parsed_sections["domain_experience"])

    db.commit()
    db.refresh(profile)
    return profile


@router.get("", response_model=Optional[UserProfileRead])
def get_profile(db: Session = Depends(get_db)) -> Optional[UserProfileRead]:
    profile = db.scalar(
        select(UserProfile)
        .where(UserProfile.user_id == DEFAULT_USER_ID)
        .order_by(UserProfile.updated_at.desc())
        .limit(1)
    )
    if not profile:
        return None

    return _to_read_model(profile)


@router.post("/from-resume-version", response_model=UserProfileRead)
def build_profile_from_resume_version(
    payload: ProfileFromResumeVersion,
    db: Session = Depends(get_db),
) -> UserProfileRead:
    resume_version = db.scalar(
        select(ResumeVersion).where(
            ResumeVersion.id == payload.resume_version_id,
            ResumeVersion.user_id == DEFAULT_USER_ID,
        )
    )
    if not resume_version:
        raise HTTPException(status_code=404, detail="Resume version not found.")

    profile = _save_profile(
        db=db,
        resume_text=resume_version.resume_text,
        name=payload.name,
        target_roles=payload.target_roles,
        target_locations=payload.target_locations,
        source_resume_version_id=resume_version.id,
    )
    return _to_read_model(profile)


@router.put("", response_model=UserProfileRead)
def upsert_profile(
    payload: UserProfileUpsert,
    db: Session = Depends(get_db),
) -> UserProfileRead:
    profile = _save_profile(
        db=db,
        resume_text=payload.resume_text,
        name=payload.name,
        target_roles=payload.target_roles,
        target_locations=payload.target_locations,
    )
    return _to_read_model(profile)


@router.post("/upload-resume", response_model=UserProfileRead)
async def upload_resume(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    target_roles: Optional[str] = Form(None),
    target_locations: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> UserProfileRead:
    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded resume file is empty.")

    if len(content) > MAX_RESUME_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Resume file must be 5 MB or smaller.")

    resume_text = _extract_text_from_resume_file(file.filename, content).strip()
    if not resume_text:
        raise HTTPException(
            status_code=400,
            detail="No readable resume text was found in this file.",
        )

    profile = _save_profile(
        db=db,
        resume_text=resume_text,
        name=name,
        target_roles=target_roles,
        target_locations=target_locations,
    )
    return _to_read_model(profile)


@router.post("/skills", response_model=UserProfileRead)
def add_manual_skill(
    payload: UserProfileSkillUpdate,
    db: Session = Depends(get_db),
) -> UserProfileRead:
    profile = db.scalar(
        select(UserProfile)
        .where(UserProfile.user_id == DEFAULT_USER_ID)
        .order_by(UserProfile.updated_at.desc())
        .limit(1)
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Save a resume profile first.")

    existing_skills = _deserialize_skills(profile.manual_skills_json)
    existing_lookup = {
        (normalize_skill(item.skill), item.category): item
        for item in existing_skills
    }
    key = (normalize_skill(payload.skill), payload.category)

    if key not in existing_lookup:
        existing_skills.append(ProfileSkill(skill=payload.skill, category=payload.category))
        profile.manual_skills_json = _serialize_profile_skills(
            sorted(existing_skills, key=lambda item: (item.category, item.skill.lower()))
        )
        db.commit()
        db.refresh(profile)

    return _to_read_model(profile)


@router.get("/skill-gaps", response_model=SkillGapSummary)
def get_skill_gap_summary(
    us_only: bool = True,
    min_target_relevance: int = 50,
    max_posting_age_days: Optional[int] = 180,
    career_eligible_only: bool = True,
    include_soft_skills: bool = False,
    limit: int = 10,
    db: Session = Depends(get_db),
) -> SkillGapSummary:
    profile = db.scalar(
        select(UserProfile)
        .where(UserProfile.user_id == DEFAULT_USER_ID)
        .order_by(UserProfile.updated_at.desc())
        .limit(1)
    )
    if not profile:
        return SkillGapSummary(
            profile_exists=False,
            profile_skills_count=0,
            analyzed_jobs_count=0,
        )

    profile_skills = parse_profile_skills(profile)
    statement = select(RawJob).where(
        or_(
            RawJob.owner_user_id.is_(None),
            RawJob.owner_user_id == DEFAULT_USER_ID,
        ),
        RawJob.is_active.is_(True),
    )

    if us_only:
        statement = statement.where(RawJob.is_us_based.is_(True))

    if career_eligible_only:
        statement = statement.where(RawJob.career_eligible.is_(True))

    statement = statement.where(RawJob.target_relevance_score >= min_target_relevance)

    if max_posting_age_days is not None:
        cutoff = datetime.utcnow() - timedelta(days=max_posting_age_days)
        statement = statement.where(RawJob.date_posted >= cutoff)

    jobs = list(db.scalars(statement).all())
    skills_by_job_id = get_job_skills_by_job_id(db, [job.id for job in jobs])
    missing_counter: Counter[tuple[str, str]] = Counter()
    missing_by_role: dict[str, Counter[tuple[str, str]]] = defaultdict(Counter)
    jobs_by_role: Counter[str] = Counter()

    for job in jobs:
        role_category = job.role_category or "unknown"
        jobs_by_role[role_category] += 1

        for skill in skills_by_job_id.get(job.id, []):
            if not include_soft_skills and skill.category == SOFT_SKILL_CATEGORY:
                continue

            if normalize_skill(skill.skill) in profile_skills:
                continue

            key = (skill.skill, skill.category)
            missing_counter[key] += 1
            missing_by_role[role_category][key] += 1

    gaps_by_role = [
        SkillGapByRole(
            role_category=role_category,
            analyzed_jobs_count=jobs_by_role[role_category],
            top_missing_skills=counter_to_gap_items(counter, limit=5),
        )
        for role_category, counter in sorted(
            missing_by_role.items(),
            key=lambda item: jobs_by_role[item[0]],
            reverse=True,
        )
    ]

    return SkillGapSummary(
        profile_exists=True,
        profile_skills_count=len(profile_skills),
        analyzed_jobs_count=len(jobs),
        top_missing_skills=counter_to_gap_items(missing_counter, limit=limit),
        gaps_by_role=gaps_by_role,
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


def counter_to_gap_items(
    counter: Counter[tuple[str, str]],
    limit: int,
) -> list[SkillGapItem]:
    return [
        SkillGapItem(skill=skill, category=category, missing_count=count)
        for (skill, category), count in counter.most_common(limit)
    ]
