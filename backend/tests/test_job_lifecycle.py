import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.raw_job import RawJob
from app.models.user import User  # noqa: F401
from app.services.collectors.base_collector import CollectedJob
from app.services.collectors.collector_runner import BoardSyncScope
from app.services.collectors import collector_runner
from app.services.raw_jobs import reconcile_missing_jobs, upsert_raw_jobs


class JobLifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def collected_job(self) -> CollectedJob:
        return CollectedJob(
            source="greenhouse",
            source_board_token="example",
            external_job_id="job-1",
            company="Example",
            title="Data Analyst",
            location="Palo Alto, CA",
        )

    def missing_scope(self, can_reconcile: bool = True) -> BoardSyncScope:
        return BoardSyncScope(
            source="greenhouse",
            board_token="example",
            seen_external_job_ids=frozenset(),
            can_reconcile=can_reconcile,
        )

    def get_job(self) -> RawJob:
        return self.db.scalar(select(RawJob).where(RawJob.external_job_id == "job-1"))

    def test_job_closes_after_two_complete_collection_misses(self) -> None:
        upsert_raw_jobs(self.db, [self.collected_job()])

        first_result = reconcile_missing_jobs(self.db, [self.missing_scope()])
        job = self.get_job()
        self.assertTrue(job.is_active)
        self.assertEqual(job.missed_collection_count, 1)
        self.assertEqual(first_result.closed, 0)

        second_result = reconcile_missing_jobs(self.db, [self.missing_scope()])
        job = self.get_job()
        self.assertFalse(job.is_active)
        self.assertEqual(job.missed_collection_count, 2)
        self.assertIsNotNone(job.closed_at)
        self.assertEqual(second_result.closed, 1)

    def test_incomplete_collection_does_not_count_as_a_miss(self) -> None:
        upsert_raw_jobs(self.db, [self.collected_job()])

        result = reconcile_missing_jobs(
            self.db,
            [self.missing_scope(can_reconcile=False)],
        )
        job = self.get_job()

        self.assertTrue(job.is_active)
        self.assertEqual(job.missed_collection_count, 0)
        self.assertEqual(result.boards_reconciled, 0)

    def test_seen_job_reactivates_and_resets_misses(self) -> None:
        upsert_raw_jobs(self.db, [self.collected_job()])
        reconcile_missing_jobs(self.db, [self.missing_scope()])
        reconcile_missing_jobs(self.db, [self.missing_scope()])

        result = upsert_raw_jobs(self.db, [self.collected_job()])
        job = self.get_job()

        self.assertTrue(job.is_active)
        self.assertEqual(job.missed_collection_count, 0)
        self.assertIsNone(job.closed_at)
        self.assertEqual(result.reactivated, 1)


class CollectorScopeTest(unittest.IsolatedAsyncioTestCase):
    async def test_keyword_filtered_collection_cannot_reconcile_missing_jobs(self) -> None:
        original_collector = collector_runner.COLLECTORS["greenhouse"]

        class FakeCollector:
            def __init__(self, board_token, company_name=None, max_jobs=25) -> None:
                self.board_token = board_token
                self.is_exhaustive = True

            async def collect(self, keywords=None) -> list[CollectedJob]:
                return [
                    CollectedJob(
                        source="greenhouse",
                        source_board_token=self.board_token,
                        external_job_id="job-1",
                        title="Data Analyst",
                    )
                ]

        collector_runner.COLLECTORS["greenhouse"] = FakeCollector
        try:
            filtered_result = await collector_runner.run_collectors(
                source="greenhouse",
                board_tokens=["lifecycle-test"],
                keywords=["data"],
            )
            complete_result = await collector_runner.run_collectors(
                source="greenhouse",
                board_tokens=["lifecycle-test"],
            )
        finally:
            collector_runner.COLLECTORS["greenhouse"] = original_collector

        self.assertFalse(filtered_result.board_scopes[0].can_reconcile)
        self.assertTrue(complete_result.board_scopes[0].can_reconcile)


if __name__ == "__main__":
    unittest.main()
