import unittest

from app.services.job_cleaning import (
    calculate_target_relevance_score,
    detect_role_category,
)


class TargetRelevanceTest(unittest.TestCase):
    def score(self, title: str, description: str) -> tuple[str, int]:
        category = detect_role_category(title, description)
        return category, calculate_target_relevance_score(
            title,
            description,
            category,
        )

    def test_direct_data_risk_and_ai_titles_are_relevant(self) -> None:
        cases = [
            ("Data Analyst", "Build SQL dashboards."),
            ("Risk Operations Specialist", "Analyze fraud trends and metrics."),
            ("Applied AI Engineer", "Build LLM evaluation systems with Python."),
            ("Data Engineer", "Build Python and SQL pipelines."),
        ]

        for title, description in cases:
            with self.subTest(title=title):
                _, score = self.score(title, description)
                self.assertGreaterEqual(score, 50)

    def test_description_alone_cannot_make_unrelated_title_relevant(self) -> None:
        cases = [
            "Mobile Engineer, Android",
            "Design Engineer",
            "Viral Creative Producer",
            "Product Manager",
            "Software Engineer, Fraud & Identity",
            "IT Operations Analyst",
            "Strategy & Operations, Learning and Development",
        ]
        description = (
            "Use Python, SQL, dashboards, machine learning, LLMs, metrics, "
            "experimentation, and data-driven decision making."
        )

        for title in cases:
            with self.subTest(title=title):
                _, score = self.score(title, description)
                self.assertLess(score, 50)

    def test_generic_analyst_title_remains_discoverable(self) -> None:
        category, score = self.score(
            "Business Operations Analyst",
            "Own metrics, forecasts, and stakeholder reporting.",
        )

        self.assertEqual(category, "analytics_adjacent")
        self.assertGreaterEqual(score, 50)

    def test_research_engineer_requires_strong_ai_evidence(self) -> None:
        ai_category, ai_score = self.score(
            "Research Engineer, Post-Training",
            "Develop machine learning and large language model evaluation systems.",
        )
        general_category, general_score = self.score(
            "Research Engineer, Hardware",
            "Design laboratory equipment and mechanical test fixtures.",
        )

        self.assertEqual(ai_category, "ai_ml")
        self.assertGreaterEqual(ai_score, 50)
        self.assertEqual(general_category, "unknown")
        self.assertLess(general_score, 50)


if __name__ == "__main__":
    unittest.main()
