import re
from dataclasses import asdict, dataclass, field
from typing import Optional


SECTION_HEADERS = [
    "work experience",
    "experience",
    "projects",
    "education",
    "skills",
    "skills & credentials",
]


@dataclass(frozen=True)
class ParsedWorkExperience:
    company: str
    title: str
    period: Optional[str] = None
    location: Optional[str] = None
    bullets: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ParsedEducation:
    school: str
    degree: Optional[str] = None
    period: Optional[str] = None


@dataclass(frozen=True)
class ParsedDomainExperience:
    domain: str
    evidence: list[str] = field(default_factory=list)


def parse_profile_sections(resume_text: str) -> dict[str, list[dict[str, object]]]:
    return {
        "work_experience": [
            asdict(item) for item in parse_work_experience(resume_text)
        ],
        "education": [
            asdict(item) for item in parse_education(resume_text)
        ],
        "domain_experience": [
            asdict(item) for item in parse_domain_experience(resume_text)
        ],
    }


def normalize_resume_text(resume_text: str) -> str:
    normalized = resume_text.replace("\r", "\n")
    boundary_terms = [
        "Work Experience",
        "Projects",
        "Education",
        "Skills & Credentials",
        "Bank of China",
        "Allianz Global Corporate & Specialty",
        "One Smart International Education Group",
        "LinkedIn-Inspired Event-Driven Platform",
        "Flight Delay Analytics & Prediction Platform",
        "Citi Bike Data Platform",
        "Citi Bike Analytics Platform",
    ]
    for term in boundary_terms:
        normalized = re.sub(rf"\s+({re.escape(term)})\b", rf"\n\1", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def split_sentences_and_bullets(text: str) -> list[str]:
    normalized = normalize_resume_text(text)
    parts = re.split(r"(?:\n|•)+", normalized)
    return [part.strip(" -\t") for part in parts if part.strip(" -\t")]


def parse_work_experience(resume_text: str) -> list[ParsedWorkExperience]:
    lines = split_sentences_and_bullets(resume_text)
    experiences: list[ParsedWorkExperience] = []
    current_company = ""
    current_title = ""
    current_location = None
    current_period = None
    current_bullets: list[str] = []

    def flush_current() -> None:
        nonlocal current_company, current_title, current_location, current_period, current_bullets
        if current_company and current_title:
            experiences.append(
                ParsedWorkExperience(
                    company=current_company,
                    title=current_title,
                    location=current_location,
                    period=current_period,
                    bullets=current_bullets[:5],
                )
            )
        current_company = ""
        current_title = ""
        current_location = None
        current_period = None
        current_bullets = []

    for index, line in enumerate(lines):
        lower = line.lower()
        if lower in SECTION_HEADERS:
            if lower in {"projects", "education", "skills", "skills & credentials"}:
                break
            continue

        parsed_header = parse_experience_header(line)
        if parsed_header:
            flush_current()
            current_company = parsed_header.company
            current_title = parsed_header.title
            current_location = parsed_header.location
            current_period = parsed_header.period
            continue

        if looks_like_company_line(line):
            flush_current()
            current_company, current_location = split_company_location(line)
            next_line = lines[index + 1] if index + 1 < len(lines) else ""
            if next_line and looks_like_title_line(next_line):
                current_title, current_period = split_title_period(next_line)
            continue

        if current_company and not current_title and looks_like_title_line(line):
            current_title, current_period = split_title_period(line)
            continue

        if current_company and current_title and len(line) > 35:
            current_bullets.append(line)

    flush_current()
    return experiences[:8]


def parse_experience_header(line: str) -> Optional[ParsedWorkExperience]:
    line = re.sub(r"^Work Experience\s+", "", line.strip(), flags=re.IGNORECASE)
    date_pattern = (
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"\s+20\d{2}\s*[–-]\s*"
        r"((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+20\d{2}|Present)"
    )
    date_match = re.search(date_pattern, line, flags=re.IGNORECASE)
    if not date_match:
        return None

    before_date = line[: date_match.start()].strip()
    period = date_match.group(0).strip()
    known_titles = [
        "Senior Consultant, Enterprise Risk",
        "Risk Management Intern",
        "Claims Analytics Intern",
        "Strategy Intern",
    ]
    for known_title in known_titles:
        if known_title in before_date:
            company_location = before_date.split(known_title, maxsplit=1)[0].strip()
            company, location = split_company_location(company_location)
            return ParsedWorkExperience(
                company=company,
                title=known_title,
                location=location,
                period=period,
            )

    title_pattern = (
        r"(Senior Consultant[^,]*(?:,\s*[^,]+)?|"
        r"Risk Management Intern|"
        r"Claims Analytics Intern|"
        r"Strategy Intern|"
        r"[A-Z][A-Za-z /&-]+ Analyst|"
        r"[A-Z][A-Za-z /&-]+ Engineer|"
        r"[A-Z][A-Za-z /&-]+ Scientist|"
        r"[A-Z][A-Za-z /&-]+ Intern)"
    )
    title_matches = list(re.finditer(title_pattern, before_date))
    if not title_matches:
        return None

    title_match = title_matches[-1]
    company_location = before_date[: title_match.start()].strip()
    title = title_match.group(0).strip()
    company, location = split_company_location(company_location)
    if not company or not title:
        return None

    return ParsedWorkExperience(
        company=company,
        title=title,
        location=location,
        period=period,
    )


def looks_like_company_line(line: str) -> bool:
    if len(line) > 140 or len(line) < 3:
        return False
    if re.search(r"\b(university|college|school)\b", line, flags=re.IGNORECASE):
        return False
    company_terms = [
        "bank",
        "consulting",
        "group",
        "global",
        "corporate",
        "company",
        "allianz",
        "ernst",
        "china",
        "citi",
    ]
    return (
        any(term in line.lower() for term in company_terms)
        or bool(re.search(r"\b(inc|llc|ltd|corp)\b", line, flags=re.IGNORECASE))
    )


def looks_like_title_line(line: str) -> bool:
    title_terms = [
        "analyst",
        "consultant",
        "engineer",
        "scientist",
        "intern",
        "manager",
        "associate",
        "developer",
    ]
    return any(term in line.lower() for term in title_terms)


def split_company_location(line: str) -> tuple[str, Optional[str]]:
    location_patterns = [
        "Shanghai, China",
        "Singapore",
        "San Jose, CA",
        "New York, NY",
        "Bay Area",
    ]
    for location in location_patterns:
        if location in line:
            return line.replace(location, "").strip(" ,-"), location

    parts = re.split(r"\s{2,}|\s+[|]\s+", line.strip(), maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return line.strip(), None


def split_title_period(line: str) -> tuple[str, Optional[str]]:
    match = re.search(
        r"(.+?)\s+((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4}).+)$",
        line.strip(),
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1).strip(" ,-"), match.group(2).strip()
    return line.strip(), None


def parse_education(resume_text: str) -> list[ParsedEducation]:
    normalized = normalize_resume_text(resume_text)
    known_schools = [
        "San José State University",
        "San Jose State University",
        "National University of Singapore",
        "Jilin University",
    ]
    for school in known_schools:
        normalized = re.sub(rf"\s+({re.escape(school)})\b", rf"\n\1", normalized)
    lines = split_sentences_and_bullets(normalized)
    education: list[ParsedEducation] = []

    for line in lines:
        if not re.search(r"\b(university|college|school)\b", line, flags=re.IGNORECASE):
            continue
        degree_match = re.search(
            r"\b(M\.?S\.?|B\.?S\.?|Master|Bachelor|Ph\.?D\.?).*",
            line,
            flags=re.IGNORECASE,
        )
        period_match = re.search(r"\b(20\d{2}|19\d{2}|Expected\s+\w+\s+20\d{2})\b", line)
        school = line
        if "—" in line:
            school = line.split("—", maxsplit=1)[0].strip()
        elif "-" in line:
            school = line.split("-", maxsplit=1)[0].strip()
        education.append(
            ParsedEducation(
                school=school,
                degree=degree_match.group(0).strip() if degree_match else None,
                period=period_match.group(0).strip() if period_match else None,
            )
        )

    return education[:5]


def parse_domain_experience(resume_text: str) -> list[ParsedDomainExperience]:
    text = normalize_resume_text(resume_text)
    domain_terms = {
        "Finance": ["finance", "financial", "valuation", "cfa", "quantitative finance"],
        "Risk": ["risk", "credit risk", "model risk", "frm"],
        "Analytics": ["analytics", "dashboard", "kpi", "metrics"],
        "Data Engineering": ["airflow", "dbt", "snowflake", "pipeline", "pyspark"],
        "AI / ML": ["machine learning", "mlflow", "prediction"],
    }
    sentences = [
        sentence
        for sentence in split_sentences_and_bullets(text)
        if len(sentence) > 25 and "@" not in sentence
    ]
    domains: list[ParsedDomainExperience] = []

    for domain, terms in domain_terms.items():
        evidence = [
            sentence
            for sentence in sentences
            if any(term in sentence.lower() for term in terms)
        ][:4]
        if evidence:
            domains.append(ParsedDomainExperience(domain=domain, evidence=evidence))

    return domains
