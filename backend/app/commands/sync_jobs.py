import argparse
import asyncio
import json

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.services.collection_runs import execute_collection_run
from app.services.collectors.company_registry import TARGET_COMPANIES
from app.services.deduplication import deduplicate_jobs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synchronize configured public job sources and record each run."
    )
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="Source to sync; repeat for multiple sources. Defaults to all configured sources.",
    )
    parser.add_argument(
        "--max-jobs-per-board",
        type=int,
        default=100,
        choices=range(1, 251),
        metavar="1-250",
    )
    return parser.parse_args()


async def sync_sources(sources: list[str], max_jobs_per_board: int) -> int:
    runs = []
    summaries = []
    with SessionLocal() as db:
        for source in sources:
            run = await execute_collection_run(
                db,
                source=source,
                max_jobs_per_board=max_jobs_per_board,
                trigger="scheduled",
            )
            runs.append(run)

        if any(run.status == "success" for run in runs):
            deduplicate_jobs(db)

        summaries = [
            {
                "run_id": run.id,
                "source": run.source,
                "status": run.status,
                "fetched": run.fetched,
                "inserted": run.inserted,
                "updated": run.updated,
                "reactivated": run.reactivated,
                "closed": run.closed,
                "error": run.error_message,
            }
            for run in runs
        ]
        has_failures = any(run.status == "failed" for run in runs)

    print(json.dumps(summaries, indent=2))
    return 1 if has_failures else 0


def main() -> None:
    args = parse_args()
    configured_sources = sorted(
        {company["source"] for company in TARGET_COMPANIES}
    )
    sources = args.sources or configured_sources
    unsupported_sources = sorted(set(sources) - set(configured_sources))
    if unsupported_sources:
        raise SystemExit(
            f"Unsupported or unconfigured sources: {', '.join(unsupported_sources)}"
        )

    init_db()
    raise SystemExit(asyncio.run(sync_sources(sources, args.max_jobs_per_board)))


if __name__ == "__main__":
    main()
