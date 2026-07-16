import hashlib
from datetime import datetime
from typing import Any, Optional

import httpx

from app.services.collectors.base_collector import CollectedJob


LEVER_API_BASE_URL = "https://api.lever.co/v0/postings"


class LeverCollector:
    source = "lever"

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
        url = f"{LEVER_API_BASE_URL}/{self.board_token}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params={"mode": "json"})
            response.raise_for_status()
            data = response.json()

        return data if isinstance(data, list) else []

    def _normalize_job(self, job: dict[str, Any]) -> CollectedJob:
        title = str(job.get("text") or "").strip()
        categories = job.get("categories") or {}
        location = self._get_location(categories)
        company = self.company_name or self.board_token
        description = self._get_description(job)
        job_url = job.get("hostedUrl")
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
            description=description,
            date_posted=self._parse_datetime(job.get("createdAt")),
            raw_json=job,
            content_hash=self._content_hash(company, title, location, description),
        )

    @staticmethod
    def _get_location(categories: dict[str, Any]) -> Optional[str]:
        location = categories.get("location")
        return str(location).strip() if location else None

    @staticmethod
    def _get_description(job: dict[str, Any]) -> Optional[str]:
        content = job.get("content") or {}
        parts = [
            str(content.get("descriptionHtml") or content.get("description") or ""),
        ]

        for list_item in content.get("lists") or []:
            parts.append(str(list_item.get("text") or ""))
            parts.extend(str(item) for item in list_item.get("content") or [])

        description = " ".join(part for part in parts if part).strip()
        return description or None

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if value is None:
            return None

        try:
            timestamp_seconds = int(value) / 1000
        except (TypeError, ValueError):
            return None

        return datetime.fromtimestamp(timestamp_seconds)

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
        categories = job.get("categories") or {}
        content = job.get("content") or {}
        searchable_parts = [
            str(job.get("text") or ""),
            str(categories.get("team") or ""),
            str(categories.get("department") or ""),
            str(categories.get("location") or ""),
            str(content.get("description") or ""),
            str(content.get("descriptionHtml") or ""),
        ]

        for list_item in content.get("lists") or []:
            searchable_parts.append(str(list_item.get("text") or ""))
            searchable_parts.extend(str(item) for item in list_item.get("content") or [])

        haystack = " ".join(searchable_parts).lower()
        return any(keyword.lower() in haystack for keyword in keywords)
