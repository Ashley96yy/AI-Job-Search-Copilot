from typing import Optional

from app.models.job_skill import JobSkill
from app.models.raw_job import RawJob
from app.models.resume_version import ResumeVersion
from app.models.user_profile import UserProfile
from app.schemas.assistant import CoverLetterResponse
from app.services.fit_score import normalize_skill, parse_profile_skills
from app.services.resume_suggestions import (
    build_profile_evidence_sentences,
    ensure_sentence,
    find_evidence,
)


ROLE_OPENERS = {
    "ai_ml": "AI and machine learning analytics",
    "data_analytics": "data analytics and business intelligence",
    "data_engineering": "data pipelines and data quality",
    "risk_compliance": "risk, compliance, and analytics",
    "finance_accounting": "finance and analytical problem solving",
    "product": "product analytics and business decision support",
}


def build_cover_letter(
    job: RawJob,
    job_skills: list[JobSkill],
    profile: UserProfile,
    resume_version: Optional[ResumeVersion],
) -> CoverLetterResponse:
    evidence_sentences = build_profile_evidence_sentences(profile, resume_version)
    profile_skills = parse_profile_skills(profile)
    job_skill_names = sorted({skill.skill for skill in job_skills})
    matched_keywords = [
        skill for skill in job_skill_names if normalize_skill(skill) in profile_skills
    ]
    evidence = find_evidence(
        evidence_sentences,
        [normalize_skill(skill) for skill in matched_keywords[:8]],
    )[:4]
    evidence = prioritize_action_evidence(evidence)[:3]

    role_focus = ROLE_OPENERS.get(job.role_category or "", "data-driven business problem solving")
    company = job.company or "your team"
    title = job.title or "this role"
    location = job.normalized_location or job.location

    evidence_paragraph = build_evidence_paragraph(evidence, matched_keywords)
    skills_paragraph = build_skills_paragraph(matched_keywords)
    caveats = build_caveats(job_skill_names, matched_keywords)

    draft_parts = [
        "Dear Hiring Team,",
        (
            f"I am writing to express my interest in the {title} role at {company}. "
            f"The position stands out to me because it connects closely with {role_focus}"
            f"{f' in {location}' if location else ''}."
        ),
        evidence_paragraph,
        skills_paragraph,
        (
            "I would welcome the opportunity to discuss how my background can support "
            f"{company}'s team. Thank you for your time and consideration."
        ),
        "Sincerely,",
        profile.name or "",
    ]

    return CoverLetterResponse(
        raw_job_id=job.id,
        resume_version_id=resume_version.id if resume_version else None,
        job_title=title,
        company=job.company,
        draft="\n\n".join(part for part in draft_parts if part.strip()),
        evidence=evidence,
        matched_keywords=matched_keywords,
        caveats=caveats,
    )


def build_evidence_paragraph(evidence: list[str], matched_keywords: list[str]) -> str:
    if evidence:
        strongest_evidence = " ".join(ensure_sentence(item) for item in evidence[:2])
        return (
            "In my previous experience, I have built evidence relevant to this role. "
            f"For example, {strongest_evidence}"
        )

    if matched_keywords:
        return (
            "My background includes skills that match several of the role requirements, "
            "and I would use the application materials to connect those skills to the "
            "most relevant projects and work experience."
        )

    return (
        "I would use this application to focus on the parts of my background that are "
        "most relevant to the role, while avoiding unsupported claims."
    )


def prioritize_action_evidence(evidence: list[str]) -> list[str]:
    action_terms = (
        "analyzed",
        "automated",
        "built",
        "consolidated",
        "created",
        "delivered",
        "designed",
        "developed",
        "implemented",
        "integrated",
        "orchestrated",
        "produced",
        "reduced",
        "standardizing",
        "using",
        "validated",
    )

    action_items = [
        item for item in evidence if any(term in item.lower() for term in action_terms)
    ]
    if action_items:
        return action_items

    fallback_items = [item for item in evidence if item not in action_items]

    return fallback_items


def build_skills_paragraph(matched_keywords: list[str]) -> str:
    if not matched_keywords:
        return (
            "I am especially interested in roles where analytical thinking, structured "
            "problem solving, and careful communication can create practical business impact."
        )

    visible_keywords = ", ".join(matched_keywords[:6])
    return (
        f"The role's requirements around {visible_keywords} align with skills already "
        "represented in my profile. I would emphasize those areas clearly while keeping "
        "the final application truthful and specific."
    )


def build_caveats(job_skill_names: list[str], matched_keywords: list[str]) -> list[str]:
    missing_keywords = [
        skill for skill in job_skill_names if skill not in set(matched_keywords)
    ][:8]

    if not missing_keywords:
        return []

    return [
        (
            "The draft does not claim these job keywords without profile evidence: "
            + ", ".join(missing_keywords)
            + "."
        )
    ]
