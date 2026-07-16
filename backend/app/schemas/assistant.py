from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ResumeSuggestionRequest(BaseModel):
    raw_job_id: int
    resume_version_id: Optional[int] = None


class CoverLetterRequest(BaseModel):
    raw_job_id: int
    resume_version_id: Optional[int] = None


class ResumeSuggestionItem(BaseModel):
    suggestion_type: str
    title: str
    suggestion: str
    related_keyword: Optional[str] = None
    evidence: list[str] = Field(default_factory=list)
    risk_level: str


class ResumeSuggestionResponse(BaseModel):
    raw_job_id: int
    resume_version_id: Optional[int] = None
    job_title: str
    company: Optional[str] = None
    suggestions: list[ResumeSuggestionItem] = Field(default_factory=list)
    unsupported_keywords: list[str] = Field(default_factory=list)


class CoverLetterResponse(BaseModel):
    raw_job_id: int
    resume_version_id: Optional[int] = None
    job_title: str
    company: Optional[str] = None
    draft: str
    evidence: list[str] = Field(default_factory=list)
    matched_keywords: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
