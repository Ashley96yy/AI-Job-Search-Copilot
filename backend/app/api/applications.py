from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.application import Application
from app.models.cover_letter import CoverLetter
from app.models.raw_job import RawJob
from app.models.resume_version import ResumeVersion
from app.schemas.application import ApplicationRead, ApplicationUpsert, ApplicationWithJob


router = APIRouter(prefix="/applications", tags=["applications"])
DEFAULT_USER_ID = 1


def serialize_application(
    application: Application,
    resume_version: Optional[ResumeVersion] = None,
    cover_letter: Optional[CoverLetter] = None,
) -> ApplicationRead:
    return ApplicationRead.model_validate(application).model_copy(
        update={
            "resume_version": (
                resume_version.name if resume_version else application.resume_version
            ),
            "cover_letter_version": (
                cover_letter.name if cover_letter else application.cover_letter_version
            ),
        }
    )


@router.get("", response_model=list[ApplicationWithJob])
def list_applications(db: Session = Depends(get_db)) -> list[ApplicationWithJob]:
    rows = db.execute(
        select(Application, RawJob, ResumeVersion, CoverLetter)
        .join(RawJob, Application.raw_job_id == RawJob.id)
        .outerjoin(ResumeVersion, Application.resume_version_id == ResumeVersion.id)
        .outerjoin(CoverLetter, Application.cover_letter_id == CoverLetter.id)
        .where(Application.user_id == DEFAULT_USER_ID)
        .order_by(Application.updated_at.desc())
    ).all()

    applications: list[ApplicationWithJob] = []

    for application, job, resume_version, cover_letter in rows:
        applications.append(
            ApplicationWithJob.model_validate(
                serialize_application(application, resume_version, cover_letter)
            ).model_copy(
                update={
                    "company": job.company,
                    "title": job.title,
                    "location": job.normalized_location or job.location,
                    "job_url": job.job_url,
                    "role_category": job.role_category,
                }
            )
        )

    return applications


@router.get("/by-job/{raw_job_id}", response_model=Optional[ApplicationRead])
def get_application_by_job(
    raw_job_id: int,
    db: Session = Depends(get_db),
) -> Optional[ApplicationRead]:
    application = db.scalar(
        select(Application).where(
            Application.user_id == DEFAULT_USER_ID,
            Application.raw_job_id == raw_job_id,
        )
    )
    if not application:
        return None

    resume_version = (
        db.get(ResumeVersion, application.resume_version_id)
        if application.resume_version_id is not None
        else None
    )
    cover_letter = (
        db.get(CoverLetter, application.cover_letter_id)
        if application.cover_letter_id is not None
        else None
    )
    return serialize_application(application, resume_version, cover_letter)


@router.put("/by-job/{raw_job_id}", response_model=ApplicationRead)
def upsert_application_for_job(
    raw_job_id: int,
    payload: ApplicationUpsert,
    db: Session = Depends(get_db),
) -> ApplicationRead:
    if raw_job_id != payload.raw_job_id:
        raise HTTPException(status_code=400, detail="raw_job_id path/body mismatch")

    job = db.get(RawJob, raw_job_id)
    if not job or (
        job.owner_user_id is not None and job.owner_user_id != DEFAULT_USER_ID
    ):
        raise HTTPException(status_code=404, detail="Job not found")

    resume_version = None
    if payload.resume_version_id is not None:
        resume_version = db.scalar(
            select(ResumeVersion).where(
                ResumeVersion.id == payload.resume_version_id,
                ResumeVersion.user_id == DEFAULT_USER_ID,
            )
        )
        if not resume_version:
            raise HTTPException(status_code=404, detail="Resume version not found")

    cover_letter = None
    if payload.cover_letter_id is not None:
        cover_letter = db.scalar(
            select(CoverLetter).where(
                CoverLetter.id == payload.cover_letter_id,
                CoverLetter.user_id == DEFAULT_USER_ID,
            )
        )
        if not cover_letter:
            raise HTTPException(status_code=404, detail="Cover letter not found")
        if cover_letter.raw_job_id != raw_job_id:
            raise HTTPException(
                status_code=400,
                detail="Cover letter belongs to a different job",
            )

    application = db.scalar(
        select(Application).where(
            Application.user_id == DEFAULT_USER_ID,
            Application.raw_job_id == raw_job_id,
        )
    )

    if not application:
        application = Application(user_id=DEFAULT_USER_ID, raw_job_id=raw_job_id)
        db.add(application)

    application.status = payload.status
    application.applied_date = payload.applied_date
    application.follow_up_date = payload.follow_up_date
    application.resume_version_id = payload.resume_version_id
    application.cover_letter_id = payload.cover_letter_id
    application.resume_version = resume_version.name if resume_version else None
    application.cover_letter_version = cover_letter.name if cover_letter else None
    application.notes = payload.notes

    db.commit()
    db.refresh(application)
    return serialize_application(application, resume_version, cover_letter)
