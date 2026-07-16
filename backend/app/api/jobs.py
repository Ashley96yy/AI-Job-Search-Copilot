from datetime import datetime, time, timedelta, timezone
from hashlib import sha256
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, delete, distinct, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.application import Application
from app.models.collection_run import CollectionRun
from app.models.cover_letter import CoverLetter
from app.models.job_fit_score import JobFitScore
from app.models.job_skill import JobSkill
from app.models.job_source_map import JobSourceMap
from app.models.raw_job import RawJob
from app.models.user import User
from app.models.user_job_state import UserJobState
from app.schemas.collector import (
    CollectionRunRead,
    CollectJobsRequest,
    CollectJobsResponse,
    CompanySource,
    SyncAllJobsRequest,
)
from app.schemas.job import (
    DeduplicationSummary,
    DistributionItem,
    FitScoreDimension,
    JobDetail,
    JobDiscoverySession,
    JobRead,
    JobSkillRead,
    JobStateRead,
    JobStateUpdate,
    ManualJobCreate,
    MarketSummary,
    PaginatedJobs,
)
from app.services.collectors.company_registry import TARGET_COMPANIES
from app.services.collectors.collector_runner import COLLECTORS
from app.services.collection_runs import (
    CollectionRunConflict,
    execute_collection_run,
    recover_stale_collection_runs,
)
from app.services.deduplication import count_canonical_jobs, deduplicate_jobs
from app.services.fit_score import (
    FitScoreResult,
    get_latest_profile,
    recommend_application_action,
)
from app.services.fit_score_cache import (
    SCORING_VERSION,
    get_cached_fit_scores,
    profile_signature,
)
from app.services.job_cleaning import apply_cleaned_fields, clean_existing_raw_jobs
from app.services.skill_extraction import extract_skills_for_all_jobs, extract_skills_for_job


router = APIRouter(prefix="/jobs", tags=["jobs"])
DEFAULT_USER_ID = 1


@router.get("/sources", response_model=list[CompanySource])
def list_job_sources() -> list[dict[str, str]]:
    return TARGET_COMPANIES


def get_distribution(
    db: Session,
    column,
    limit: int = 10,
    filters: Optional[list] = None,
) -> list[DistributionItem]:
    statement = (
        select(column, func.count(RawJob.id))
        .group_by(column)
        .order_by(func.count(RawJob.id).desc())
        .limit(limit)
    )

    if filters:
        statement = statement.where(*filters)

    rows = db.execute(statement).all()

    return [
        DistributionItem(name=row[0] or "unknown", count=row[1])
        for row in rows
    ]


def get_skill_distribution(
    db: Session,
    limit: int = 10,
    filters: Optional[list] = None,
) -> list[DistributionItem]:
    statement = (
        select(JobSkill.skill, func.count(JobSkill.id))
        .join(RawJob, JobSkill.raw_job_id == RawJob.id)
        .group_by(JobSkill.skill)
        .order_by(func.count(JobSkill.id).desc())
        .limit(limit)
    )

    if filters:
        statement = statement.where(*filters)

    rows = db.execute(statement).all()

    return [
        DistributionItem(name=row[0] or "unknown", count=row[1])
        for row in rows
    ]


def get_weekly_postings(
    db: Session,
    filters: Optional[list] = None,
    limit: int = 12,
) -> list[DistributionItem]:
    weekly_counts = get_weekly_counts(db, filters)

    return [
        DistributionItem(name=label, count=weekly_counts[label])
        for label in sorted(weekly_counts)[-limit:]
    ]


def get_weekly_counts(
    db: Session,
    filters: Optional[list] = None,
) -> dict[str, int]:
    statement = select(RawJob.date_posted, RawJob.date_collected)

    if filters:
        statement = statement.where(*filters)

    rows = db.execute(statement).all()
    weekly_counts: dict[str, int] = {}

    for date_posted, date_collected in rows:
        date_value = date_posted or date_collected
        if not isinstance(date_value, datetime):
            continue

        year, week, _ = date_value.isocalendar()
        label = f"{year}-W{week:02d}"
        weekly_counts[label] = weekly_counts.get(label, 0) + 1

    return weekly_counts


