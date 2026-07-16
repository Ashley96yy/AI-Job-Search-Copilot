from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

from app.services.collectors.base_collector import CollectedJob
from app.services.collectors.ashby_collector import AshbyCollector
from app.services.collectors.company_registry import TARGET_COMPANIES
from app.services.collectors.greenhouse_collector import GreenhouseCollector
from app.services.collectors.lever_collector import LeverCollector


COLLECTORS = {
    "ashby": AshbyCollector,
    "greenhouse": GreenhouseCollector,
    "lever": LeverCollector,
}


@dataclass(frozen=True)
class BoardSyncScope:
    source: str
    board_token: str
    seen_external_job_ids: frozenset[str]
    can_reconcile: bool


@dataclass(frozen=True)
class BoardCollectionResult:
    source: str
    board_token: str
    company_name: str
    status: str
    started_at: datetime
    completed_at: datetime
    fetched: int = 0
    can_reconcile: bool = False
    error_message: Optional[str] = None


@dataclass
class CollectorRunResult:
    jobs: list[CollectedJob] = field(default_factory=list)
    board_scopes: list[BoardSyncScope] = field(default_factory=list)
    board_results: list[BoardCollectionResult] = field(default_factory=list)


async def run_collectors(
    source: str = "greenhouse",
    board_tokens: Optional[list[str]] = None,
    keywords: Optional[list[str]] = None,
    max_jobs_per_board: int = 25,
    on_board_complete: Optional[Callable[[BoardCollectionResult], None]] = None,
) -> CollectorRunResult:
    if source not in COLLECTORS:
        raise ValueError(f"Unsupported collector source: {source}")

    configured_companies = [
        company
        for company in TARGET_COMPANIES
        if company["source"] == source
        and (board_tokens is None or company["board_token"] in board_tokens)
    ]

    if board_tokens:
        configured_tokens = {company["board_token"] for company in configured_companies}
        configured_companies.extend(
            {
                "name": token,
                "source": source,
                "board_token": token,
                "keywords": keywords or [],
            }
            for token in board_tokens
            if token not in configured_tokens
        )

    result = CollectorRunResult()
    collector_class = COLLECTORS[source]

    for company in configured_companies:
        started_at = datetime.utcnow()
        try:
            collector = collector_class(
                board_token=company["board_token"],
                company_name=company["name"],
                max_jobs=max_jobs_per_board,
            )
            board_jobs = await collector.collect(keywords)
        except Exception as exc:
            board_result = BoardCollectionResult(
                source=source,
                board_token=company["board_token"],
                company_name=company["name"],
                status="failed",
                started_at=started_at,
                completed_at=datetime.utcnow(),
                error_message=str(exc)[:2000],
            )
            result.board_results.append(board_result)
            if on_board_complete:
                on_board_complete(board_result)
            continue

        result.jobs.extend(board_jobs)
        can_reconcile = not keywords and collector.is_exhaustive
        board_scope = BoardSyncScope(
            source=source,
            board_token=company["board_token"],
            seen_external_job_ids=frozenset(
                job.external_job_id for job in board_jobs
            ),
            can_reconcile=can_reconcile,
        )
        result.board_scopes.append(board_scope)
        board_result = BoardCollectionResult(
            source=source,
            board_token=company["board_token"],
            company_name=company["name"],
            status="success",
            started_at=started_at,
            completed_at=datetime.utcnow(),
            fetched=len(board_jobs),
            can_reconcile=can_reconcile,
        )
        result.board_results.append(board_result)
        if on_board_complete:
            on_board_complete(board_result)

    return result
