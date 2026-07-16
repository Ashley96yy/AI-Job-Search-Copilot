from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.collection_board_run import CollectionBoardRun
from app.models.collection_run import CollectionRun
from app.services.collectors.collector_runner import run_collectors
from app.services.collectors.collector_runner import BoardCollectionResult
from app.services.collectors.company_registry import TARGET_COMPANIES
from app.services.raw_jobs import reconcile_missing_jobs, upsert_raw_jobs
from app.services.skill_extraction import extract_skills_for_jobs


RUN_TIMEOUT_MINUTES = 10


class CollectionRunConflict(Exception):
    def __init__(self, active_run: CollectionRun) -> None:
        self.active_run = active_run
        super().__init__(
            f"{active_run.source} collection run {active_run.id} is already running."
        )


class CollectionRunInterrupted(Exception):
    pass


def recover_stale_collection_runs(
    db: Session,
    timeout_minutes: int = RUN_TIMEOUT_MINUTES,
) -> int:
    cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
    stale_runs = list(
        db.scalars(
            select(CollectionRun).where(
                CollectionRun.status == "running",
                CollectionRun.heartbeat_at < cutoff,
            )
        ).all()
    )
    if not stale_runs:
        return 0

    completed_at = datetime.utcnow()
    for run in stale_runs:
        run.status = "failed"
        run.completed_at = completed_at
        run.error_message = (
            f"Interrupted or no heartbeat received for more than "
            f"{timeout_minutes} minutes."
        )

    db.commit()
    return len(stale_runs)


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
    recover_stale_collection_runs(db)
    started_at = datetime.utcnow()
    run = CollectionRun(
        source=source,
        trigger=trigger,
        status="running",
        started_at=started_at,
        heartbeat_at=started_at,
        boards_requested=count_requested_boards(source, board_tokens),
    )
    db.add(run)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        active_run = db.scalar(
            select(CollectionRun)
            .where(
                CollectionRun.source == source,
                CollectionRun.status == "running",
            )
            .order_by(CollectionRun.started_at.desc())
            .limit(1)
        )
        if active_run:
            raise CollectionRunConflict(active_run) from exc
        raise
    db.refresh(run)
    run_id = run.id

    try:
        def report_board_progress(board_result: BoardCollectionResult) -> None:
            progress_run = db.get(CollectionRun, run_id)
            db.refresh(progress_run)
            if progress_run.status != "running":
                raise CollectionRunInterrupted(
                    f"Collection run {run_id} is no longer active."
                )
            db.add(
                CollectionBoardRun(
                    collection_run_id=run_id,
                    board_token=board_result.board_token,
                    company_name=board_result.company_name,
                    status=board_result.status,
                    started_at=board_result.started_at,
                    completed_at=board_result.completed_at,
                    fetched=board_result.fetched,
                    can_reconcile=board_result.can_reconcile,
                    error_message=board_result.error_message,
                )
            )
            progress_run.boards_completed += 1
            progress_run.heartbeat_at = datetime.utcnow()
            db.commit()

        collector_result = await run_collectors(
            source=source,
            board_tokens=board_tokens,
            keywords=keywords,
            max_jobs_per_board=max_jobs_per_board,
            on_board_complete=report_board_progress,
        )
        run = db.get(CollectionRun, run_id)
        db.refresh(run)
        if run.status != "running":
            raise CollectionRunInterrupted(
                f"Collection run {run_id} timed out before results could be saved."
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

        successful_boards = [
            result
            for result in collector_result.board_results
            if result.status == "success"
        ]
        failed_boards = [
            result
            for result in collector_result.board_results
            if result.status == "failed"
        ]
        if successful_boards and failed_boards:
            final_status = "partial_success"
        elif successful_boards:
            final_status = "success"
        else:
            final_status = "failed"

        error_message = None
        if failed_boards:
            board_errors = "; ".join(
                f"{result.board_token}: {result.error_message or 'Unknown error'}"
                for result in failed_boards
            )
            error_message = (
                f"{len(failed_boards)} board(s) failed: {board_errors}"
            )[:2000]
        elif not collector_result.board_results:
            error_message = "No company boards are configured for this source."

        run = db.get(CollectionRun, run_id)
        run.status = final_status
        run.completed_at = datetime.utcnow()
        run.heartbeat_at = run.completed_at
        run.boards_completed = len(collector_result.board_results)
        run.boards_reconciled = reconciliation_result.boards_reconciled
        run.fetched = len(collector_result.jobs)
        run.inserted = upsert_result.inserted
        run.updated = upsert_result.updated
        run.reactivated = upsert_result.reactivated
        run.missing_observations = reconciliation_result.missing_observations
        run.closed = reconciliation_result.closed
        run.error_message = error_message
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:
        db.rollback()
        run = db.get(CollectionRun, run_id)
        db.refresh(run)
        if run.status == "running":
            run.status = "failed"
            run.completed_at = datetime.utcnow()
            run.heartbeat_at = run.completed_at
            run.error_message = str(exc)[:2000]
            db.commit()
        db.refresh(run)
        return run
