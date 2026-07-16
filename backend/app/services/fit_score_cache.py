from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_fit_score import JobFitScore
from app.models.raw_job import RawJob
from app.models.user_profile import UserProfile
from app.services.fit_score import (
    FitScoreResult,
    calculate_fit_score,
    get_job_skills_by_job_id,
)


SCORING_VERSION = "2026-07-16-v1"


def profile_signature(profile: UserProfile) -> str:
    values = {
        "resume_text": profile.resume_text,
        "target_roles": profile.target_roles,
        "target_locations": profile.target_locations,
        "extracted_skills_json": profile.extracted_skills_json,
        "manual_skills_json": profile.manual_skills_json,
        "domain_experience_json": profile.domain_experience_json,
    }
    return _hash_values(values)


def job_signature(job: RawJob) -> str:
    values = {
        "content_hash": job.content_hash,
        "description": job.description if not job.content_hash else None,
        "title": job.title,
        "location": job.location,
        "normalized_title": job.normalized_title,
        "normalized_location": job.normalized_location,
        "work_mode": job.work_mode,
        "seniority": job.seniority,
        "required_experience_years": job.required_experience_years,
        "career_eligible": job.career_eligible,
        "career_eligibility_reason": job.career_eligibility_reason,
        "role_category": job.role_category,
    }
    return _hash_values(values)


def get_cached_fit_scores(
    db: Session,
    jobs: list[RawJob],
    profile: Optional[UserProfile],
) -> dict[int, FitScoreResult]:
    if not profile or not jobs:
        return {}

    profile_hash = profile_signature(profile)
    job_ids = [job.id for job in jobs]
    cached_rows = {
        row.raw_job_id: row
        for row in db.scalars(
            select(JobFitScore).where(
                JobFitScore.user_id == profile.user_id,
                JobFitScore.raw_job_id.in_(job_ids),
            )
        ).all()
    }
    results: dict[int, FitScoreResult] = {}
    jobs_to_calculate: list[RawJob] = []

    for job in jobs:
        cached = cached_rows.get(job.id)
        if (
            cached
            and cached.profile_id == profile.id
            and cached.profile_signature == profile_hash
            and cached.job_signature == job_signature(job)
            and cached.scoring_version == SCORING_VERSION
        ):
            result = _deserialize_result(cached.result_json)
            if result:
                results[job.id] = result
                continue

        jobs_to_calculate.append(job)

    if not jobs_to_calculate:
        return results

    skills_by_job_id = get_job_skills_by_job_id(
        db,
        [job.id for job in jobs_to_calculate],
    )
    calculated_at = datetime.utcnow()

    for job in jobs_to_calculate:
        result = calculate_fit_score(
            job,
            skills_by_job_id.get(job.id, []),
            profile,
        )
        if not result:
            continue

        cached = cached_rows.get(job.id)
        if not cached:
            cached = JobFitScore(
                user_id=profile.user_id,
                raw_job_id=job.id,
                profile_id=profile.id,
                profile_signature=profile_hash,
                job_signature=job_signature(job),
                scoring_version=SCORING_VERSION,
                fit_score=result.fit_score,
                match_level=result.match_level,
                result_json="{}",
            )
            db.add(cached)

        cached.profile_id = profile.id
        cached.profile_signature = profile_hash
        cached.job_signature = job_signature(job)
        cached.scoring_version = SCORING_VERSION
        cached.fit_score = result.fit_score
        cached.match_level = result.match_level
        cached.result_json = json.dumps(asdict(result), sort_keys=True)
        cached.calculated_at = calculated_at
        results[job.id] = result

    db.commit()
    return results


def _deserialize_result(value: str) -> Optional[FitScoreResult]:
    try:
        return FitScoreResult(**json.loads(value))
    except (json.JSONDecodeError, TypeError):
        return None


def _hash_values(values: dict[str, object]) -> str:
    payload = json.dumps(values, sort_keys=True, default=str, ensure_ascii=True)
    return sha256(payload.encode("utf-8")).hexdigest()