def calculate_week_over_week_change(
    this_week_count: int,
    last_week_count: int,
) -> Optional[float]:
    if last_week_count == 0:
        return None

    return round((this_week_count - last_week_count) / last_week_count, 4)


def build_job_read(
    job: RawJob,
    fit_score: Optional[FitScoreResult],
    user_state: Optional[UserJobState] = None,
) -> JobRead:
    recommendation = recommend_application_action(job, fit_score)
    updates = {
        "posting_age_days": calculate_posting_age_days(job.date_posted),
        "freshness_bucket": calculate_freshness_bucket(job.date_posted),
        "is_viewed": user_state is not None and user_state.viewed_at is not None,
        "is_hidden": user_state is not None and user_state.hidden_at is not None,
        "viewed_at": user_state.viewed_at if user_state else None,
        "hidden_at": user_state.hidden_at if user_state else None,
        "application_recommendation": recommendation.key,
        "application_recommendation_label": recommendation.label,
        "application_recommendation_reason": recommendation.reason,
    }

    if fit_score:
        updates.update({
            "fit_score": fit_score.fit_score,
            "match_level": fit_score.match_level,
            "matched_skills": fit_score.matched_skills,
            "missing_skills": fit_score.missing_skills,
            "matched_required_skills": fit_score.matched_required_skills,
            "missing_required_skills": fit_score.missing_required_skills,
            "matched_preferred_skills": fit_score.matched_preferred_skills,
            "missing_preferred_skills": fit_score.missing_preferred_skills,
            "fit_breakdown": [
                FitScoreDimension.model_validate(item)
                for item in fit_score.fit_breakdown
            ],
            "fit_notes": fit_score.fit_notes,
        })

    return JobRead.model_validate(job).model_copy(update=updates)


def get_user_job_states(
    db: Session,
    job_ids: list[int],
) -> dict[int, UserJobState]:
    if not job_ids:
        return {}

    states = db.scalars(
        select(UserJobState).where(
            UserJobState.user_id == DEFAULT_USER_ID,
            UserJobState.raw_job_id.in_(job_ids),
        )
    ).all()
    return {state.raw_job_id: state for state in states}


def build_job_state_read(job_id: int, state: Optional[UserJobState]) -> JobStateRead:
    return JobStateRead(
        raw_job_id=job_id,
        is_viewed=state is not None and state.viewed_at is not None,
        is_hidden=state is not None and state.hidden_at is not None,
        viewed_at=state.viewed_at if state else None,
        hidden_at=state.hidden_at if state else None,
    )


def normalize_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def calculate_posting_age_days(date_posted: Optional[datetime]) -> Optional[int]:
    if not date_posted:
        return None

    return max((datetime.utcnow().date() - date_posted.date()).days, 0)


def calculate_freshness_bucket(date_posted: Optional[datetime]) -> str:
    age_days = calculate_posting_age_days(date_posted)
    if age_days is None:
        return "Unknown"
    if age_days <= 30:
        return "Fresh"
    if age_days <= 90:
        return "Recent"
    if age_days <= 180:
        return "Aging"
    return "Stale / Evergreen"


def normalize_match_level(value: str) -> str:
    cleaned = value.strip().replace("_", " ").replace("-", " ").lower()
    levels = {
        "strong match": "Strong Match",
        "good match": "Good Match",
        "stretch match": "Stretch Match",
        "low match": "Low Match",
    }
    return levels.get(cleaned, value)


def normalize_freshness(value: str) -> str:
    cleaned = value.strip().replace("_", " ").replace("-", " ").lower()
    buckets = {
        "fresh": "Fresh",
        "recent": "Recent",
        "aging": "Aging",
        "stale": "Stale / Evergreen",
        "stale evergreen": "Stale / Evergreen",
        "unknown": "Unknown",
    }
    return buckets.get(cleaned, value)


