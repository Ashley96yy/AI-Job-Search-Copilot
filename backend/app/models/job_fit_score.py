from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobFitScore(Base):
    __tablename__ = "job_fit_scores"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "raw_job_id",
            name="uq_job_fit_scores_user_job",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    raw_job_id: Mapped[int] = mapped_column(
        ForeignKey("raw_jobs.id", ondelete="CASCADE"),
        index=True,
    )
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    profile_signature: Mapped[str] = mapped_column(String(64), index=True)
    job_signature: Mapped[str] = mapped_column(String(64), index=True)
    scoring_version: Mapped[str] = mapped_column(String(50), index=True)
    fit_score: Mapped[int] = mapped_column(Integer, index=True)
    match_level: Mapped[str] = mapped_column(String(50), index=True)
    result_json: Mapped[str] = mapped_column(Text)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )
