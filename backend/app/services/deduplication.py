import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.canonical_job import CanonicalJob
from app.models.job_source_map import JobSourceMap
from app.models.raw_job import RawJob


@dataclass(frozen=True)
class DeduplicationResult:
    raw_jobs: int
    canonical_jobs: int
    duplicate_jobs: int
    duplicate_rate: float
    mapped_jobs: int


def deduplicate_jobs(db: Session) -> DeduplicationResult:
    raw_jobs = list(
        db.scalars(
            select(RawJob)
            .where(
                RawJob.is_user_added.is_(False),
                RawJob.is_active.is_(True),
            )
            .order_by(RawJob.id)
        ).all()
    )

    db.execute(delete(JobSourceMap))
    db.execute(delete(CanonicalJob))

    grouped_jobs: dict[str, list[tuple[RawJob, str, int]]] = {}

    for job in raw_jobs:
        fingerprint, match_method, confidence = build_fingerprint(job)
        grouped_jobs.setdefault(fingerprint, []).append((job, match_method, confidence))

    mapped_jobs = 0

    for fingerprint, group in grouped_jobs.items():
        jobs = [item[0] for item in group]
        representative = choose_representative_job(jobs)
        canonical_job = CanonicalJob(
            fingerprint=fingerprint,
            representative_raw_job_id=representative.id,
            company=representative.normalized_company or representative.company,
            title=representative.normalized_title or representative.title,
            location=representative.normalized_location or representative.location,
            job_url=representative.job_url,
            apply_url=representative.apply_url,
            date_posted=representative.date_posted,
            first_seen=min(job.first_seen_at for job in jobs),
            last_seen=max(job.last_seen_at for job in jobs),
            source_count=len({job.source for job in jobs}),
            raw_job_count=len(jobs),
        )
        db.add(canonical_job)
        db.flush()

        for job, match_method, confidence in group:
            db.add(
                JobSourceMap(
                    canonical_job_id=canonical_job.id,
                    raw_job_id=job.id,
                    source=job.source,
                    external_job_id=job.external_job_id,
                    match_method=match_method,
                    confidence=confidence,
                )
            )
            mapped_jobs += 1

    db.commit()

    raw_count = len(raw_jobs)
    canonical_count = len(grouped_jobs)
    duplicate_count = max(raw_count - canonical_count, 0)
    duplicate_rate = round(duplicate_count / raw_count, 4) if raw_count else 0.0

    return DeduplicationResult(
        raw_jobs=raw_count,
        canonical_jobs=canonical_count,
        duplicate_jobs=duplicate_count,
        duplicate_rate=duplicate_rate,
        mapped_jobs=mapped_jobs,
    )


def build_fingerprint(job: RawJob) -> tuple[str, str, int]:
    normalized_apply_url = normalize_url(job.apply_url)
    if normalized_apply_url:
        return f"apply_url:{hash_text(normalized_apply_url)}", "apply_url", 100

    normalized_company = normalize_text(job.normalized_company or job.company)
    normalized_title = normalize_text(job.normalized_title or job.title)
    normalized_location = normalize_text(job.normalized_location or job.location)

    if normalized_company and normalized_title:
        fingerprint = "|".join(
            [
                normalized_company,
                normalized_title,
                normalized_location or "unknown_location",
            ]
        )
        return f"normalized_fields:{fingerprint}", "normalized_fingerprint", 90

    return f"raw_job:{job.source}:{job.external_job_id}", "source_external_id", 80


def choose_representative_job(jobs: list[RawJob]) -> RawJob:
    return sorted(
        jobs,
        key=lambda job: (
            job.date_posted or datetime.min,
            job.date_collected,
            job.id,
        ),
        reverse=True,
    )[0]


def normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""

    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_url(value: Optional[str]) -> str:
    if not value:
        return ""

    normalized = value.strip().lower()
    normalized = normalized.split("#", maxsplit=1)[0]
    normalized = normalized.rstrip("/")
    return normalized


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def count_canonical_jobs(
    db: Session,
    raw_job_filters: Optional[list] = None,
) -> int:
    statement = (
        select(func.count(func.distinct(JobSourceMap.canonical_job_id)))
        .join(RawJob, JobSourceMap.raw_job_id == RawJob.id)
    )

    if raw_job_filters:
        statement = statement.where(*raw_job_filters)

    return db.scalar(statement) or 0
