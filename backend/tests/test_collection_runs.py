import unittest

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.collection_run import CollectionRun
from app.models.job_skill import JobSkill
from app.models.raw_job import RawJob
from app.models.user import User  # noqa: F401
from app.services.collection_runs import execute_collection_run
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


if __name__ == "__main__":
    unittest.main()
