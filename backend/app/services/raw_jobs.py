import json
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.raw_job import RawJob
from app.services.collectors.base_collector import CollectedJob
from app.services.collectors.collector_runner import BoardSyncScope
from app.services.job_cleaning import apply_cleaned_fields


@dataclass
class UpsertResult:
    inserted: int = 0
    updated: int = 0
    reactivated: int = 0
    job_ids: list[int] = field(default_factory=list)


@dataclass
class ReconciliationResult:
    boards_reconciled: int = 0
    missing_observations: int = 0
    closed: int = 0


def upsert_raw_jobs(
    db: Session,
    jobs: list[CollectedJob],
    commit: bool = True,
) -> UpsertResult:
    result = UpsertResult()
    seen_at = datetime.utcnow()
    processed_jobs: list[RawJob] = []

    for job in jobs:
        existing = db.scalar(
            select(RawJob).where(
                RawJob.source == job.source,
                RawJob.external_job_id == job.external_job_id,
            )
        )

        raw_json = json.dumps(job.raw_json, ensure_ascii=False) if job.raw_json else None

        if existing:
            if not existing.is_active:
                result.reactivated += 1
            existing.source_board_token = job.source_board_token
            existing.company = job.company
            existing.title = job.title
            existing.location = job.location
            existing.job_url = job.job_url
            existing.apply_url = job.apply_url
            existing.description = job.description
            existing.date_posted = job.date_posted
            existing.raw_json = raw_json
            existing.content_hash = job.content_hash
            existing.last_seen_at = seen_at
            existing.is_active = True
            existing.missed_collection_count = 0
            existing.closed_at = None
            apply_cleaned_fields(existing)
            processed_jobs.append(existing)
            result.updated += 1
            continue

        raw_job = RawJob(
            source=job.source,
            source_board_token=job.source_board_token,
            external_job_id=job.external_job_id,
            company=job.company,
            title=job.title,
            location=job.location,
            job_url=job.job_url,
            apply_url=job.apply_url,
            description=job.description,
            date_posted=job.date_posted,
            raw_json=raw_json,
            content_hash=job.content_hash,
            first_seen_at=seen_at,
            last_seen_at=seen_at,
            is_active=True,
            missed_collection_count=0,
        )
        apply_cleaned_fields(raw_job)
        db.add(raw_job)
        processed_jobs.append(raw_job)
        result.inserted += 1

    db.flush()
    result.job_ids = [job.id for job in processed_jobs]
    if commit:
        db.commit()
    return result


def reconcile_missing_jobs(
    db: Session,
    board_scopes: list[BoardSyncScope],
    close_after_misses: int = 2,
    commit: bool = True,
) -> ReconciliationResult:
    result = ReconciliationResult()
    reconciled_at = datetime.utcnow()

    for scope in board_scopes:
        if not scope.can_reconcile:
            continue

        result.boards_reconciled += 1
        jobs = list(
            db.scalars(
                select(RawJob).where(
                    RawJob.source == scope.source,
                    RawJob.source_board_token == scope.board_token,
                    RawJob.is_user_added.is_(False),
                )
            ).all()
        )

        for job in jobs:
            if job.external_job_id in scope.seen_external_job_ids:
                continue

            job.missed_collection_count += 1
            result.missing_observations += 1

            if job.is_active and job.missed_collection_count >= close_after_misses:
                job.is_active = False
                job.closed_at = reconciled_at
                result.closed += 1

    if commit:
        db.commit()
    else:
        db.flush()
    return result
