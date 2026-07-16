from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProfileSkill(BaseModel):
    skill: str
    category: str


class UserProfileBase(BaseModel):
    name: Optional[str] = None
    resume_text: str = ""
    target_roles: Optional[str] = None
    target_locations: Optional[str] = None


class UserProfileUpsert(UserProfileBase):
    pass


class ProfileFromResumeVersion(BaseModel):
    resume_version_id: int
    name: Optional[str] = None
    target_roles: Optional[str] = None
    target_locations: Optional[str] = None


class UserProfileSkillUpdate(ProfileSkill):
    pass


class WorkExperienceItem(BaseModel):
    company: str
    title: str
    period: Optional[str] = None
    location: Optional[str] = None
    bullets: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    school: str
    degree: Optional[str] = None
    period: Optional[str] = None


class DomainExperienceItem(BaseModel):
    domain: str
    evidence: list[str] = Field(default_factory=list)


class UserProfileRead(UserProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    source_resume_version_id: Optional[int] = None
    extracted_skills: list[ProfileSkill] = Field(default_factory=list)
    manual_skills: list[ProfileSkill] = Field(default_factory=list)
    work_experience: list[WorkExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    domain_experience: list[DomainExperienceItem] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SkillGapItem(BaseModel):
    skill: str
    category: str
    missing_count: int


class SkillGapByRole(BaseModel):
    role_category: str
    analyzed_jobs_count: int
    top_missing_skills: list[SkillGapItem] = Field(default_factory=list)


class SkillGapSummary(BaseModel):
    profile_exists: bool
    profile_skills_count: int
    analyzed_jobs_count: int
    top_missing_skills: list[SkillGapItem] = Field(default_factory=list)
    gaps_by_role: list[SkillGapByRole] = Field(default_factory=list)
