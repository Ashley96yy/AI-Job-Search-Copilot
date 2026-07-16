from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=1, index=True)
    source_resume_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("resume_versions.id"),
        nullable=True,
    )
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resume_text: Mapped[str] = mapped_column(Text)
    target_roles: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_locations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_skills_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manual_skills_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    work_experience_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    education_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    domain_experience_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
