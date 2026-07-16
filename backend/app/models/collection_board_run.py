from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CollectionBoardRun(Base):
    __tablename__ = "collection_board_runs"
    __table_args__ = (
        UniqueConstraint(
            "collection_run_id",
            "board_token",
            name="uq_collection_board_runs_run_token",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    collection_run_id: Mapped[int] = mapped_column(
        ForeignKey("collection_runs.id", ondelete="CASCADE"),
        index=True,
    )
    board_token: Mapped[str] = mapped_column(String(255), index=True)
    company_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    completed_at: Mapped[datetime] = mapped_column(DateTime)
    fetched: Mapped[int] = mapped_column(Integer, default=0)
    can_reconcile: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    collection_run = relationship("CollectionRun", back_populates="board_runs")
