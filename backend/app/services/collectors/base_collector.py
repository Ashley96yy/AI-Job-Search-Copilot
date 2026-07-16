from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class CollectedJob:
    source: str
    source_board_token: str
    external_job_id: str
    title: str
    company: str | None = None
    location: str | None = None
    job_url: str | None = None
    apply_url: str | None = None
    description: str | None = None
    date_posted: datetime | None = None
    raw_json: dict[str, Any] | None = None
    content_hash: str | None = None


class BaseCollector(ABC):
    source: str

    @abstractmethod
    async def collect(self, keywords: list[str] | None = None) -> list[CollectedJob]:
        """Fetch jobs from a source and normalize them into CollectedJob records."""
