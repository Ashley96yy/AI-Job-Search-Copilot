import json
import re
from typing import Optional

from app.models.job_skill import JobSkill
from app.models.raw_job import RawJob
from app.models.resume_version import ResumeVersion
from app.models.user_profile import UserProfile
from app.schemas.assistant import ResumeSuggestionItem, ResumeSuggestionResponse
from app.services.fit_score import normalize_skill, parse_profile_skills


ROLE_EMPHASIS = {
    "data_analytics": [
        ("SQL / dashboard analytics", ["sql", "dashboard", "power bi", "tableau", "metrics"]),
        ("business impact and stakeholder reporting", ["stakeholder", "kpi", "reporting"]),
    ],
    "data_engineering": [
        ("data pipelines and warehouse modeling", ["airflow", "dbt", "snowflake", "pipeline", "pyspark"]),
        ("reliability and data quality", ["data-quality", "quality", "reconciliation", "validation"]),
    ],
    "risk_compliance": [
        ("risk analysis and controls evidence", ["risk", "credit", "compliance", "fraud", "aml"]),
        ("financial statement and risk indicator analysis", ["financial", "borrower", "creditworthiness"]),
    ],
    "ai_ml": [
        ("modeling and ML platform evidence", ["machine learning", "mlflow", "model", "feature", "prediction"]),
        ("AI application and evaluation language", ["ai", "llm", "genai", "prompt", "rag"]),
    ],
}


def build_resume_suggestions(
    job: RawJob,
    job_skills: list[JobSkill],
    profile: UserProfile,
    resume_version: Optional[ResumeVersion],
) -> ResumeSuggestionResponse:
    evidence_sentences = build_profile_evidence_sentences(profile, resume_version)
    profile_skills = parse_profile_skills(profile)
    job_skill_names = sorted({skill.skill for skill in job_skills})
    suggestions: list[ResumeSuggestionItem] = []
    unsupported_keywords: list[str] = []

    for skill in job_skill_names:
        normalized = normalize_skill(skill)
        evidence = find_evidence(evidence_sentences, [normalized])
        if normalized in profile_skills or evidence:
            suggestions.append(
                ResumeSuggestionItem(
                    suggestion_type="skill_emphasis",
                    title=f"Emphasize {skill}",
                    suggestion=(
                        f"Make {skill} visible in the selected resume version if it is relevant "
                        "to this role's requirements."
                    ),
                    related_keyword=skill,
                    evidence=evidence[:3],
                    risk_level="safe" if evidence else "needs_review",
                )
            )
        else:
            unsupported_keywords.append(skill)

    for title, keywords in ROLE_EMPHASIS.get(job.role_category or "", []):
        evidence = find_evidence(evidence_sentences, keywords)
        if evidence:
            suggestions.append(
                ResumeSuggestionItem(
                    suggestion_type="role_emphasis",
                    title=f"Highlight {title}",
                    suggestion=(
                        f"For this {job.role_category.replace('_', ' ')} role, move the strongest "
                        f"{title} bullets higher in the resume version."
                    ),
                    related_keyword=title,
                    evidence=evidence[:3],
                    risk_level="safe",
                )
            )

    if job.entry_fit_level == "too_senior":
        suggestions.append(
            ResumeSuggestionItem(
                suggestion_type="seniority_risk",
                title="Check seniority risk before tailoring",
                suggestion=(
                    "This role appears above intern/entry-level. Tailor only if you still want "
                    "to treat it as a stretch application."
                ),
                related_keyword=job.entry_fit_level,
                evidence=[job.entry_fit_reasons] if job.entry_fit_reasons else [],
                risk_level="needs_review",
            )
        )

    for keyword in unsupported_keywords[:8]:
        suggestions.append(
            ResumeSuggestionItem(
                suggestion_type="unsupported_keyword",
                title=f"Do not invent {keyword}",
                suggestion=(
                    f"{keyword} appears in the job requirements, but the current profile/resume "
                    "does not provide clear evidence. Do not add it as a claim unless you can support it."
                ),
                related_keyword=keyword,
                evidence=[],
                risk_level="unsupported",
            )
        )

    return ResumeSuggestionResponse(
        raw_job_id=job.id,
        resume_version_id=resume_version.id if resume_version else None,
        job_title=job.title,
        company=job.company,
        suggestions=dedupe_suggestions(suggestions)[:12],
        unsupported_keywords=unsupported_keywords,
    )


def build_profile_evidence_sentences(
    profile: UserProfile,
    resume_version: Optional[ResumeVersion],
) -> list[str]:
    sentences: list[str] = []
    sentences.extend(extract_json_evidence(profile.work_experience_json or ""))
    sentences.extend(extract_json_evidence(profile.domain_experience_json or ""))
    if resume_version:
        sentences.extend(split_evidence(resume_version.resume_text or ""))
    sentences.extend(split_evidence(profile.resume_text or ""))

    return dedupe_text_items(sentences)


def split_evidence(text: str) -> list[str]:
    try:
        parsed = json.loads(text)
        return extract_json_items(parsed)
    except (json.JSONDecodeError, TypeError):
        pass

    parts = re.split(r"(?:\n|•|;)+", text)
    return [clean_evidence_text(part) for part in parts if clean_evidence_text(part)]


def extract_json_evidence(text: str) -> list[str]:
    if not text:
        return []

    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return split_evidence(text)

    return extract_json_items(parsed)


def extract_json_items(value: object) -> list[str]:
    items: list[str] = []

    if isinstance(value, list):
        for item in value:
            items.extend(extract_json_items(item))
        return items

    if isinstance(value, dict):
        for key in ("bullets", "evidence"):
            nested_value = value.get(key)
            if nested_value:
                items.extend(extract_json_items(nested_value))
        return items

    if isinstance(value, str):
        cleaned = clean_evidence_text(value)
        return [cleaned] if cleaned else []

    return items


def clean_evidence_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip(" -[]{}\"'")
    if len(cleaned) < 35:
        return ""
    if any(token in cleaned for token in ("{", "}", "[", "]", "\":")):
        return ""
    return cleaned


def dedupe_text_items(items: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()

    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped


def ensure_sentence(value: str) -> str:
    if value.endswith((".", "!", "?")):
        return value
    return f"{value}."


def find_evidence(sentences: list[str], keywords: list[str]) -> list[str]:
    matches: list[str] = []
    seen: set[str] = set()
    for sentence in sentences:
        sentence_lower = sentence.lower()
        if any(keyword_matches_sentence(keyword, sentence_lower) for keyword in keywords):
            normalized = re.sub(r"\s+", " ", sentence_lower)
            if normalized in seen:
                continue
            seen.add(normalized)
            matches.append(sentence)
    return matches


def keyword_matches_sentence(keyword: str, sentence_lower: str) -> bool:
    if not keyword:
        return False
    if keyword in sentence_lower:
        return True

    stop_terms = {
        "analysis",
        "analytics",
        "business",
        "data",
        "engineering",
        "management",
    }
    tokens = [
        token
        for token in re.split(r"[^a-z0-9]+", keyword.lower())
        if len(token) >= 3 and token not in stop_terms
    ]
    if not tokens:
        return False

    return all(token in sentence_lower for token in tokens)


def dedupe_suggestions(
    suggestions: list[ResumeSuggestionItem],
) -> list[ResumeSuggestionItem]:
    seen: set[tuple[str, str]] = set()
    deduped: list[ResumeSuggestionItem] = []

    for suggestion in suggestions:
        key = (suggestion.suggestion_type, suggestion.title)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(suggestion)

    return deduped
