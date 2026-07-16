from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ResumeVersion(Base):
    __tablename__ = "resume_versions"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_resume_versions_user_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=1, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    target_role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resume_text: Mapped[str] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
