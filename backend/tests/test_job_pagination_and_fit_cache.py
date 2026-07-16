import unittest
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import jobs
from app.db.base import Base
from app.db import init_db as _registered_models  # noqa: F401
from app.db.session import get_db
from app.models.job_fit_score import JobFitScore
from app.models.job_skill import JobSkill
from app.models.raw_job import RawJob
from app.models.user import User
from app.models.user_profile import UserProfile


class JobPaginationAndFitCacheTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.db = self.session_factory()
        self.db.add(User(id=1, display_name="Default User"))
        self.profile = UserProfile(
            user_id=1,
            resume_text="Python SQL",
            target_roles="data analyst",
            target_locations="Bay Area",
        )
        self.db.add(self.profile)

        now = datetime.utcnow()
        for index, skill in enumerate(("Python", "SQL", "Tableau"), start=1):
            job = RawJob(
                source="test",
                external_job_id=f"job-{index}",
                company="Example",
                title=f"Data Analyst {index}",
                location="Palo Alto, CA",
                description=f"Required: {skill}",
                content_hash=f"hash-{index}",
                date_posted=now - timedelta(days=index),
                date_collected=now - timedelta(minutes=index),
                first_seen_at=now,
                last_seen_at=now,
                is_active=True,
                is_us_based=True,
                work_mode="onsite",
                seniority="entry",
                entry_fit_level="entry_friendly",
                entry_fit_score=90,
                career_eligible=True,
                role_category="data_analytics",
                target_relevance_score=90,
            )
            self.db.add(job)
            self.db.flush()
            self.db.add(
                JobSkill(
                    raw_job_id=job.id,
                    skill=skill,
                    category="programming" if skill != "Tableau" else "data_tools",
                    requirement_level="required",
                )
            )

        self.db.commit()

        app = FastAPI()
        app.include_router(jobs.router)

        def override_db():
            db = self.session_factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def test_jobs_endpoint_returns_pagination_metadata(self) -> None:
        response = self.client.get("/jobs?page=1&page_size=2")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["items"]), 2)
        self.assertEqual(payload["total"], 3)
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["page_size"], 2)
        self.assertEqual(payload["total_pages"], 2)

        second_page = self.client.get("/jobs?page=2&page_size=2").json()
        self.assertEqual(len(second_page["items"]), 1)
        self.assertEqual(second_page["total"], 3)

    def test_fit_cache_is_reused_and_invalidated_by_profile_changes(self) -> None:
        first_response = self.client.get("/jobs?page=1&page_size=2")
        self.assertEqual(first_response.status_code, 200)

        with Session(self.engine) as db:
            cache_count = db.scalar(select(func.count(JobFitScore.id)))
            cached = db.scalar(
                select(JobFitScore).order_by(JobFitScore.raw_job_id).limit(1)
            )
            first_signature = cached.profile_signature
            first_calculated_at = cached.calculated_at

        second_response = self.client.get("/jobs?page=1&page_size=2")
        self.assertEqual(second_response.status_code, 200)

        with Session(self.engine) as db:
            cached = db.scalar(
                select(JobFitScore).order_by(JobFitScore.raw_job_id).limit(1)
            )
            self.assertEqual(cache_count, 2)
            self.assertEqual(cached.profile_signature, first_signature)
            self.assertEqual(cached.calculated_at, first_calculated_at)

            profile = db.get(UserProfile, self.profile.id)
            profile.manual_skills_json = '[{"skill":"Tableau","category":"data_tools"}]'
            db.commit()

        changed_response = self.client.get("/jobs?page=1&page_size=2")
        self.assertEqual(changed_response.status_code, 200)

        with Session(self.engine) as db:
            cached = db.scalar(
                select(JobFitScore).order_by(JobFitScore.raw_job_id).limit(1)
            )
            self.assertNotEqual(cached.profile_signature, first_signature)

    def test_fit_sort_warms_cache_for_all_filtered_jobs(self) -> None:
        response = self.client.get("/jobs?sort_by=fit_score&page=1&page_size=2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 3)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count(JobFitScore.id))), 3)


if __name__ == "__main__":
    unittest.main()
