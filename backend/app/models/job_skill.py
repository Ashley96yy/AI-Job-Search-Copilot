from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobSkill(Base):
    __tablename__ = "job_skills"
    __table_args__ = (
        UniqueConstraint("raw_job_id", "skill", name="uq_job_skills_raw_job_skill"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    raw_job_id: Mapped[int] = mapped_column(ForeignKey("raw_jobs.id"), index=True)
    skill: Mapped[str] = mapped_column(String(100), index=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    requirement_level: Mapped[str] = mapped_column(
        String(50),
        default="mentioned",
        index=True,
    )
    evidence_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
