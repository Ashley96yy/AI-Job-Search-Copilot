from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CollectJobsRequest(BaseModel):
    source: str = "greenhouse"
    board_tokens: Optional[list[str]] = None
    keywords: Optional[list[str]] = None
    max_jobs_per_board: int = Field(default=100, ge=1, le=250)


class CollectJobsResponse(BaseModel):
    source: str
    boards_requested: int
    fetched: int
    matched: int
    inserted: int
    updated: int
    reactivated: int = 0
    boards_reconciled: int = 0
    missing_observations: int = 0
    closed: int = 0


class SyncAllJobsRequest(BaseModel):
    max_jobs_per_board: int = Field(default=100, ge=1, le=250)


class CollectionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    trigger: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    boards_requested: int = 0
    boards_completed: int = 0
    boards_reconciled: int = 0
    fetched: int = 0
    inserted: int = 0
    updated: int = 0
    reactivated: int = 0
    missing_observations: int = 0
    closed: int = 0
    error_message: Optional[str] = None


class CompanySource(BaseModel):
    name: str
    source: str
    board_token: str
    category: str
