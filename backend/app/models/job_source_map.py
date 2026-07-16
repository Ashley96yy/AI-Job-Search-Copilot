from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobSourceMap(Base):
    __tablename__ = "job_source_map"
    __table_args__ = (
        UniqueConstraint("raw_job_id", name="uq_job_source_map_raw_job_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    canonical_job_id: Mapped[int] = mapped_column(ForeignKey("canonical_jobs.id"), index=True)
    raw_job_id: Mapped[int] = mapped_column(ForeignKey("raw_jobs.id"), index=True)
    source: Mapped[str] = mapped_column(String(100), index=True)
    external_job_id: Mapped[str] = mapped_column(String(255), index=True)
    match_method: Mapped[str] = mapped_column(String(100), index=True)
    confidence: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
