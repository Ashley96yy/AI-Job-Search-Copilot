from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ApplicationBase(BaseModel):
    status: str = "saved"
    applied_date: Optional[date] = None
    follow_up_date: Optional[date] = None
    resume_version_id: Optional[int] = None
    cover_letter_id: Optional[int] = None
    notes: Optional[str] = None


class ApplicationUpsert(ApplicationBase):
    raw_job_id: int


class ApplicationRead(ApplicationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    raw_job_id: int
    resume_version: Optional[str] = None
    cover_letter_version: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ApplicationWithJob(ApplicationRead):
    company: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    job_url: Optional[str] = None
    role_category: Optional[str] = None
