from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.application import Application
from app.models.cover_letter import CoverLetter
from app.models.raw_job import RawJob
from app.models.resume_version import ResumeVersion
from app.schemas.cover_letter import CoverLetterRead, CoverLetterUpsert


router = APIRouter(prefix="/cover-letters", tags=["cover letters"])
DEFAULT_USER_ID = 1


def parse_list(value: str | None) -> list[str]:
    if not value:
        return []

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []

    return [item for item in parsed if isinstance(item, str)] if isinstance(parsed, list) else []


def serialize_cover_letter(
    cover_letter: CoverLetter,
    job: RawJob,
    resume_version: ResumeVersion | None,
) -> CoverLetterRead:
    return CoverLetterRead(
        id=cover_letter.id,
        user_id=cover_letter.user_id,
        name=cover_letter.name,
        raw_job_id=cover_letter.raw_job_id,
        resume_version_id=cover_letter.resume_version_id,
        draft=cover_letter.draft,
        evidence=parse_list(cover_letter.evidence_json),
        matched_keywords=parse_list(cover_letter.matched_keywords_json),
        caveats=parse_list(cover_letter.caveats_json),
        company=job.company,
        job_title=job.title,
        resume_version_name=resume_version.name if resume_version else None,
        created_at=cover_letter.created_at,
        updated_at=cover_letter.updated_at,
    )


def get_job_and_resume(
    payload: CoverLetterUpsert,
    db: Session,
) -> tuple[RawJob, ResumeVersion | None]:
    job = db.get(RawJob, payload.raw_job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

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

    return job, resume_version


@router.get("", response_model=list[CoverLetterRead])
def list_cover_letters(db: Session = Depends(get_db)) -> list[CoverLetterRead]:
    rows = db.execute(
        select(CoverLetter, RawJob, ResumeVersion)
        .join(RawJob, CoverLetter.raw_job_id == RawJob.id)
        .outerjoin(ResumeVersion, CoverLetter.resume_version_id == ResumeVersion.id)
        .where(CoverLetter.user_id == DEFAULT_USER_ID)
        .order_by(CoverLetter.updated_at.desc())
    ).all()
    return [serialize_cover_letter(letter, job, resume) for letter, job, resume in rows]


@router.post("", response_model=CoverLetterRead)
def create_cover_letter(
    payload: CoverLetterUpsert,
    db: Session = Depends(get_db),
) -> CoverLetterRead:
    job, resume_version = get_job_and_resume(payload, db)
    cover_letter = CoverLetter(
        user_id=DEFAULT_USER_ID,
        raw_job_id=payload.raw_job_id,
        resume_version_id=payload.resume_version_id,
        name=payload.name.strip(),
        draft=payload.draft.strip(),
        evidence_json=json.dumps(payload.evidence),
        matched_keywords_json=json.dumps(payload.matched_keywords),
        caveats_json=json.dumps(payload.caveats),
    )
    db.add(cover_letter)
    db.commit()
    db.refresh(cover_letter)
    return serialize_cover_letter(cover_letter, job, resume_version)


@router.put("/{cover_letter_id}", response_model=CoverLetterRead)
def update_cover_letter(
    cover_letter_id: int,
    payload: CoverLetterUpsert,
    db: Session = Depends(get_db),
) -> CoverLetterRead:
    cover_letter = db.scalar(
        select(CoverLetter).where(
            CoverLetter.id == cover_letter_id,
            CoverLetter.user_id == DEFAULT_USER_ID,
        )
    )
    if not cover_letter:
        raise HTTPException(status_code=404, detail="Cover letter not found.")

    job, resume_version = get_job_and_resume(payload, db)
    cover_letter.raw_job_id = payload.raw_job_id
    cover_letter.resume_version_id = payload.resume_version_id
    cover_letter.name = payload.name.strip()
    cover_letter.draft = payload.draft.strip()
    cover_letter.evidence_json = json.dumps(payload.evidence)
    cover_letter.matched_keywords_json = json.dumps(payload.matched_keywords)
    cover_letter.caveats_json = json.dumps(payload.caveats)
    db.commit()
    db.refresh(cover_letter)
    return serialize_cover_letter(cover_letter, job, resume_version)


@router.delete("/{cover_letter_id}")
def delete_cover_letter(
    cover_letter_id: int,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    cover_letter = db.scalar(
        select(CoverLetter).where(
            CoverLetter.id == cover_letter_id,
            CoverLetter.user_id == DEFAULT_USER_ID,
        )
    )
    if not cover_letter:
        raise HTTPException(status_code=404, detail="Cover letter not found.")

    db.execute(
        update(Application)
        .where(Application.cover_letter_id == cover_letter_id)
        .values(cover_letter_id=None, cover_letter_version=None)
    )
    db.delete(cover_letter)
    db.commit()
    return {"status": "deleted"}
