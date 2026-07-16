from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RawJob(Base):
    __tablename__ = "raw_jobs"
    __table_args__ = (
        UniqueConstraint("source", "external_job_id", name="uq_raw_jobs_source_external_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    is_user_added: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    source: Mapped[str] = mapped_column(String(100), index=True)
    source_board_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    external_job_id: Mapped[str] = mapped_column(String(255), index=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(500))
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    job_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    apply_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    date_posted: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    date_collected: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    missed_collection_count: Mapped[int] = mapped_column(Integer, default=0)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    normalized_company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    normalized_title: Mapped[Optional[str]] = mapped_column(String(500), index=True, nullable=True)
    normalized_location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    is_us_based: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    work_mode: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    seniority: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    entry_fit_level: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    entry_fit_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    entry_fit_reasons: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    required_experience_years: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )
    career_eligible: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    career_eligibility_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role_category: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    target_relevance_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
