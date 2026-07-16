import html
import re
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.raw_job import RawJob


US_LOCATION_TERMS = {
    " usa",
    " us-",
    " united states",
    "new york",
    "san francisco",
    "chicago",
    "atlanta",
    "seattle",
    "boston",
    "austin",
    "denver",
    "washington",
    "california",
    "palo alto",
    "mountain view",
    "san jose",
    "sunnyvale",
    "santa clara",
    "redwood city",
    "menlo park",
    "remote - usa",
}

US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}

US_STATE_ALIASES = {
    "al": "Alabama",
    "alabama": "Alabama",
    "az": "Arizona",
    "arizona": "Arizona",
    "ca": "California",
    "california": "California",
    "co": "Colorado",
    "colorado": "Colorado",
    "dc": "District of Columbia",
    "district of columbia": "District of Columbia",
    "fl": "Florida",
    "florida": "Florida",
    "ga": "Georgia",
    "georgia": "Georgia",
    "il": "Illinois",
    "illinois": "Illinois",
    "ma": "Massachusetts",
    "massachusetts": "Massachusetts",
    "ny": "New York",
    "new york": "New York",
    "tx": "Texas",
    "texas": "Texas",
    "ut": "Utah",
    "utah": "Utah",
    "wa": "Washington",
    "washington": "Washington",
}

US_CITY_TO_STATE = {
    "atlanta": "Georgia",
    "austin": "Texas",
    "boston": "Massachusetts",
    "chicago": "Illinois",
    "denver": "Colorado",
    "miami": "Florida",
    "new york": "New York",
    "new york city": "New York",
    "palo alto": "California",
    "mountain view": "California",
    "san jose": "California",
    "sunnyvale": "California",
    "santa clara": "California",
    "redwood city": "California",
    "menlo park": "California",
    "san mateo": "California",
    "salt lake city": "Utah",
    "san francisco": "California",
    "seattle": "Washington",
    "sf hq": "California",
    "washington dc": "District of Columbia",
}

GENERAL_ENGINEERING_TITLE_TERMS = (
    "software engineer",
    "backend engineer",
    "frontend engineer",
    "mobile engineer",
    "security engineer",
    "design engineer",
    "infrastructure engineer",
    "platform engineer",
)

ENGINEERING_TARGET_OVERRIDES = (
    "data",
    "analytics",
    "machine learning",
    "ml engineer",
    "ai engineer",
    "artificial intelligence",
)

NON_TARGET_FUNCTION_TITLE_TERMS = (
    "it operations",
    "learning and development",
    "people operations",
    "human resources",
)


@dataclass
class CleanedJobFields:
    normalized_company: Optional[str]
    normalized_title: str
    normalized_location: Optional[str]
    country: Optional[str]
    state: Optional[str]
    is_us_based: bool
    work_mode: str
    seniority: str
    entry_fit_level: str
    entry_fit_score: int
    entry_fit_reasons: str
    required_experience_years: Optional[int]
    career_eligible: bool
    career_eligibility_reason: Optional[str]
    role_category: str
    target_relevance_score: int


def clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()
    return cleaned or None


