from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.job_skill import JobSkill
from app.models.raw_job import RawJob
from app.models.resume_version import ResumeVersion
from app.models.user_profile import UserProfile
from app.schemas.assistant import (
    CoverLetterRequest,
    CoverLetterResponse,
    ResumeSuggestionRequest,
    ResumeSuggestionResponse,
)
from app.services.cover_letter import build_cover_letter
from app.services.resume_suggestions import build_resume_suggestions


router = APIRouter(prefix="/assistant", tags=["assistant"])
DEFAULT_USER_ID = 1


@router.post("/resume-suggestions", response_model=ResumeSuggestionResponse)
def get_resume_suggestions(
    payload: ResumeSuggestionRequest,
    db: Session = Depends(get_db),
) -> ResumeSuggestionResponse:
    job = db.get(RawJob, payload.raw_job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    profile = db.scalar(
        select(UserProfile)
        .where(UserProfile.user_id == DEFAULT_USER_ID)
        .order_by(UserProfile.updated_at.desc())
        .limit(1)
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Build a profile first.")

    resume_version = None
    if payload.resume_version_id is not None:
        resume_version = db.scalar(
            select(ResumeVersion).where(
                ResumeVersion.id == payload.resume_version_id,
                ResumeVersion.user_id == DEFAULT_USER_ID,
            )
        )
        if not resume_version:
            raise HTTPException(status_code=404, detail="Resume version not found.")

    job_skills = list(
        db.scalars(
            select(JobSkill)
            .where(JobSkill.raw_job_id == payload.raw_job_id)
            .order_by(JobSkill.category, JobSkill.skill)
        ).all()
    )

    return build_resume_suggestions(
        job=job,
        job_skills=job_skills,
        profile=profile,
        resume_version=resume_version,
    )


@router.post("/cover-letter", response_model=CoverLetterResponse)
def get_cover_letter(
    payload: CoverLetterRequest,
    db: Session = Depends(get_db),
) -> CoverLetterResponse:
    job = db.get(RawJob, payload.raw_job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    profile = db.scalar(
        select(UserProfile)
        .where(UserProfile.user_id == DEFAULT_USER_ID)
        .order_by(UserProfile.updated_at.desc())
        .limit(1)
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Build a profile first.")

    resume_version = None
    if payload.resume_version_id is not None:
        resume_version = db.scalar(
            select(ResumeVersion).where(
                ResumeVersion.id == payload.resume_version_id,
                ResumeVersion.user_id == DEFAULT_USER_ID,
            )
        )
        if not resume_version:
            raise HTTPException(status_code=404, detail="Resume version not found.")

    job_skills = list(
        db.scalars(
            select(JobSkill)
            .where(JobSkill.raw_job_id == payload.raw_job_id)
            .order_by(JobSkill.category, JobSkill.skill)
        ).all()
    )

    return build_cover_letter(
        job=job,
        job_skills=job_skills,
        profile=profile,
        resume_version=resume_version,
    )
