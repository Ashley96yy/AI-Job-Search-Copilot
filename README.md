# AI Job Search Copilot

Human-in-the-loop job search assistant for entry-level data, risk, finance analytics, and AI analytics candidates.

The project collects compliant public job postings, stores raw job data, cleans and deduplicates roles, extracts requirements, analyzes market trends, compares jobs with a candidate profile, and helps prepare application materials without auto-submitting applications.

## Project Structure

```text
backend/
  app/
    api/
    core/
    db/
    models/
    schemas/
    services/
      collectors/
frontend/
  src/
PROJECT_PLAN.md
```

## Backend

The backend is a FastAPI application.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

On startup, the backend initializes the local SQLite database and creates the `raw_jobs` table if it does not already exist.

### Collect Greenhouse Jobs

The first collector supports public Greenhouse job boards. Greenhouse Job Board GET endpoints are public and do not require authentication.

Collect from the built-in Greenhouse company registry:

```bash
curl -X POST http://127.0.0.1:8000/jobs/collect \
  -H "Content-Type: application/json" \
  -d '{
    "source": "greenhouse",
    "max_jobs_per_board": 3
  }'
```

### Collect Ashby Jobs

Ashby's public Job Postings API is also supported. The built-in registry focuses on
US data, risk, fintech, and AI employers such as Ramp, SentiLink, Cardless, Quora,
and Netic.

```bash
curl -X POST http://127.0.0.1:8000/jobs/collect \
  -H "Content-Type: application/json" \
  -d '{
    "source": "ashby",
    "board_tokens": ["ramp", "sentilink"],
    "max_jobs_per_board": 100
  }'
```

Ashby collection keeps only listed public postings and stores primary and secondary
locations, workplace type, description, publication date, apply URL, and raw
compensation data when available.

### Sync All Sources

Run all configured Ashby, Greenhouse, and Lever sources from the Data Sources page or API:

```bash
curl -X POST http://127.0.0.1:8000/jobs/sync-all \
  -H "Content-Type: application/json" \
  -d '{"max_jobs_per_board": 100}'
```

Each source creates a persistent `collection_runs` record. One failed source does not
prevent the remaining sources from running. Read recent history with:

```bash
curl "http://127.0.0.1:8000/jobs/collection-runs?limit=20"
```

### Scheduled Collection

The scheduler-ready command synchronizes all configured sources, records each run, and
rebuilds active-job deduplication:

```bash
cd backend
./.venv/bin/python -m app.commands.sync_jobs --max-jobs-per-board 100
```

Example daily cron entry for 7:00 AM, using absolute paths:

```cron
0 7 * * * cd /absolute/path/to/JobSearchCopilot/backend && ./.venv/bin/python -m app.commands.sync_jobs --max-jobs-per-board 100 >> daily-sync.log 2>&1
```

The command exits nonzero when any source fails, while preserving successful source runs
and detailed failure records in `collection_runs`.

Each company board also creates a `collection_board_runs` record. A failed board no
longer discards jobs fetched from successful boards in the same source run:

- `success`: every requested board completed.
- `partial_success`: at least one board completed and at least one failed.
- `failed`: no requested board completed successfully.

Board token, company, fetched count, reconciliation eligibility, and error details are
available by expanding the Boards cell in Data Sources collection history. Scheduled
commands return a nonzero exit code for both failed and partially successful runs so the
failure remains visible to monitoring.

### Collection Concurrency and Recovery

- Only one `running` collection is allowed per source at the database level.
- UI, API, and scheduled CLI runs share the same concurrency constraint.
- Each completed company board updates `heartbeat_at` and `boards_completed`.
- A run without a heartbeat for more than 10 minutes is marked failed automatically.
- A timed-out process cannot later commit stale job results.
- The Data Sources page refreshes collection progress every 15 seconds and disables
  actions that would conflict with a running source.
- A single-source conflict returns HTTP `409`; Sync All skips sources already running.

You can optionally pass `board_tokens` if you want to collect from specific Greenhouse boards:

```bash
curl -X POST http://127.0.0.1:8000/jobs/collect \
  -H "Content-Type: application/json" \
  -d '{
    "source": "greenhouse",
    "board_tokens": ["stripe", "databricks"],
    "max_jobs_per_board": 5
  }'
```

You can also pass `keywords` if you want collection-time filtering, but the default approach is to collect broadly and filter later through the API/UI.

List built-in Greenhouse sources:

```bash
curl http://127.0.0.1:8000/jobs/sources
```

