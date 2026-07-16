from __future__ import annotations

from datetime import date, datetime
from math import ceil
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class FitScoreDimension(BaseModel):
    key: str
    label: str
    score: int
    max_score: int
    explanation: str


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_user_id: Optional[int] = None
    is_user_added: bool = False
    source: str
    source_board_token: Optional[str] = None
    external_job_id: str
    company: Optional[str] = None
    title: str
    location: Optional[str] = None
    job_url: Optional[str] = None
    apply_url: Optional[str] = None
    date_posted: Optional[datetime] = None
    posting_age_days: Optional[int] = None
    freshness_bucket: str = "Unknown"
    date_collected: datetime
    first_seen_at: datetime
    last_seen_at: datetime
    is_active: bool = True
    missed_collection_count: int = 0
    closed_at: Optional[datetime] = None
    normalized_company: Optional[str] = None
    normalized_title: Optional[str] = None
    normalized_location: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    is_us_based: bool = False
    work_mode: Optional[str] = None
    seniority: Optional[str] = None
    entry_fit_level: Optional[str] = None
    entry_fit_score: int = 0
    entry_fit_reasons: Optional[str] = None
    required_experience_years: Optional[int] = None
    career_eligible: bool = True
    career_eligibility_reason: Optional[str] = None
    role_category: Optional[str] = None
    target_relevance_score: int = 0
    fit_score: Optional[int] = None
    match_level: Optional[str] = None
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    matched_required_skills: list[str] = Field(default_factory=list)
    missing_required_skills: list[str] = Field(default_factory=list)
    matched_preferred_skills: list[str] = Field(default_factory=list)
    missing_preferred_skills: list[str] = Field(default_factory=list)
    fit_breakdown: list[FitScoreDimension] = Field(default_factory=list)
    fit_notes: list[str] = Field(default_factory=list)


class JobSkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill: str
    category: str
    requirement_level: str = "mentioned"
    evidence_snippet: Optional[str] = None


class JobDetail(JobRead):
    description: Optional[str] = None
    skills: list[JobSkillRead] = Field(default_factory=list)


class PaginatedJobs(BaseModel):
    items: list[JobRead]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[JobRead],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedJobs":
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=ceil(total / page_size) if total else 0,
        )


class ManualJobCreate(BaseModel):
    source: Literal["linkedin", "handshake", "other"]
    company: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=500)
    location: Optional[str] = Field(default=None, max_length=500)
    job_url: Optional[str] = None
    description: Optional[str] = None
    date_posted: Optional[date] = None


class DistributionItem(BaseModel):
    name: str
    count: int


class DeduplicationSummary(BaseModel):
    raw_jobs: int
    canonical_jobs: int
    duplicate_jobs: int
    duplicate_rate: float
    mapped_jobs: int


class MarketSummary(BaseModel):
    total_jobs: int
    us_jobs: int
    canonical_jobs: int
    duplicate_rate: float
    remote_jobs: int
    companies: int
    new_jobs_this_week: int
    new_jobs_last_week: int
    week_over_week_change: Optional[float] = None
    active_weeks: int
    top_role_category: Optional[str] = None
    role_categories: list[DistributionItem]
    work_modes: list[DistributionItem]
    seniorities: list[DistributionItem]
    top_skills: list[DistributionItem]
    top_locations: list[DistributionItem]
    top_states: list[DistributionItem]
    weekly_postings: list[DistributionItem]
