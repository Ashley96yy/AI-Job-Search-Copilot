from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pypdf import PdfReader
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.application import Application
from app.models.cover_letter import CoverLetter
from app.models.resume_version import ResumeVersion
from app.models.user_profile import UserProfile
from app.schemas.resume_version import ResumeVersionRead, ResumeVersionUpsert


router = APIRouter(prefix="/resume-versions", tags=["resume versions"])
DEFAULT_USER_ID = 1
MAX_RESUME_FILE_SIZE_BYTES = 5 * 1024 * 1024
SUPPORTED_RESUME_EXTENSIONS = {".pdf", ".txt", ".md"}


def file_extension(filename: Optional[str]) -> str:
    if not filename or "." not in filename:
        return ""

    return f".{filename.rsplit('.', maxsplit=1)[-1].lower()}"


def extract_text_from_resume_file(filename: Optional[str], content: bytes) -> str:
    extension = file_extension(filename)

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


@router.get("", response_model=list[ResumeVersionRead])
def list_resume_versions(db: Session = Depends(get_db)) -> list[ResumeVersion]:
    return list(
        db.scalars(
            select(ResumeVersion)
            .where(ResumeVersion.user_id == DEFAULT_USER_ID)
            .order_by(ResumeVersion.updated_at.desc())
        ).all()
    )


@router.post("/parse-upload")
async def parse_resume_upload(file: UploadFile = File(...)) -> dict[str, str]:
    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded resume file is empty.")

    if len(content) > MAX_RESUME_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Resume file must be 5 MB or smaller.")

    resume_text = extract_text_from_resume_file(file.filename, content).strip()
    if not resume_text:
        raise HTTPException(
            status_code=400,
            detail="No readable resume text was found in this file.",
        )

    return {
        "filename": file.filename or "resume",
        "resume_text": resume_text,
    }


@router.post("", response_model=ResumeVersionRead)
def create_resume_version(
    payload: ResumeVersionUpsert,
    db: Session = Depends(get_db),
) -> ResumeVersion:
    existing = db.scalar(
        select(ResumeVersion).where(
            ResumeVersion.user_id == DEFAULT_USER_ID,
            ResumeVersion.name == payload.name,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Resume version name already exists.")

    resume_version = ResumeVersion(
        user_id=DEFAULT_USER_ID,
        name=payload.name,
        target_role=payload.target_role,
        resume_text=payload.resume_text,
        notes=payload.notes,
    )
    db.add(resume_version)
    db.commit()
    db.refresh(resume_version)
    return resume_version


@router.put("/{resume_version_id}", response_model=ResumeVersionRead)
def update_resume_version(
    resume_version_id: int,
    payload: ResumeVersionUpsert,
    db: Session = Depends(get_db),
) -> ResumeVersion:
    resume_version = db.scalar(
        select(ResumeVersion).where(
            ResumeVersion.id == resume_version_id,
            ResumeVersion.user_id == DEFAULT_USER_ID,
        )
    )
    if not resume_version:
        raise HTTPException(status_code=404, detail="Resume version not found.")

    duplicate = db.scalar(
        select(ResumeVersion).where(
            ResumeVersion.user_id == DEFAULT_USER_ID,
            ResumeVersion.name == payload.name,
            ResumeVersion.id != resume_version_id,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Resume version name already exists.")

    resume_version.name = payload.name
    resume_version.target_role = payload.target_role
    resume_version.resume_text = payload.resume_text
    resume_version.notes = payload.notes

    db.commit()
    db.refresh(resume_version)
    return resume_version


@router.delete("/{resume_version_id}")
def delete_resume_version(
    resume_version_id: int,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    resume_version = db.scalar(
        select(ResumeVersion).where(
            ResumeVersion.id == resume_version_id,
            ResumeVersion.user_id == DEFAULT_USER_ID,
        )
    )
    if not resume_version:
        raise HTTPException(status_code=404, detail="Resume version not found.")

    db.execute(
        update(Application)
        .where(Application.resume_version_id == resume_version_id)
        .values(resume_version_id=None, resume_version=None)
    )
    db.execute(
        update(CoverLetter)
        .where(CoverLetter.resume_version_id == resume_version_id)
        .values(resume_version_id=None)
    )
    db.execute(
        update(UserProfile)
        .where(UserProfile.source_resume_version_id == resume_version_id)
        .values(source_resume_version_id=None)
    )
    db.delete(resume_version)
    db.commit()
    return {"status": "deleted"}