Then read saved raw jobs:

```bash
curl http://127.0.0.1:8000/jobs
```

Read one job with description and extracted skills:

```bash
curl http://127.0.0.1:8000/jobs/1
```

### Add Jobs from LinkedIn or Handshake

Restricted platforms are not scraped. Add a job manually from the Jobs page, or use the API:

```bash
curl -X POST http://127.0.0.1:8000/jobs/manual \
  -H "Content-Type: application/json" \
  -d '{
    "source": "linkedin",
    "company": "Example Company",
    "title": "Junior Data Analyst",
    "location": "Palo Alto, CA",
    "job_url": "https://www.linkedin.com/jobs/view/example",
    "date_posted": "2026-07-15",
    "description": "Paste the job description here."
  }'
```

Manual jobs are private to the current user. They use the same cleaning, skill extraction,
experience screening, and Fit Score pipeline as collected jobs, but are excluded from the
public market dashboard and deduplication statistics.

Filter saved jobs:

```bash
curl "http://127.0.0.1:8000/jobs?company=stripe&search=analytics&page=1&page_size=25"
```

`GET /jobs` returns a paginated object with `items`, `total`, `page`,
`page_size`, and `total_pages`. The legacy `limit` query parameter is still
accepted as a page-size override.

Fit Scores are cached in `job_fit_scores` by user, profile contents, job
contents, and scoring version. Repeated list/detail requests reuse the cached
result; changing profile skills, target roles/locations, or job content causes
the score to be recalculated.

Jobs are active-only by default. Include closed jobs when reviewing history:

```bash
curl "http://127.0.0.1:8000/jobs?active_only=false&limit=100"
```

### Job Lifecycle

Collected jobs store `first_seen_at`, `last_seen_at`, `is_active`,
`missed_collection_count`, and `closed_at`.

- Seeing a job again updates `last_seen_at` and reactivates it if necessary.
- Missing jobs are evaluated only when a company board was fetched completely without keyword filtering.
- A job is marked closed after two consecutive complete collection runs do not return it.
- Partial, capped, keyword-filtered, or failed collection runs never close jobs.
- Market metrics, Skill Gaps, and deduplication use active public jobs only.
- Tracker history remains available when its job closes.

Filter by location:

```bash
curl "http://127.0.0.1:8000/jobs?location=US&limit=20"
```

Use structured filters after cleaning:

```bash
curl "http://127.0.0.1:8000/jobs?us_only=true&work_mode=onsite&limit=20"
curl "http://127.0.0.1:8000/jobs?seniority=senior&limit=20"
curl "http://127.0.0.1:8000/jobs?role_category=finance_accounting&limit=20"
```

Get market summary metrics:

```bash
curl http://127.0.0.1:8000/jobs/market-summary
```

Backfill cleaned fields for existing raw jobs:

```bash
curl -X POST http://127.0.0.1:8000/jobs/clean
```

Extract skills from saved job descriptions:

```bash
curl -X POST http://127.0.0.1:8000/jobs/extract-skills
```

## Manual Application Tracker

Application tracking is manual. Apply on the company site first, then record the status in this system.

Save or update tracking info for a job:

```bash
curl -X PUT http://127.0.0.1:8000/applications/by-job/47 \
  -H "Content-Type: application/json" \
  -d '{
    "raw_job_id": 47,
    "status": "applied",
    "applied_date": "2026-06-17",
    "follow_up_date": "2026-06-24",
    "resume_version_id": 1,
    "cover_letter_id": null,
    "notes": "Applied manually on the company careers page."
  }'
```

Read tracking info for a job:

```bash
curl http://127.0.0.1:8000/applications/by-job/47
```

List tracked applications with job summary fields:

```bash
curl http://127.0.0.1:8000/applications
```

Use `title_search` when you only want to search job titles:

```bash
curl "http://127.0.0.1:8000/jobs?title_search=analyst&limit=20"
```

## Frontend

The frontend is prepared as a React + Vite app.

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://127.0.0.1:5173
```

The UI is US-focused by default. Job list and dashboard metrics load with `us_only=true` unless the `US only` filter is unchecked.

If the backend is running on a different port:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8001 npm run dev
```

## First Milestone

The first implementation milestone is:

```text
Collect public jobs from one source
-> Save raw jobs
-> Return jobs through the API
```

## Ethics

This project does not auto-submit applications, scrape restricted platforms, bypass authentication/CAPTCHA, or invent resume experience. Users must review all generated application materials before using them.
