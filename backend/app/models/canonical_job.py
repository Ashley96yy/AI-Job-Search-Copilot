from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CanonicalJob(Base):
    __tablename__ = "canonical_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fingerprint: Mapped[str] = mapped_column(String(700), unique=True, index=True)
    representative_raw_job_id: Mapped[int] = mapped_column(Integer, index=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(500))
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    job_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    apply_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date_posted: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime)
    last_seen: Mapped[datetime] = mapped_column(DateTime)
    source_count: Mapped[int] = mapped_column(Integer, default=1)
    raw_job_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
