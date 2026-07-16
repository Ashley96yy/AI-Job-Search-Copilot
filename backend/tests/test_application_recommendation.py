import unittest
from typing import Optional

from app.models.raw_job import RawJob
from app.services.fit_score import FitScoreResult, recommend_application_action


def make_job(**updates) -> RawJob:
    defaults = {
        "source": "test",
        "external_job_id": "job-1",
        "title": "Data Analyst",
        "career_eligible": True,
        "entry_fit_level": "entry_friendly",
        "target_relevance_score": 80,
    }
    defaults.update(updates)
    return RawJob(**defaults)


def make_fit(
    score: int,
    missing_required: Optional[list[str]] = None,
) -> FitScoreResult:
    return FitScoreResult(
        fit_score=score,
        match_level="Good Match",
        missing_required_skills=missing_required or [],
        fit_breakdown=[
            {"key": "domain", "score": 10},
            {"key": "interest", "score": 5},
        ],
    )


class ApplicationRecommendationTest(unittest.TestCase):
    def test_ineligible_or_too_senior_job_is_skipped(self) -> None:
        job = make_job(
            career_eligible=False,
            required_experience_years=3,
            career_eligibility_reason="Requires 3 years of experience.",
        )

        result = recommend_application_action(job, make_fit(90))

        self.assertEqual(result.key, "skip")
        self.assertIn("3 years", result.reason)

    def test_irrelevant_job_is_skipped(self) -> None:
        result = recommend_application_action(
            make_job(target_relevance_score=20),
            make_fit(80),
        )

        self.assertEqual(result.key, "skip")

    def test_unclear_seniority_is_not_automatically_skipped(self) -> None:
        result = recommend_application_action(
            make_job(
                seniority="unknown",
                entry_fit_level="too_senior",
                entry_fit_reasons="Seniority unclear",
            ),
            make_fit(60),
        )

        self.assertEqual(result.key, "tailor_first")

    def test_good_fit_without_required_gaps_is_apply(self) -> None:
        result = recommend_application_action(make_job(), make_fit(72))

        self.assertEqual(result.key, "apply")

    def test_required_gap_is_tailor_first(self) -> None:
        result = recommend_application_action(
            make_job(),
            make_fit(68, ["Tableau"]),
        )

        self.assertEqual(result.key, "tailor_first")
        self.assertIn("1 required skill gap", result.reason)

    def test_domain_mismatch_is_tailor_first_even_with_good_fit(self) -> None:
        fit = make_fit(72)
        fit = FitScoreResult(
            fit_score=fit.fit_score,
            match_level=fit.match_level,
            fit_breakdown=[
                {"key": "domain", "score": 0},
                {"key": "interest", "score": 0},
            ],
        )

        result = recommend_application_action(make_job(), fit)

        self.assertEqual(result.key, "tailor_first")

    def test_low_fit_but_relevant_job_is_stretch(self) -> None:
        result = recommend_application_action(make_job(), make_fit(42))

        self.assertEqual(result.key, "stretch")


if __name__ == "__main__":
    unittest.main()
