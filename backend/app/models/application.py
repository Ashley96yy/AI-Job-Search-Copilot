from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "raw_job_id", name="uq_applications_user_raw_job_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=1, index=True)
    raw_job_id: Mapped[int] = mapped_column(ForeignKey("raw_jobs.id"), index=True)
    status: Mapped[str] = mapped_column(String(50), default="saved", index=True)
    applied_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    follow_up_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    resume_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cover_letter_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("cover_letters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Retained while migrating older SQLite data; IDs above are authoritative.
    resume_version: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cover_letter_version: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