PREFERRED_SECTION_MARKERS = (
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


def extract_required_experience_years(description: Optional[str]) -> Optional[int]:
    if not description:
        return None

    text = html.unescape(description)
    text = re.sub(
        r"<\s*/?\s*(?:br|div|p|li|ul|ol|h[1-6])\b[^>]*>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text).lower()

    preferred_indexes = [
        text.find(marker) for marker in PREFERRED_SECTION_MARKERS if marker in text
    ]
    required_scope = text[: min(preferred_indexes)] if preferred_indexes else text

    years_pattern = re.compile(
        r"\b(?P<years>\d{1,2})\s*(?:\+|(?:[-–—]|to)\s*\d{1,2})?\s+years?\b"
    )
    experience_signals = (
        "experience",
        "professional background",
        "working with",
        "work with",
        "work in",
    )
    non_candidate_signals = (
        "we have",
        "our company",
        "company has",
        "our team has",
        "collective experience",
    )
    detected_years: list[int] = []

    for match in years_pattern.finditer(required_scope):
        context_start = max(0, match.start() - 100)
        context_end = min(len(required_scope), match.end() + 120)
        context = required_scope[context_start:context_end]

        if any(marker in context for marker in PREFERRED_SECTION_MARKERS):
            continue
        if not any(signal in context for signal in experience_signals):
            continue
        if any(signal in context for signal in non_candidate_signals):
            continue

        detected_years.append(int(match.group("years")))

    return max(detected_years) if detected_years else None


def determine_career_eligibility(
    required_experience_years: Optional[int],
) -> tuple[bool, Optional[str]]:
    if required_experience_years is not None and required_experience_years >= 3:
        return (
            False,
            f"Requires at least {required_experience_years} years of experience",
        )

    return True, None


def normalize_company(company: Optional[str]) -> Optional[str]:
    cleaned = clean_text(company)
    if not cleaned:
        return None

    suffix_pattern = r"\b(inc\.?|llc|ltd\.?|corp\.?|corporation|financial,\s*inc)\b"
    normalized = re.sub(suffix_pattern, "", cleaned, flags=re.IGNORECASE)
    normalized = re.sub(r"[,.\s]+$", "", normalized)
    return clean_text(normalized)


def normalize_title(title: str) -> str:
    return clean_text(title).lower() if clean_text(title) else "unknown"


def normalize_location(location: Optional[str]) -> Optional[str]:
    cleaned = clean_text(location)
    if not cleaned:
        return None

    cleaned = cleaned.replace("US-", "US - ")
    cleaned = cleaned.replace("Remote -", "Remote - ")
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    cleaned = re.sub(r"\s*-\s*", " - ", cleaned)
    return clean_text(cleaned)


def detect_country(location: Optional[str]) -> Optional[str]:
    if not location:
        return None

    location_lower = f" {location.lower()} "
    state_code_pattern = "|".join(sorted(US_STATE_CODES))

    if re.search(rf",\s*(?:{state_code_pattern})\b", location, flags=re.IGNORECASE):
        return "US"

    if re.search(rf"\b(?:{state_code_pattern})\s*$", location, flags=re.IGNORECASE):
        return "US"

    if any(term in location_lower for term in US_LOCATION_TERMS):
        return "US"

    if "australia" in location_lower:
        return "Australia"

    if "canada" in location_lower:
        return "Canada"

    if "germany" in location_lower:
        return "Germany"

    if "singapore" in location_lower:
        return "Singapore"

    if "paris" in location_lower or "france" in location_lower:
        return "France"

    if "london" in location_lower or "united kingdom" in location_lower or " uk " in location_lower:
        return "UK"

    return None


def detect_us_state(location: Optional[str], country: Optional[str], work_mode: str) -> Optional[str]:
    if country != "US" or not location:
        return None

    location_lower = location.lower()
    normalized_for_match = re.sub(r"[^a-z0-9]+", " ", location_lower)
    detected_states: set[str] = set()

    for alias, state in US_STATE_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", normalized_for_match):
            detected_states.add(state)

    for city, state in US_CITY_TO_STATE.items():
        if re.search(rf"\b{re.escape(city)}\b", normalized_for_match):
            detected_states.add(state)

    if len(detected_states) == 1:
        return next(iter(detected_states))

    if len(detected_states) > 1:
        return "Multiple US States"

    if work_mode == "remote" or "remote" in location_lower:
        return "Remote - US"

    if "united states" in location_lower or re.search(r"\busa\b", normalized_for_match):
        return "United States - Unspecified"

    return None


def detect_work_mode(location: Optional[str], description: Optional[str]) -> str:
    location_lower = (location or "").lower()
    description_lower = (description or "").lower()

    if "remote" in location_lower:
        return "remote"

    if "hybrid" in location_lower:
        return "hybrid"

    if location:
        return "onsite"

    if "remote" in description_lower:
        return "remote"

    if "hybrid" in description_lower:
        return "hybrid"

    return "unknown"


def detect_seniority(
    title: str,
    description: Optional[str],
    required_experience_years: Optional[int] = None,
) -> str:
    title_lower = title.lower()

    if re.search(r"\b(intern|internship)\b", title_lower):
        return "intern"

    if re.search(r"\b(new grad|new graduate|entry level|entry-level)\b", title_lower):
        return "entry"

    if re.search(r"\b(junior|jr\.)\b", title_lower):
        return "junior"

    if required_experience_years is not None and required_experience_years <= 0:
        return "entry"

    if required_experience_years == 1:
        return "junior"

    if re.search(r"\b(lead|principal|staff)\b", title_lower):
        return "lead"

    if re.search(r"\b(senior|sr\.)\b", title_lower):
        return "senior"

    if required_experience_years is not None and required_experience_years >= 5:
        return "senior"

    if required_experience_years is not None and required_experience_years >= 2:
        return "mid"

    return "unknown"


def detect_entry_fit(
    title: str,
    description: Optional[str],
    seniority: str,
    required_experience_years: Optional[int] = None,
) -> tuple[str, int, str]:
    title_lower = title.lower()
    combined = f"{title} {description or ''}".lower()
    score = 45
    reasons: list[str] = []

    positive_title_patterns = [
        (r"\b(intern|internship)\b", 35, "Internship title signal"),
        (r"\b(new grad|new graduate|recent graduate|university graduate)\b", 35, "New grad title signal"),
        (r"\b(entry level|entry-level|early career)\b", 30, "Entry-level title signal"),
        (r"\b(junior|jr\.|associate)\b", 20, "Junior or associate title signal"),
    ]
    for pattern, weight, reason in positive_title_patterns:
        if re.search(pattern, title_lower):
            score += weight
            reasons.append(reason)

    positive_description_patterns = [
        (r"\b(new grad|new graduate|recent graduate|university graduate)\b", 25, "New grad requirement"),
        (r"\b(entry level|entry-level|early career)\b", 25, "Entry-level requirement"),
        (r"\b0\s*[-–]\s*2\s+years\b", 20, "0-2 years requirement"),
        (r"\b0\s*[-–]\s*1\s+years\b", 20, "0-1 years requirement"),
        (r"\b1\s*[-–]\s*2\s+years\b", 12, "1-2 years requirement"),
    ]
    for pattern, weight, reason in positive_description_patterns:
        if re.search(pattern, combined):
            score += weight
            reasons.append(reason)

    negative_title_patterns = [
        (r"\b(senior|sr\.|lead|principal|staff|manager|director|head of)\b", 45, "Senior title signal"),
    ]
    for pattern, penalty, reason in negative_title_patterns:
        if re.search(pattern, title_lower):
            score -= penalty
            reasons.append(reason)

    if required_experience_years is not None:
        if required_experience_years >= 5:
            score -= 45
            reasons.append(f"{required_experience_years}+ years required")
        elif required_experience_years >= 3:
            score -= 30
            reasons.append(f"{required_experience_years}+ years required")

    seniority_adjustments = {
        "intern": (30, "Classified as intern"),
        "entry": (25, "Classified as entry level"),
        "junior": (15, "Classified as junior"),
        "unknown": (0, "Seniority unclear"),
        "mid": (-15, "Classified as mid-level"),
        "senior": (-35, "Classified as senior"),
        "lead": (-45, "Classified as lead/principal"),
    }
    adjustment, reason = seniority_adjustments.get(seniority, (0, "Seniority unclear"))
    score += adjustment
    reasons.append(reason)

    score = max(0, min(100, score))
    unique_reasons = list(dict.fromkeys(reasons))

    if score >= 75:
        level = "entry_friendly"
    elif score >= 50:
        level = "possible_stretch"
    else:
        level = "too_senior"

    return level, score, "; ".join(unique_reasons[:5])


def detect_role_category(title: str, description: Optional[str]) -> str:
    title_lower = title.lower()
    description_lower = (description or "").lower()

    if any(term in title_lower for term in ["data analyst", "business intelligence", "bi analyst"]):
        return "data_analytics"

    if any(term in title_lower for term in ["analytics engineer", "data engineer"]):
        return "data_engineering"

    if any(
        term in title_lower
        for term in [
            "data scientist",
            "machine learning",
            "ml engineer",
            "ai engineer",
            "applied scientist",
        ]
    ):
        return "ai_ml"

    if any(
        term in title_lower
        for term in ["research engineer", "research scientist"]
    ) and any(
        term in description_lower
        for term in [
            "machine learning",
            "artificial intelligence",
            "large language model",
            "llm",
            "deep learning",
            "generative ai",
        ]
    ):
        return "ai_ml"

    if any(term in title_lower for term in GENERAL_ENGINEERING_TITLE_TERMS) and not any(
        term in title_lower for term in ENGINEERING_TARGET_OVERRIDES
    ):
        return "engineering"

    if any(term in title_lower for term in ["risk", "fraud", "aml", "compliance"]):
        return "risk_compliance"

    if any(term in title_lower for term in ["finance", "financial", "accounting", "controller"]):
        return "finance_accounting"

    if any(term in title_lower for term in ["product analyst", "product manager", "product operations"]):
        return "product"

    if any(term in title_lower for term in GENERAL_ENGINEERING_TITLE_TERMS):
        return "engineering"

    if any(term in title_lower for term in ["account executive", "sales", "customer success"]):
        return "sales_gtm"

    if any(
        term in title_lower
        for term in [
            "analyst",
            "analytics",
            "insights",
            "decision scientist",
            "operations research",
            "business operations",
            "strategy and operations",
            "strategy & operations",
            "quantitative",
            "data operations",
            "data quality",
            "data governance",
        ]
    ):
        return "analytics_adjacent"

    return "unknown"


def calculate_target_relevance_score(
    title: str,
    description: Optional[str],
    role_category: str,
) -> int:
    title_lower = title.lower()
    description_lower = (description or "").lower()
    score = 0

    category_scores = {
        "data_analytics": 35,
        "risk_compliance": 35,
        "ai_ml": 35,
        "data_engineering": 35,
        "analytics_adjacent": 25,
    }
    score += category_scores.get(role_category, 0)

    title_positive_terms = {
        "data analyst": 30,
        "analytics": 25,
        "analyst": 18,
        "business intelligence": 25,
        "bi analyst": 25,
        "insights": 20,
        "strategy": 12,
        "operations analyst": 18,
        "risk": 25,
        "fraud": 25,
        "compliance": 18,
        "aml": 25,
        "credit": 18,
        "data scientist": 28,
        "machine learning": 25,
        "ai": 18,
        "product analyst": 25,
        "analytics engineer": 24,
        "decision scientist": 28,
        "research engineer": 15,
        "research scientist": 20,
        "applied scientist": 25,
        "quantitative": 18,
        "data operations": 20,
        "data quality": 20,
        "data governance": 20,
    }
    title_signal_score = 0
    for term, weight in title_positive_terms.items():
        if term in title_lower:
            title_signal_score += weight
    score += title_signal_score

    description_positive_terms = {
        "sql": 12,
        "python": 12,
        "dashboard": 8,
        "tableau": 8,
        "power bi": 8,
        "looker": 8,
        "metrics": 8,
        "experimentation": 10,
        "a/b test": 10,
        "forecast": 8,
        "model": 8,
        "machine learning": 12,
        "llm": 10,
        "genai": 10,
        "risk": 10,
        "fraud": 10,
        "compliance": 8,
        "credit": 8,
        "aml": 10,
        "data-driven": 8,
        "data driven": 8,
    }
    description_score = sum(
        weight
        for term, weight in description_positive_terms.items()
        if term in description_lower
    )
    score += min(description_score, 30)

    negative_terms = {
        "account executive": 45,
        "sales": 28,
        "customer success": 22,
        "recruiter": 30,
        "talent acquisition": 30,
        "legal counsel": 35,
        "attorney": 35,
        "accounting manager": 35,
        "controller": 35,
        "software engineer": 25,
        "backend engineer": 25,
        "frontend engineer": 25,
        "full stack": 22,
        "designer": 20,
        "it operations": 35,
        "learning and development": 40,
        "people operations": 35,
        "human resources": 35,
    }
    for term, penalty in negative_terms.items():
        if term in title_lower:
            score -= penalty

    if role_category in {"sales_gtm", "engineering", "finance_accounting"}:
        score -= 15

    has_target_title_signal = (
        role_category
        in {
            "data_analytics",
            "analytics_adjacent",
            "risk_compliance",
            "ai_ml",
            "data_engineering",
        }
        or title_signal_score > 0
    )
    if not has_target_title_signal:
        score = min(score, 49)

    is_non_target_engineering = any(
        term in title_lower for term in GENERAL_ENGINEERING_TITLE_TERMS
    ) and not any(term in title_lower for term in ENGINEERING_TARGET_OVERRIDES)
    if is_non_target_engineering:
        score = min(score, 49)

    if any(term in title_lower for term in NON_TARGET_FUNCTION_TITLE_TERMS):
        score = min(score, 49)

    return max(0, min(100, score))


def clean_job_fields(job: RawJob) -> CleanedJobFields:
    normalized_location = normalize_location(job.location)
    country = detect_country(normalized_location)
    work_mode = detect_work_mode(normalized_location, job.description)
    role_category = detect_role_category(job.title, job.description)
    required_experience_years = extract_required_experience_years(job.description)
    career_eligible, career_eligibility_reason = determine_career_eligibility(
        required_experience_years
    )
    seniority = detect_seniority(
        job.title,
        job.description,
        required_experience_years,
    )
    entry_fit_level, entry_fit_score, entry_fit_reasons = detect_entry_fit(
        job.title,
        job.description,
        seniority,
        required_experience_years,
    )

    return CleanedJobFields(
        normalized_company=normalize_company(job.company),
        normalized_title=normalize_title(job.title),
        normalized_location=normalized_location,
        country=country,
        state=detect_us_state(normalized_location, country, work_mode),
        is_us_based=country == "US",
        work_mode=work_mode,
        seniority=seniority,
        entry_fit_level=entry_fit_level,
        entry_fit_score=entry_fit_score,
        entry_fit_reasons=entry_fit_reasons,
        required_experience_years=required_experience_years,
        career_eligible=career_eligible,
        career_eligibility_reason=career_eligibility_reason,
        role_category=role_category,
        target_relevance_score=calculate_target_relevance_score(
            job.title,
            job.description,
            role_category,
        ),
    )


def apply_cleaned_fields(job: RawJob) -> None:
    cleaned = clean_job_fields(job)
    job.normalized_company = cleaned.normalized_company
    job.normalized_title = cleaned.normalized_title
    job.normalized_location = cleaned.normalized_location
    job.country = cleaned.country
    job.state = cleaned.state
    job.is_us_based = cleaned.is_us_based
    job.work_mode = cleaned.work_mode
    job.seniority = cleaned.seniority
    job.entry_fit_level = cleaned.entry_fit_level
    job.entry_fit_score = cleaned.entry_fit_score
    job.entry_fit_reasons = cleaned.entry_fit_reasons
    job.required_experience_years = cleaned.required_experience_years
    job.career_eligible = cleaned.career_eligible
    job.career_eligibility_reason = cleaned.career_eligibility_reason
    job.role_category = cleaned.role_category
    job.target_relevance_score = cleaned.target_relevance_score


def clean_existing_raw_jobs(db: Session) -> int:
    jobs = list(db.scalars(select(RawJob)).all())

    for job in jobs:
        apply_cleaned_fields(job)

    db.commit()
    return len(jobs)
