from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CoverLetter(Base):
    __tablename__ = "cover_letters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=1, index=True)
    raw_job_id: Mapped[int] = mapped_column(ForeignKey("raw_jobs.id"), index=True)
    resume_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    draft: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    matched_keywords_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    caveats_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
