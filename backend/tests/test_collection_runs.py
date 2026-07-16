import unittest
from datetime import datetime, timedelta

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.collection_board_run import CollectionBoardRun
from app.models.collection_run import CollectionRun
from app.models.job_skill import JobSkill
from app.models.raw_job import RawJob
from app.models.user import User  # noqa: F401
from app.services.collection_runs import (
    CollectionRunConflict,
    execute_collection_run,
    recover_stale_collection_runs,
)
from app.services.collectors import collector_runner
from app.services.collectors.base_collector import CollectedJob


class CollectionRunTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.original_collector = collector_runner.COLLECTORS["greenhouse"]

    def tearDown(self) -> None:
        collector_runner.COLLECTORS["greenhouse"] = self.original_collector
        self.db.close()
        self.engine.dispose()

    async def test_successful_run_persists_metrics_and_jobs(self) -> None:
        class SuccessfulCollector:
            def __init__(self, board_token, company_name=None, max_jobs=100) -> None:
                self.board_token = board_token
                self.is_exhaustive = True

            async def collect(self, keywords=None) -> list[CollectedJob]:
                return [
                    CollectedJob(
                        source="greenhouse",
                        source_board_token=self.board_token,
                        external_job_id="job-1",
                        company="Example",
                        title="SQL Data Analyst",
                        location="Palo Alto, CA",
                    )
                ]

        collector_runner.COLLECTORS["greenhouse"] = SuccessfulCollector
        run = await execute_collection_run(
            self.db,
            source="greenhouse",
            board_tokens=["example"],
            trigger="scheduled",
        )

        self.assertEqual(run.status, "success")
        self.assertEqual(run.trigger, "scheduled")
        self.assertEqual(run.fetched, 1)
        self.assertEqual(run.inserted, 1)
        self.assertEqual(run.boards_completed, 1)
        self.assertEqual(self.db.scalar(select(func.count(RawJob.id))), 1)
        self.assertEqual(self.db.scalar(select(func.count(JobSkill.id))), 1)
        board_run = self.db.scalar(select(CollectionBoardRun))
        self.assertEqual(board_run.status, "success")
        self.assertEqual(board_run.board_token, "example")
        self.assertEqual(board_run.fetched, 1)

    async def test_failed_run_is_logged_without_partial_jobs(self) -> None:
        class FailingCollector:
            def __init__(self, board_token, company_name=None, max_jobs=100) -> None:
                self.is_exhaustive = False

            async def collect(self, keywords=None) -> list[CollectedJob]:
                raise RuntimeError("source unavailable")

        collector_runner.COLLECTORS["greenhouse"] = FailingCollector
        run = await execute_collection_run(
            self.db,
            source="greenhouse",
            board_tokens=["example"],
        )

        self.assertEqual(run.status, "failed")
        self.assertIn("source unavailable", run.error_message)
        self.assertEqual(self.db.scalar(select(func.count(RawJob.id))), 0)
        self.assertEqual(self.db.scalar(select(func.count(CollectionRun.id))), 1)
        board_run = self.db.scalar(select(CollectionBoardRun))
        self.assertEqual(board_run.status, "failed")
        self.assertIn("source unavailable", board_run.error_message)

    async def test_failed_board_does_not_discard_successful_board_jobs(self) -> None:
        class PartiallyFailingCollector:
            def __init__(self, board_token, company_name=None, max_jobs=100) -> None:
                self.board_token = board_token
                self.is_exhaustive = True

            async def collect(self, keywords=None) -> list[CollectedJob]:
                if self.board_token == "broken":
                    raise RuntimeError("board unavailable")
                return [
                    CollectedJob(
                        source="greenhouse",
                        source_board_token=self.board_token,
                        external_job_id=f"{self.board_token}-job",
                        company=self.board_token,
                        title="Data Analyst",
                        location="San Francisco, CA",
                    )
                ]

        collector_runner.COLLECTORS["greenhouse"] = PartiallyFailingCollector
        run = await execute_collection_run(
            self.db,
            source="greenhouse",
            board_tokens=["working", "broken"],
        )

        self.assertEqual(run.status, "partial_success")
        self.assertEqual(run.boards_completed, 2)
        self.assertEqual(run.fetched, 1)
        self.assertEqual(run.inserted, 1)
        self.assertIn("broken", run.error_message)
        self.assertEqual(self.db.scalar(select(func.count(RawJob.id))), 1)

        board_runs = list(
            self.db.scalars(
                select(CollectionBoardRun).order_by(CollectionBoardRun.board_token)
            ).all()
        )
        self.assertEqual(
            [(board.board_token, board.status) for board in board_runs],
            [("broken", "failed"), ("working", "success")],
        )

    async def test_same_source_cannot_start_twice(self) -> None:
        active_run = CollectionRun(
            source="greenhouse",
            trigger="scheduled",
            status="running",
            started_at=datetime.utcnow(),
            heartbeat_at=datetime.utcnow(),
            boards_requested=1,
        )
        self.db.add(active_run)
        self.db.commit()

        with self.assertRaises(CollectionRunConflict) as context:
            await execute_collection_run(
                self.db,
                source="greenhouse",
                board_tokens=["example"],
            )

        self.assertEqual(context.exception.active_run.id, active_run.id)
        self.assertEqual(self.db.scalar(select(func.count(CollectionRun.id))), 1)

    async def test_stale_run_is_recovered_as_failed(self) -> None:
        stale_at = datetime.utcnow() - timedelta(minutes=11)
        stale_run = CollectionRun(
            source="greenhouse",
            trigger="scheduled",
            status="running",
            started_at=stale_at,
            heartbeat_at=stale_at,
            boards_requested=37,
        )
        self.db.add(stale_run)
        self.db.commit()

        recovered = recover_stale_collection_runs(self.db, timeout_minutes=10)
        self.db.refresh(stale_run)

        self.assertEqual(recovered, 1)
        self.assertEqual(stale_run.status, "failed")
        self.assertIsNotNone(stale_run.completed_at)
        self.assertIn("10 minutes", stale_run.error_message)

    async def test_interrupted_run_cannot_save_late_results(self) -> None:
        db = self.db

        class InterruptedCollector:
            def __init__(self, board_token, company_name=None, max_jobs=100) -> None:
                self.board_token = board_token
                self.is_exhaustive = True

            async def collect(self, keywords=None) -> list[CollectedJob]:
                run = db.scalar(
                    select(CollectionRun).where(CollectionRun.status == "running")
                )
                run.status = "failed"
                run.completed_at = datetime.utcnow()
                run.error_message = "Timed out during test."
                db.commit()
                return [
                    CollectedJob(
                        source="greenhouse",
                        source_board_token=self.board_token,
                        external_job_id="late-job",
                        title="SQL Data Analyst",
                    )
                ]

        collector_runner.COLLECTORS["greenhouse"] = InterruptedCollector
        run = await execute_collection_run(
            self.db,
            source="greenhouse",
            board_tokens=["example"],
        )

        self.assertEqual(run.status, "failed")
        self.assertEqual(self.db.scalar(select(func.count(RawJob.id))), 0)


if __name__ == "__main__":
    unittest.main()
