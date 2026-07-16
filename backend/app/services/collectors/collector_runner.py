from dataclasses import dataclass, field
from typing import Optional

from app.services.collectors.base_collector import CollectedJob
from app.services.collectors.company_registry import TARGET_COMPANIES
from app.services.collectors.greenhouse_collector import GreenhouseCollector
from app.services.collectors.lever_collector import LeverCollector


COLLECTORS = {
    "greenhouse": GreenhouseCollector,
    "lever": LeverCollector,
}


@dataclass(frozen=True)
class BoardSyncScope:
    source: str
    board_token: str
    seen_external_job_ids: frozenset[str]
    can_reconcile: bool


@dataclass
class CollectorRunResult:
    jobs: list[CollectedJob] = field(default_factory=list)
    board_scopes: list[BoardSyncScope] = field(default_factory=list)


async def run_collectors(
    source: str = "greenhouse",
    board_tokens: Optional[list[str]] = None,
    keywords: Optional[list[str]] = None,
    max_jobs_per_board: int = 25,
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
        collector = collector_class(
            board_token=company["board_token"],
            company_name=company["name"],
            max_jobs=max_jobs_per_board,
        )
        board_jobs = await collector.collect(keywords)
        result.jobs.extend(board_jobs)
        result.board_scopes.append(
            BoardSyncScope(
                source=source,
                board_token=company["board_token"],
                seen_external_job_ids=frozenset(
                    job.external_job_id for job in board_jobs
                ),
                can_reconcile=not keywords and collector.is_exhaustive,
            )
        )

    return result