def apply_freshness_filter(statement, freshness: Optional[str]):
    if not freshness:
        return statement

    expected = normalize_freshness(freshness)
    now = datetime.utcnow()
    fresh_cutoff = now - timedelta(days=30)
    recent_cutoff = now - timedelta(days=90)
    aging_cutoff = now - timedelta(days=180)

    if expected == "Fresh":
        return statement.where(RawJob.date_posted >= fresh_cutoff)
    if expected == "Recent":
        return statement.where(
            RawJob.date_posted >= recent_cutoff,
            RawJob.date_posted < fresh_cutoff,
        )
    if expected == "Aging":
        return statement.where(
            RawJob.date_posted >= aging_cutoff,
            RawJob.date_posted < recent_cutoff,
        )
    if expected == "Stale / Evergreen":
        return statement.where(RawJob.date_posted < aging_cutoff)
    if expected == "Unknown":
        return statement.where(RawJob.date_posted.is_(None))

    return statement


@router.get("/market-summary", response_model=MarketSummary)
def get_market_summary(
    us_only: Optional[bool] = None,
    career_eligible_only: bool = False,
    role_category: Optional[str] = None,
    min_target_relevance: Optional[int] = None,
    max_posting_age_days: Optional[int] = None,
    db: Session = Depends(get_db),
) -> MarketSummary:
    filters = [
        RawJob.is_user_added.is_(False),
        RawJob.is_active.is_(True),
    ]
    if us_only is True:
        filters.append(RawJob.is_us_based.is_(True))
    if career_eligible_only:
        filters.append(RawJob.career_eligible.is_(True))
    if role_category:
        filters.append(RawJob.role_category == role_category)
    if min_target_relevance is not None:
        filters.append(RawJob.target_relevance_score >= min_target_relevance)
    if max_posting_age_days is not None:
        cutoff = datetime.utcnow() - timedelta(days=max_posting_age_days)
        filters.append(RawJob.date_posted >= cutoff)

    total_statement = select(func.count(RawJob.id))
    remote_statement = select(func.count(RawJob.id)).where(RawJob.work_mode == "remote")
    company_statement = select(func.count(distinct(RawJob.company)))

    if filters:
        total_statement = total_statement.where(*filters)
        remote_statement = remote_statement.where(*filters)
        company_statement = company_statement.where(*filters)

    total_jobs = db.scalar(total_statement) or 0
    us_statement = select(func.count(RawJob.id)).where(
        RawJob.is_user_added.is_(False),
        RawJob.is_active.is_(True),
        RawJob.is_us_based.is_(True),
    )
    if role_category:
        us_statement = us_statement.where(RawJob.role_category == role_category)
    us_jobs = db.scalar(us_statement) or 0
    canonical_jobs = count_canonical_jobs(db, filters)
    duplicate_jobs = max(total_jobs - canonical_jobs, 0) if canonical_jobs else 0
    duplicate_rate = round(duplicate_jobs / total_jobs, 4) if total_jobs and canonical_jobs else 0.0
    remote_jobs = db.scalar(remote_statement) or 0
    companies = db.scalar(company_statement) or 0
    role_categories = get_distribution(db, RawJob.role_category, filters=filters)
    weekly_counts = get_weekly_counts(db, filters)
    sorted_weeks = sorted(weekly_counts)
    this_week_count = weekly_counts[sorted_weeks[-1]] if sorted_weeks else 0
    last_week_count = weekly_counts[sorted_weeks[-2]] if len(sorted_weeks) >= 2 else 0

    return MarketSummary(
        total_jobs=total_jobs,
        us_jobs=us_jobs,
        canonical_jobs=canonical_jobs,
        duplicate_rate=duplicate_rate,
        remote_jobs=remote_jobs,
        companies=companies,
        new_jobs_this_week=this_week_count,
        new_jobs_last_week=last_week_count,
        week_over_week_change=calculate_week_over_week_change(
            this_week_count,
            last_week_count,
        ),
        active_weeks=len(sorted_weeks),
        top_role_category=role_categories[0].name if role_categories else None,
        role_categories=role_categories,
        work_modes=get_distribution(db, RawJob.work_mode, filters=filters),
        seniorities=get_distribution(db, RawJob.seniority, filters=filters),
        top_skills=get_skill_distribution(db, filters=filters),
        top_locations=get_distribution(db, RawJob.normalized_location, filters=filters),
        top_states=get_distribution(db, RawJob.state, filters=filters),
        weekly_postings=get_weekly_postings(db, filters=filters),
    )


