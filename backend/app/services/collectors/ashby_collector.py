import hashlib
from datetime import datetime
from typing import Any, Optional

import httpx

from app.services.collectors.base_collector import CollectedJob


ASHBY_API_BASE_URL = "https://api.ashbyhq.com/posting-api/job-board"


class AshbyCollector:
    source = "ashby"

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
        jobs = [job for job in await self._fetch_jobs() if job.get("isListed") is not False]
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
        url = f"{ASHBY_API_BASE_URL}/{self.board_token}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params={"includeCompensation": "true"})
            response.raise_for_status()
            data = response.json()

        jobs = data.get("jobs", []) if isinstance(data, dict) else []
        return jobs if isinstance(jobs, list) else []

    def _normalize_job(self, job: dict[str, Any]) -> CollectedJob:
        title = str(job.get("title") or "").strip()
        company = self.company_name or self.board_token
        location = self._get_location(job)
        description = job.get("descriptionPlain") or job.get("descriptionHtml")
        job_url = job.get("jobUrl")
        apply_url = job.get("applyUrl") or job_url
        external_job_id = str(job.get("id") or job_url or title)

        return CollectedJob(
            source=self.source,
            source_board_token=self.board_token,
            external_job_id=external_job_id,
            title=title,
            company=company,
            location=location,
            job_url=job_url,
            apply_url=apply_url,
            description=str(description).strip() if description else None,
            date_posted=self._parse_datetime(job.get("publishedAt")),
            raw_json=job,
            content_hash=self._content_hash(company, title, location, description),
        )

    @staticmethod
    def _get_location(job: dict[str, Any]) -> Optional[str]:
        locations: list[str] = []
        primary_location = str(job.get("location") or "").strip()
        if primary_location:
            locations.append(primary_location)

        for secondary in job.get("secondaryLocations") or []:
            if not isinstance(secondary, dict):
                continue
            location = str(secondary.get("location") or "").strip()
            if location and location not in locations:
                locations.append(location)

        workplace_type = str(job.get("workplaceType") or "").strip()
        if workplace_type and not any(
            workplace_type.lower() in location.lower() for location in locations
        ):
            locations.append(workplace_type)

        return " | ".join(locations) or None

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if not isinstance(value, str) or not value:
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
        description: Any,
    ) -> str:
        content = " | ".join(
            [
                company or "",
                title or "",
                location or "",
                str(description or ""),
            ]
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _matches_keywords(job: dict[str, Any], keywords: list[str]) -> bool:
        searchable_parts = [
            str(job.get("title") or ""),
            str(job.get("department") or ""),
            str(job.get("team") or ""),
            str(job.get("location") or ""),
            str(job.get("descriptionPlain") or ""),
            str(job.get("descriptionHtml") or ""),
        ]
        searchable_parts.extend(
            str(location.get("location") or "")
            for location in job.get("secondaryLocations") or []
            if isinstance(location, dict)
        )
        haystack = " ".join(searchable_parts).lower()
        return any(keyword.lower() in haystack for keyword in keywords)
