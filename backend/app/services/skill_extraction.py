import html
import re
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.job_skill import JobSkill
from app.models.raw_job import RawJob


SKILL_DICTIONARY: dict[str, dict[str, list[str]]] = {
    "programming": {
        "SQL": [r"\bsql\b"],
        "Python": [r"\bpython\b"],
        "R": [r"\br\b", r"\br programming\b"],
        "Java": [r"\bjava\b"],
        "Scala": [r"\bscala\b"],
    },
    "data_tools": {
        "Excel": [r"\bexcel\b", r"\bspreadsheets?\b"],
        "Tableau": [r"\btableau\b"],
        "Power BI": [r"\bpower\s*bi\b"],
        "Looker": [r"\blooker\b"],
        "Dashboarding": [r"\bdashboards?\b", r"\bdashboarding\b"],
    },
    "database": {
        "PostgreSQL": [r"\bpostgresql\b", r"\bpostgres\b"],
        "MySQL": [r"\bmysql\b"],
        "Snowflake": [r"\bsnowflake\b"],
        "BigQuery": [r"\bbigquery\b", r"\bbig query\b"],
    },
    "ml_ai": {
        "Machine Learning": [r"\bmachine learning\b", r"\bml\b"],
        "Regression": [r"\bregression\b"],
        "Classification": [r"\bclassification\b"],
        "LLM": [r"\bllm\b", r"\blarge language model"],
        "GenAI": [r"\bgenai\b", r"\bgenerative ai\b"],
        "RAG": [r"\brag\b", r"\bretrieval augmented generation\b"],
        "Prompt Engineering": [r"\bprompt engineering\b"],
    },
    "cloud": {
        "AWS": [r"\baws\b", r"\bamazon web services\b"],
        "Azure": [r"\bazure\b"],
        "GCP": [r"\bgcp\b", r"\bgoogle cloud\b"],
    },
    "finance_risk": {
        "Credit Risk": [r"\bcredit risk\b"],
        "Fraud": [r"\bfraud\b"],
        "AML": [r"\baml\b", r"\banti-money laundering\b"],
        "Compliance": [r"\bcompliance\b"],
        "Model Risk": [r"\bmodel risk\b"],
        "Risk Management": [r"\brisk management\b"],
    },
    "soft_skills": {
        "Communication": [r"\bcommunication\b"],
        "Stakeholder Management": [r"\bstakeholder\b"],
        "Presentation": [r"\bpresentation\b", r"\bpresentations\b"],
    },
}


@dataclass(frozen=True)
class ExtractedSkill:
    skill: str
    category: str
    requirement_level: str = "mentioned"
    evidence_snippet: Optional[str] = None


REQUIREMENT_PRIORITY = {
    "mentioned": 0,
    "preferred": 1,
    "required": 2,
}

REQUIRED_SECTION_MARKERS = (
    "required",
    "requirements",
    "required qualifications",
    "minimum qualifications",
    "basic qualifications",
    "what you'll need",
    "what you will need",
    "what we're looking for",
    "what we are looking for",
    "what you'll bring",
    "what you will bring",
    "you have",
    "must have",
)

PREFERRED_SECTION_MARKERS = (
    "preferred",
    "preferred qualifications",
    "preferred experience",
    "preferred skills",
    "preferred:",
    "nice to have",
    "nice-to-have",
    "bonus qualifications",
    "bonus points",
    "desired qualifications",
)

MENTIONED_SECTION_MARKERS = (
    "about the team",
    "about the role",
    "about this role",
    "job summary",
    "responsibilities",
    "what you'll do",
    "what you will do",
    "the opportunity",
    "role overview",
    "benefits",
    "compensation",
    "work model",
    "equal opportunity",
)


def html_to_lines(text: str) -> list[str]:
    decoded = text
    for _ in range(2):
        next_value = html.unescape(decoded)
        if next_value == decoded:
            break
        decoded = next_value

    decoded = re.sub(
        r"<\s*/?\s*(?:br|div|p|li|ul|ol|section|h[1-6])\b[^>]*>",
        "\n",
        decoded,
        flags=re.IGNORECASE,
    )
    decoded = re.sub(r"<[^>]+>", " ", decoded)
    decoded = decoded.replace("\r", "\n")

    lines: list[str] = []
    for raw_line in decoded.split("\n"):
        cleaned = re.sub(r"\s+", " ", raw_line).strip(" -•\t")
        if not cleaned:
            continue
        lines.extend(
            part.strip()
            for part in re.split(r"(?<=[.!?])\s+(?=[A-Z])", cleaned)
            if part.strip()
        )

    return lines


