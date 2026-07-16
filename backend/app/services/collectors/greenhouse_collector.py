import hashlib
from datetime import datetime
from typing import Any, Optional

import httpx

from app.services.collectors.base_collector import CollectedJob


GREENHOUSE_API_BASE_URL = "https://boards-api.greenhouse.io/v1/boards"


class GreenhouseCollector:
    source = "greenhouse"

    def __init__(
        self,
        board_token: str,
        company_name: Optional[str] = None,
        max_jobs: int = 25,
    ) -> None:
        self.board_token = board_token
        self.company_name = company_name
        self.max_jobs = max_jobs
        self.is_exhaustive = False

    async def collect(self, keywords: Optional[list[str]] = None) -> list[CollectedJob]:
        jobs = await self._fetch_jobs()
        self.is_exhaustive = len(jobs) <= self.max_jobs
        normalized_jobs: list[CollectedJob] = []

        for job in jobs:
            if keywords and not self._matches_keywords(job, keywords):
                continue

            normalized_jobs.append(self._normalize_job(job))

            if len(normalized_jobs) >= self.max_jobs:
                break

        return normalized_jobs

    async def _fetch_jobs(self) -> list[dict[str, Any]]:
        url = f"{GREENHOUSE_API_BASE_URL}/{self.board_token}/jobs"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params={"content": "true"})
            response.raise_for_status()
            data = response.json()

        return data.get("jobs", [])

    def _normalize_job(self, job: dict[str, Any]) -> CollectedJob:
        title = str(job.get("title") or "").strip()
        location = self._get_location(job)
        company = job.get("company_name") or self.company_name or self.board_token
        description = job.get("content")
        absolute_url = job.get("absolute_url")
        external_job_id = str(job.get("id"))

        return CollectedJob(
            source=self.source,
            source_board_token=self.board_token,
            external_job_id=external_job_id,
            title=title,
            company=company,
            location=location,
            job_url=absolute_url,
            apply_url=absolute_url,
            description=description,
            date_posted=self._parse_datetime(job.get("first_published") or job.get("updated_at")),
            raw_json=job,
            content_hash=self._content_hash(company, title, location, description),
        )

    @staticmethod
    def _get_location(job: dict[str, Any]) -> Optional[str]:
        location = job.get("location")
        if isinstance(location, dict):
            name = location.get("name")
            return str(name).strip() if name else None
        return None

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if not value:
            return None

        if not isinstance(value, str):
            return None

        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _content_hash(
        company: Optional[str],
        title: Optional[str],
        location: Optional[str],
        description: Optional[str],
    ) -> str:
        content = " | ".join(
            [
                company or "",
                title or "",
                location or "",
                description or "",
            ]
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _matches_keywords(job: dict[str, Any], keywords: list[str]) -> bool:
        searchable_parts = [
            str(job.get("title") or ""),
            str(job.get("content") or ""),
            str(job.get("company_name") or ""),
        ]

        for department in job.get("departments") or []:
            searchable_parts.append(str(department.get("name") or ""))

        haystack = " ".join(searchable_parts).lower()
        return any(keyword.lower() in haystack for keyword in keywords)
