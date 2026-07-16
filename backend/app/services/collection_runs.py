from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.collection_run import CollectionRun
from app.services.collectors.collector_runner import run_collectors
from app.services.collectors.company_registry import TARGET_COMPANIES
from app.services.raw_jobs import reconcile_missing_jobs, upsert_raw_jobs
from app.services.skill_extraction import extract_skills_for_jobs


def count_requested_boards(
    source: str,
    board_tokens: Optional[list[str]],
) -> int:
    if board_tokens:
        return len(set(board_tokens))

    return len(
        [company for company in TARGET_COMPANIES if company["source"] == source]
    )


async def execute_collection_run(
    db: Session,
    source: str,
    board_tokens: Optional[list[str]] = None,
    keywords: Optional[list[str]] = None,
    max_jobs_per_board: int = 100,
    trigger: str = "manual",
) -> CollectionRun:
    run = CollectionRun(
        source=source,
        trigger=trigger,
        status="running",
        boards_requested=count_requested_boards(source, board_tokens),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    run_id = run.id

    try:
        collector_result = await run_collectors(
            source=source,
            board_tokens=board_tokens,
            keywords=keywords,
            max_jobs_per_board=max_jobs_per_board,
        )
        upsert_result = upsert_raw_jobs(
            db,
            collector_result.jobs,
            commit=False,
        )
        reconciliation_result = reconcile_missing_jobs(
            db,
            collector_result.board_scopes,
            commit=False,
        )
        extract_skills_for_jobs(db, upsert_result.job_ids, commit=False)

        run = db.get(CollectionRun, run_id)
        run.status = "success"
        run.completed_at = datetime.utcnow()
        run.boards_completed = len(collector_result.board_scopes)
        run.boards_reconciled = reconciliation_result.boards_reconciled
        run.fetched = len(collector_result.jobs)
        run.inserted = upsert_result.inserted
        run.updated = upsert_result.updated
        run.reactivated = upsert_result.reactivated
        run.missing_observations = reconciliation_result.missing_observations
        run.closed = reconciliation_result.closed
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:
        db.rollback()
        run = db.get(CollectionRun, run_id)
        run.status = "failed"
        run.completed_at = datetime.utcnow()
        run.error_message = str(exc)[:2000]
        db.commit()
        db.refresh(run)
        return run