@router.get("", response_model=PaginatedJobs)
def list_jobs(
    source: Optional[str] = None,
    company: Optional[str] = None,
    location: Optional[str] = None,
    country: Optional[str] = None,
    state: Optional[str] = None,
    us_only: Optional[bool] = None,
    career_eligible_only: bool = False,
    min_target_relevance: Optional[int] = None,
    max_posting_age_days: Optional[int] = None,
    freshness: Optional[str] = None,
    work_mode: Optional[str] = None,
    seniority: Optional[str] = None,
    entry_fit_level: Optional[str] = None,
    role_category: Optional[str] = None,
    search: Optional[str] = None,
    title_search: Optional[str] = None,
    sort_by: str = "first_seen",
    match_level: Optional[str] = None,
    min_fit_score: Optional[int] = None,
    has_fit_score: Optional[bool] = None,
    unseen_only: bool = False,
    hidden_only: bool = False,
    new_since: Optional[datetime] = None,
    active_only: bool = True,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    limit: Optional[int] = Query(default=None, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PaginatedJobs:
    effective_page_size = limit or page_size
    state_join = and_(
        UserJobState.raw_job_id == RawJob.id,
        UserJobState.user_id == DEFAULT_USER_ID,
    )
    statement = (
        select(RawJob)
        .outerjoin(UserJobState, state_join)
        .where(
            or_(
                RawJob.owner_user_id.is_(None),
                RawJob.owner_user_id == DEFAULT_USER_ID,
            )
        )
    )

    if hidden_only:
        statement = statement.where(UserJobState.hidden_at.is_not(None))
    else:
        statement = statement.where(UserJobState.hidden_at.is_(None))

    if unseen_only:
        statement = statement.where(UserJobState.viewed_at.is_(None))

    if new_since:
        statement = statement.where(
            RawJob.first_seen_at >= normalize_utc_datetime(new_since)
        )

    if active_only:
        statement = statement.where(RawJob.is_active.is_(True))

    if source:
        statement = statement.where(RawJob.source == source)

    if company:
        statement = statement.where(RawJob.company.ilike(f"%{company}%"))

    if location:
        statement = statement.where(
            or_(
                RawJob.location.ilike(f"%{location}%"),
                RawJob.normalized_location.ilike(f"%{location}%"),
            )
        )

    if country:
        statement = statement.where(RawJob.country == country)

    if state:
        statement = statement.where(RawJob.state.ilike(f"%{state}%"))

    if us_only is True:
        statement = statement.where(RawJob.is_us_based.is_(True))

    if career_eligible_only:
        statement = statement.where(RawJob.career_eligible.is_(True))

    if min_target_relevance is not None:
        statement = statement.where(RawJob.target_relevance_score >= min_target_relevance)

    if max_posting_age_days is not None:
        cutoff = datetime.utcnow() - timedelta(days=max_posting_age_days)
        statement = statement.where(RawJob.date_posted >= cutoff)

    if work_mode:
        statement = statement.where(RawJob.work_mode == work_mode)

    if seniority:
        statement = statement.where(RawJob.seniority == seniority)

    if entry_fit_level:
        statement = statement.where(RawJob.entry_fit_level == entry_fit_level)

    if role_category:
        statement = statement.where(RawJob.role_category == role_category)

    if title_search:
        title_pattern = f"%{title_search}%"
        statement = statement.where(
            or_(
                RawJob.title.ilike(title_pattern),
                RawJob.normalized_title.ilike(title_pattern),
            )
        )

    if search:
        search_pattern = f"%{search}%"
        statement = statement.where(
            or_(
                RawJob.title.ilike(search_pattern),
                RawJob.normalized_title.ilike(search_pattern),
                RawJob.company.ilike(search_pattern),
                RawJob.location.ilike(search_pattern),
                RawJob.normalized_location.ilike(search_pattern),
                RawJob.description.ilike(search_pattern),
            )
        )

    statement = apply_freshness_filter(statement, freshness)
    profile = get_latest_profile(db)
    uses_fit_cache_query = (
        sort_by == "fit_score"
        or bool(match_level)
        or min_fit_score is not None
        or has_fit_score is True
    )
    fit_filter_requested = (
        bool(match_level)
        or min_fit_score is not None
        or has_fit_score is True
    )

    if fit_filter_requested and not profile:
        return PaginatedJobs.create([], 0, page, effective_page_size)

    if profile and uses_fit_cache_query:
        candidate_jobs = list(db.scalars(statement).all())
        get_cached_fit_scores(db, candidate_jobs, profile)
        statement = statement.join(
            JobFitScore,
            and_(
                JobFitScore.raw_job_id == RawJob.id,
                JobFitScore.user_id == profile.user_id,
                JobFitScore.profile_id == profile.id,
                JobFitScore.profile_signature == profile_signature(profile),
                JobFitScore.scoring_version == SCORING_VERSION,
            ),
        )

        if match_level:
            statement = statement.where(
                JobFitScore.match_level == normalize_match_level(match_level)
            )
        if min_fit_score is not None:
            statement = statement.where(JobFitScore.fit_score >= min_fit_score)

    total = db.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    ) or 0

    if sort_by == "fit_score" and profile:
        statement = statement.order_by(
            JobFitScore.fit_score.desc(),
            RawJob.date_collected.desc(),
        )
    elif sort_by == "target_relevance":
        statement = statement.order_by(
            RawJob.target_relevance_score.desc(),
            RawJob.date_collected.desc(),
        )
    elif sort_by == "entry_fit":
        statement = statement.order_by(
            RawJob.entry_fit_score.desc(),
            RawJob.date_collected.desc(),
        )
    elif sort_by == "date_collected":
        statement = statement.order_by(RawJob.date_collected.desc())
    else:
        statement = statement.order_by(
            RawJob.first_seen_at.desc(),
            RawJob.date_collected.desc(),
        )

    statement = statement.offset((page - 1) * effective_page_size).limit(
        effective_page_size
    )
    jobs = list(db.scalars(statement).all())
    fit_scores = get_cached_fit_scores(db, jobs, profile)
    user_states = get_user_job_states(db, [job.id for job in jobs])
    job_reads = [
        build_job_read(job, fit_scores.get(job.id), user_states.get(job.id))
        for job in jobs
    ]
    return PaginatedJobs.create(
        job_reads,
        total,
        page,
        effective_page_size,
    )


@router.post("/manual", response_model=JobDetail)
def create_manual_job(
    payload: ManualJobCreate,
    db: Session = Depends(get_db),
) -> JobDetail:
    job_url = payload.job_url.strip() if payload.job_url else None
    source = f"manual_{payload.source}"

    if job_url:
        existing = db.scalar(
            select(RawJob).where(
                RawJob.owner_user_id == DEFAULT_USER_ID,
                RawJob.is_user_added.is_(True),
                RawJob.job_url == job_url,
            )
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail="This external job URL has already been added.",
            )

    external_job_id = sha256(
        f"{DEFAULT_USER_ID}|{job_url or uuid4().hex}".encode("utf-8")
    ).hexdigest()[:32]
    description = payload.description.strip() if payload.description else None
    job = RawJob(
        owner_user_id=DEFAULT_USER_ID,
        is_user_added=True,
        source=source,
        external_job_id=external_job_id,
        company=payload.company.strip(),
        title=payload.title.strip(),
        location=payload.location.strip() if payload.location else None,
        job_url=job_url,
        apply_url=job_url,
        description=description,
        content_hash=(
            sha256(description.encode("utf-8")).hexdigest() if description else None
        ),
        date_posted=(
            datetime.combine(payload.date_posted, time.min)
            if payload.date_posted
            else None
        ),
    )
    apply_cleaned_fields(job)
    db.add(job)
    db.flush()
    extract_skills_for_job(db, job)
    db.commit()
    db.refresh(job)

    return get_job(job.id, db)


@router.delete("/manual/{job_id}")
def delete_manual_job(
    job_id: int,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    job = db.scalar(
        select(RawJob).where(
            RawJob.id == job_id,
            RawJob.owner_user_id == DEFAULT_USER_ID,
            RawJob.is_user_added.is_(True),
        )
    )
    if not job:
        raise HTTPException(status_code=404, detail="Manual job not found")

    db.execute(
        delete(Application).where(
            Application.user_id == DEFAULT_USER_ID,
            Application.raw_job_id == job_id,
        )
    )
    db.execute(
        delete(CoverLetter).where(
            CoverLetter.user_id == DEFAULT_USER_ID,
            CoverLetter.raw_job_id == job_id,
        )
    )
    db.execute(delete(JobSkill).where(JobSkill.raw_job_id == job_id))
    db.execute(delete(JobSourceMap).where(JobSourceMap.raw_job_id == job_id))
    db.execute(
        delete(UserJobState).where(UserJobState.raw_job_id == job_id)
    )
    db.delete(job)
    db.commit()

    return {"status": "deleted", "job_id": job_id}


@router.post("/deduplicate", response_model=DeduplicationSummary)
def deduplicate_raw_jobs(db: Session = Depends(get_db)) -> DeduplicationSummary:
    result = deduplicate_jobs(db)
    return DeduplicationSummary(
        raw_jobs=result.raw_jobs,
        canonical_jobs=result.canonical_jobs,
        duplicate_jobs=result.duplicate_jobs,
        duplicate_rate=result.duplicate_rate,
        mapped_jobs=result.mapped_jobs,
    )


@router.get("/collection-runs", response_model=list[CollectionRunRead])
def list_collection_runs(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[CollectionRun]:
    recover_stale_collection_runs(db)
    safe_limit = max(1, min(limit, 100))
    return list(
        db.scalars(
            select(CollectionRun)
            .options(selectinload(CollectionRun.board_runs))
            .order_by(CollectionRun.started_at.desc(), CollectionRun.id.desc())
            .limit(safe_limit)
        ).all()
    )


@router.post("/sync-all", response_model=list[CollectionRunRead])
async def sync_all_job_sources(
    request: Optional[SyncAllJobsRequest] = None,
    db: Session = Depends(get_db),
) -> list[CollectionRun]:
    request = request or SyncAllJobsRequest()
    sources = sorted({company["source"] for company in TARGET_COMPANIES})
    runs: list[CollectionRun] = []

    for source in sources:
        try:
            run = await execute_collection_run(
                db,
                source=source,
                max_jobs_per_board=request.max_jobs_per_board,
                trigger="sync_all",
            )
        except CollectionRunConflict as exc:
            run = exc.active_run
        runs.append(run)

    if any(run.status in {"success", "partial_success"} for run in runs):
        deduplicate_jobs(db)

    return runs


@router.post("/discovery-session", response_model=JobDiscoverySession)
def start_job_discovery_session(
    db: Session = Depends(get_db),
) -> JobDiscoverySession:
    user = db.get(User, DEFAULT_USER_ID)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    session_started_at = datetime.utcnow()
    previous_visit_at = user.jobs_last_visited_at
    new_since = previous_visit_at or (session_started_at - timedelta(days=7))
    user.jobs_last_visited_at = session_started_at
    db.commit()

    return JobDiscoverySession(
        previous_visit_at=previous_visit_at,
        new_since=new_since,
        session_started_at=session_started_at,
    )


@router.put("/{job_id}/state", response_model=JobStateRead)
def update_job_state(
    job_id: int,
    payload: JobStateUpdate,
    db: Session = Depends(get_db),
) -> JobStateRead:
    if payload.viewed is None and payload.hidden is None:
        raise HTTPException(
            status_code=400,
            detail="Provide viewed or hidden state.",
        )

    job = db.get(RawJob, job_id)
    if not job or (
        job.owner_user_id is not None and job.owner_user_id != DEFAULT_USER_ID
    ):
        raise HTTPException(status_code=404, detail="Job not found")

    state = db.scalar(
        select(UserJobState).where(
            UserJobState.user_id == DEFAULT_USER_ID,
            UserJobState.raw_job_id == job_id,
        )
    )
    if not state:
        state = UserJobState(
            user_id=DEFAULT_USER_ID,
            raw_job_id=job_id,
        )
        db.add(state)

    now = datetime.utcnow()
    if payload.viewed is not None:
        state.viewed_at = now if payload.viewed else None
    if payload.hidden is not None:
        state.hidden_at = now if payload.hidden else None
        if payload.hidden and state.viewed_at is None:
            state.viewed_at = now

    db.commit()
    db.refresh(state)
    return build_job_state_read(job_id, state)


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobDetail:
    job = db.get(RawJob, job_id)

    if not job or (
        job.owner_user_id is not None and job.owner_user_id != DEFAULT_USER_ID
    ):
        raise HTTPException(status_code=404, detail="Job not found")

    skills = list(
        db.scalars(
            select(JobSkill)
            .where(JobSkill.raw_job_id == job.id)
            .order_by(JobSkill.category, JobSkill.skill)
        ).all()
    )
    profile = get_latest_profile(db)
    fit_score = get_cached_fit_scores(db, [job], profile).get(job.id)
    recommendation = recommend_application_action(job, fit_score)
    user_state = db.scalar(
        select(UserJobState).where(
            UserJobState.user_id == DEFAULT_USER_ID,
            UserJobState.raw_job_id == job.id,
        )
    )
    updates = {
        "skills": [JobSkillRead.model_validate(skill) for skill in skills],
        "posting_age_days": calculate_posting_age_days(job.date_posted),
        "freshness_bucket": calculate_freshness_bucket(job.date_posted),
        "is_viewed": user_state is not None and user_state.viewed_at is not None,
        "is_hidden": user_state is not None and user_state.hidden_at is not None,
        "viewed_at": user_state.viewed_at if user_state else None,
        "hidden_at": user_state.hidden_at if user_state else None,
        "application_recommendation": recommendation.key,
        "application_recommendation_label": recommendation.label,
        "application_recommendation_reason": recommendation.reason,
    }

    if fit_score:
        updates.update(
            {
                "fit_score": fit_score.fit_score,
                "match_level": fit_score.match_level,
                "matched_skills": fit_score.matched_skills,
                "missing_skills": fit_score.missing_skills,
                "matched_required_skills": fit_score.matched_required_skills,
                "missing_required_skills": fit_score.missing_required_skills,
                "matched_preferred_skills": fit_score.matched_preferred_skills,
                "missing_preferred_skills": fit_score.missing_preferred_skills,
                "fit_breakdown": [
                    FitScoreDimension.model_validate(item)
                    for item in fit_score.fit_breakdown
                ],
                "fit_notes": fit_score.fit_notes,
            }
        )

    return JobDetail.model_validate(job).model_copy(update=updates)


@router.post("/collect", response_model=CollectJobsResponse)
async def collect_jobs(
    request: Optional[CollectJobsRequest] = None,
    db: Session = Depends(get_db),
) -> CollectJobsResponse:
    request = request or CollectJobsRequest()

    if request.source not in COLLECTORS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported collector source: {request.source}",
        )

    try:
        run = await execute_collection_run(
            db,
            source=request.source,
            board_tokens=request.board_tokens,
            keywords=request.keywords,
            max_jobs_per_board=request.max_jobs_per_board,
            trigger="manual",
        )
    except CollectionRunConflict as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(exc),
                "active_run_id": exc.active_run.id,
                "source": exc.active_run.source,
            },
        ) from exc
    if run.status == "failed":
        raise HTTPException(
            status_code=502,
            detail=f"Collector failed: {run.error_message}",
        )

    return CollectJobsResponse(
        source=run.source,
        status=run.status,
        boards_requested=run.boards_requested,
        fetched=run.fetched,
        matched=run.fetched,
        inserted=run.inserted,
        updated=run.updated,
        reactivated=run.reactivated,
        boards_reconciled=run.boards_reconciled,
        missing_observations=run.missing_observations,
        closed=run.closed,
        failed_boards=[
            board_run.board_token
            for board_run in run.board_runs
            if board_run.status == "failed"
        ],
    )


@router.post("/clean")
def clean_jobs(db: Session = Depends(get_db)) -> dict[str, object]:
    cleaned_count = clean_existing_raw_jobs(db)
    return {"status": "ok", "cleaned": cleaned_count}


@router.post("/extract-skills")
def extract_skills(db: Session = Depends(get_db)) -> dict[str, object]:
    extracted_count = extract_skills_for_all_jobs(db)
    return {"status": "ok", "extracted": extracted_count}
