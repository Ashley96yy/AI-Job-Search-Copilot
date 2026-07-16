from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserJobState(Base):
    __tablename__ = "user_job_states"
    __table_args__ = (
        UniqueConstraint("user_id", "raw_job_id", name="uq_user_job_states_user_job"),
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
    viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    hidden_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
