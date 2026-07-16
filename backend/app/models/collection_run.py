from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CollectionRun(Base):
    __tablename__ = "collection_runs"
    __table_args__ = (
        Index(
            "uq_collection_runs_running_source",
            "source",
            unique=True,
            sqlite_where=text("status = 'running'"),
            postgresql_where=text("status = 'running'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(100), index=True)
    trigger: Mapped[str] = mapped_column(String(50), default="manual", index=True)
    status: Mapped[str] = mapped_column(String(50), default="running", index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )
    heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    boards_requested: Mapped[int] = mapped_column(Integer, default=0)
    boards_completed: Mapped[int] = mapped_column(Integer, default=0)
    boards_reconciled: Mapped[int] = mapped_column(Integer, default=0)
    fetched: Mapped[int] = mapped_column(Integer, default=0)
    inserted: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[int] = mapped_column(Integer, default=0)
    reactivated: Mapped[int] = mapped_column(Integer, default=0)
    missing_observations: Mapped[int] = mapped_column(Integer, default=0)
    closed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    board_runs: Mapped[list["CollectionBoardRun"]] = relationship(
        "CollectionBoardRun",
        back_populates="collection_run",
        cascade="all, delete-orphan",
        order_by="CollectionBoardRun.id",
    )
