import unittest
from unittest.mock import AsyncMock

from app.services.collectors.ashby_collector import AshbyCollector


class AshbyCollectorTest(unittest.IsolatedAsyncioTestCase):
    def ashby_job(self, **overrides):
        job = {
            "id": "job-1",
            "title": "Data Analyst",
            "department": "Data",
            "team": "Risk Analytics",
            "employmentType": "FullTime",
            "location": "San Francisco, CA",
            "secondaryLocations": [
                {"location": "Remote (US)"},
                {"location": "New York, NY"},
            ],
            "publishedAt": "2026-07-15T10:30:00.000+00:00",
            "isListed": True,
            "isRemote": True,
            "workplaceType": "Hybrid",
            "jobUrl": "https://jobs.ashbyhq.com/example/job-1",
            "applyUrl": "https://jobs.ashbyhq.com/example/job-1/application",
            "descriptionPlain": "Analyze fraud and credit risk data with SQL.",
            "descriptionHtml": "<p>Analyze fraud and credit risk data with SQL.</p>",
            "compensation": {"scrapeableCompensationSalarySummary": "$90K - $120K"},
        }
        job.update(overrides)
        return job

    async def test_collect_normalizes_listed_jobs_and_excludes_unlisted_jobs(self) -> None:
        collector = AshbyCollector(
            board_token="example",
            company_name="Example",
            max_jobs=10,
        )
        collector._fetch_jobs = AsyncMock(
            return_value=[
                self.ashby_job(),
                self.ashby_job(id="hidden", isListed=False),
            ]
        )

        jobs = await collector.collect()

        self.assertEqual(len(jobs), 1)
        self.assertTrue(collector.is_exhaustive)
        self.assertEqual(jobs[0].source, "ashby")
        self.assertEqual(jobs[0].source_board_token, "example")
        self.assertEqual(jobs[0].external_job_id, "job-1")
        self.assertEqual(jobs[0].company, "Example")
        self.assertIn("San Francisco, CA", jobs[0].location)
        self.assertIn("Remote (US)", jobs[0].location)
        self.assertIn("Hybrid", jobs[0].location)
        self.assertEqual(
            jobs[0].description,
            "Analyze fraud and credit risk data with SQL.",
        )
        self.assertEqual(jobs[0].date_posted.year, 2026)
        self.assertIsNotNone(jobs[0].content_hash)

    async def test_collect_applies_keywords_across_structured_fields(self) -> None:
        collector = AshbyCollector("example", max_jobs=10)
        collector._fetch_jobs = AsyncMock(
            return_value=[
                self.ashby_job(),
                self.ashby_job(
                    id="job-2",
                    title="Account Executive",
                    department="Sales",
                    team="Enterprise",
                    descriptionPlain="Sell enterprise software.",
                    descriptionHtml="",
                ),
            ]
        )

        jobs = await collector.collect(keywords=["fraud"])

        self.assertEqual([job.external_job_id for job in jobs], ["job-1"])

    async def test_collection_is_not_exhaustive_when_board_exceeds_cap(self) -> None:
        collector = AshbyCollector("example", max_jobs=1)
        collector._fetch_jobs = AsyncMock(
            return_value=[
                self.ashby_job(id="job-1"),
                self.ashby_job(id="job-2"),
            ]
        )

        jobs = await collector.collect()

        self.assertEqual(len(jobs), 1)
        self.assertFalse(collector.is_exhaustive)


if __name__ == "__main__":
    unittest.main()
