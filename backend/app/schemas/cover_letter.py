from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CoverLetterUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    raw_job_id: int
    resume_version_id: Optional[int] = None
    draft: str = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list)
    matched_keywords: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class CoverLetterRead(CoverLetterUpsert):
    id: int
    user_id: int
    company: Optional[str] = None
    job_title: str
    resume_version_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