def section_for_line(line: str, current_section: str) -> str:
    normalized = line.lower().strip()

    if any(is_section_heading(normalized, marker) for marker in PREFERRED_SECTION_MARKERS):
        return "preferred"
    if any(is_section_heading(normalized, marker) for marker in REQUIRED_SECTION_MARKERS):
        return "required"
    if any(is_section_heading(normalized, marker) for marker in MENTIONED_SECTION_MARKERS):
        return "mentioned"

    return current_section


def is_section_heading(line: str, marker: str) -> bool:
    normalized_line = line.strip(" :–—-")
    normalized_marker = marker.strip(" :–—-")

    if normalized_line == normalized_marker:
        return True
    if normalized_line.startswith(f"{normalized_marker}:"):
        return True
    return len(normalized_line) <= 120 and normalized_marker in normalized_line


def requirement_level_for_line(line: str, current_section: str) -> str:
    normalized = line.lower()
    preferred_cues = (
        "preferred",
        "nice to have",
        "nice-to-have",
        "bonus",
        "ideally",
        "a plus",
    )
    required_cues = (
        "required",
        "must have",
        "must be",
        "minimum",
        "at least",
        "you have",
        "you bring",
    )

    if any(cue in normalized for cue in preferred_cues):
        return "preferred"
    if any(cue in normalized for cue in required_cues):
        return "required"

    return current_section


def extract_job_skills(job: RawJob) -> list[ExtractedSkill]:
    lines = [job.title or ""] + html_to_lines(job.description or "")
    classified_lines: list[tuple[str, str]] = []
    current_section = "mentioned"

    for index, line in enumerate(lines):
        if index > 0:
            current_section = section_for_line(line, current_section)
        classified_lines.append(
            (line, requirement_level_for_line(line, current_section))
        )

    extracted_by_skill: dict[str, ExtractedSkill] = {}

    for category, skills in SKILL_DICTIONARY.items():
        for skill, patterns in skills.items():
            for line, requirement_level in classified_lines:
                if not any(
                    re.search(pattern, line, flags=re.IGNORECASE)
                    for pattern in patterns
                ):
                    continue

                candidate = ExtractedSkill(
                    skill=skill,
                    category=category,
                    requirement_level=requirement_level,
                    evidence_snippet=line[:500],
                )
                existing = extracted_by_skill.get(skill)
                if (
                    not existing
                    or REQUIREMENT_PRIORITY[candidate.requirement_level]
                    > REQUIREMENT_PRIORITY[existing.requirement_level]
                ):
                    extracted_by_skill[skill] = candidate

    return sorted(
        extracted_by_skill.values(),
        key=lambda item: (
            -REQUIREMENT_PRIORITY[item.requirement_level],
            item.category,
            item.skill,
        ),
    )


def extract_skills_from_text(text: str) -> list[ExtractedSkill]:
    extracted: list[ExtractedSkill] = []

    for category, skills in SKILL_DICTIONARY.items():
        for skill, patterns in skills.items():
            if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
                extracted.append(ExtractedSkill(skill=skill, category=category))

    return extracted


def extract_skills_for_job(db: Session, job: RawJob) -> int:
    extracted_skills = extract_job_skills(job)

    db.execute(delete(JobSkill).where(JobSkill.raw_job_id == job.id))

    for extracted in extracted_skills:
        db.add(
            JobSkill(
                raw_job_id=job.id,
                skill=extracted.skill,
                category=extracted.category,
                requirement_level=extracted.requirement_level,
                evidence_snippet=extracted.evidence_snippet,
            )
        )

    return len(extracted_skills)


def extract_skills_for_all_jobs(db: Session) -> int:
    jobs = list(db.scalars(select(RawJob)).all())
    total_skills = 0

    for job in jobs:
        total_skills += extract_skills_for_job(db, job)

    db.commit()
    return total_skills


def extract_skills_for_jobs(
    db: Session,
    job_ids: list[int],
    commit: bool = True,
) -> int:
    if not job_ids:
        return 0

    jobs = list(db.scalars(select(RawJob).where(RawJob.id.in_(job_ids))).all())
    total_skills = 0

    for job in jobs:
        total_skills += extract_skills_for_job(db, job)

    if commit:
        db.commit()
    else:
        db.flush()
    return total_skills
