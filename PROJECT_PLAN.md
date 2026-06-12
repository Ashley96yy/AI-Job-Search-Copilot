# AI Job Search Copilot - Project Plan

## Table of Contents

1. [Project Vision](#1-project-vision)
2. [Why This Project](#2-why-this-project)
3. [Target Users](#3-target-users)
4. [Core Product Principle](#4-core-product-principle)
5. [Main Product Modules](#5-main-product-modules)
6. [Recommended Tech Stack](#6-recommended-tech-stack)
7. [Long-Term Product Architecture](#7-long-term-product-architecture)
8. [Web First, App Later Strategy](#8-web-first-app-later-strategy)
9. [Data Acquisition Strategy](#9-data-acquisition-strategy)
10. [Job Collector Module](#10-job-collector-module)
11. [Raw Job Storage](#11-raw-job-storage)
12. [Job Cleaning & Normalization](#12-job-cleaning--normalization)
13. [Job Deduplication & Canonicalization](#13-job-deduplication--canonicalization)
14. [Skill & Requirement Extraction](#14-skill--requirement-extraction)
15. [Market Intelligence Dashboard](#15-market-intelligence-dashboard)
16. [User Profile / Resume Parser](#16-user-profile--resume-parser)
17. [Fit Score & Skill Gap Analyzer](#17-fit-score--skill-gap-analyzer)
18. [Resume Tailoring Assistant](#18-resume-tailoring-assistant)
19. [Application Assistant](#19-application-assistant)
20. [Application Tracker](#20-application-tracker)
21. [Suggested Database Tables](#21-suggested-database-tables)
22. [Suggested API Endpoints](#22-suggested-api-endpoints)
23. [Web Pages](#23-web-pages)
24. [8-Week Development Plan](#24-8-week-development-plan)
25. [MVP Scope](#25-mvp-scope)
26. [Future Improvements](#26-future-improvements)
27. [Project Ethics](#27-project-ethics)
28. [Portfolio Story](#28-portfolio-story)
29. [Resume Bullets](#29-resume-bullets)
30. [Short Demo Script](#30-short-demo-script)

## 1. Project Vision

**AI Job Search Copilot** is a human-in-the-loop job search assistant for entry-level data, risk, finance analytics, and AI analytics candidates.

The system automatically collects job postings from compliant public sources, cleans and deduplicates position data, extracts job requirements, analyzes market trends, compares jobs with a candidate profile, generates resume/application suggestions, and tracks application progress.

The goal is not to build a spammy auto-apply bot. The goal is to build a thoughtful job intelligence and application workflow system.

## 2. Why This Project

This project comes from a real problem:

Entry-level data candidates are facing a confusing job market. Many jobs labeled as "entry-level" require multiple years of experience, AI-related skills are becoming more common, and job postings are scattered across many sources.

Instead of manually searching and guessing, this project builds a data-driven system to answer:

- What skills are most demanded in data / risk / AI analytics roles?
- Which jobs are actually suitable for entry-level candidates?
- Which jobs match my background best?
- What skills am I missing?
- How should I tailor my resume for a specific role?
- How can I track applications without losing control?

## 3. Target Users

### Primary User

Entry-level or early-career candidates looking for:

- Data Analyst roles
- Risk Data Analyst roles
- Financial Data Analyst roles
- Product Analyst roles
- BI Analyst roles
- AI Data Analyst roles
- Compliance / Fraud / AML Analytics roles

### Personal Positioning

This project also supports the creator's own career positioning:

> Finance / risk background + data analytics skills + AI tools + business problem solving.

## 4. Core Product Principle

The system should be:

> Automated where automation is helpful, human-controlled where judgment is necessary.

The project should automate:

- Job data collection
- Data cleaning
- Deduplication
- Skill extraction
- Market analytics
- Fit score calculation
- Resume suggestion drafting
- Application tracking

The project should not automate:

- Logging into LinkedIn / Indeed
- Clicking Easy Apply
- Submitting applications without user review
- Bypassing CAPTCHA or platform restrictions
- Sending spammy applications or messages

## 5. Main Product Modules

The project has 8 major modules:

1. Job Data Collector
2. Raw Job Storage
3. Job Cleaning & Normalization
4. Job Deduplication & Canonicalization
5. Skill / Requirement Extraction
6. Market Intelligence Dashboard
7. Candidate Fit & Skill Gap Analyzer
8. Application Assistant & Tracker

## 6. Recommended Tech Stack

### MVP Stack

- Backend: FastAPI
- Frontend: React
- Database: SQLite first, PostgreSQL later
- Data processing: Python, pandas
- NLP / ML: scikit-learn, regex, keyword matching, embeddings later
- LLM: OpenAI API or Gemini API
- Visualization: React chart library or Plotly
- Version control: GitHub

### Why FastAPI + React

The project should start with a web version, but the architecture should support a future mobile app.

FastAPI backend can be reused by:

- React web app
- Future Expo / React Native mobile app
- Internal scripts
- Scheduled job collectors

React web app should be the first product interface.

Future mobile app can reuse the same backend APIs.

## 7. Long-Term Product Architecture

```text
React Web App
    |
    v
FastAPI Backend
    |
    v
PostgreSQL / SQLite
    |
    v
Collectors + Deduplication + Cleaning + Extraction + Matching
    |
    v
LLM Application Assistant

Future:
Expo / React Native Mobile App
    |
    v
Same FastAPI Backend
```

## 8. Web First, App Later Strategy

### Phase 1: Web MVP

Build a full web version first.

Core web pages:

1. Dashboard
2. Job List
3. Job Detail
4. Fit Analyzer
5. Application Assistant
6. Application Tracker
7. User Profile / Resume

### Phase 2: Mobile-Friendly Web / PWA

Make the web app usable on phone browser.

Mobile-friendly features:

- View saved jobs
- Check fit score
- Update application status
- Copy referral message
- View follow-up reminders

### Phase 3: Native Mobile App

Build Expo / React Native app later.

Mobile app should focus on:

- Saved jobs
- Job alerts
- Fit score summary
- Application tracker
- Follow-up reminders
- Referral message copy
- Status updates

Complex dashboards should stay mainly on web.

## 9. Data Acquisition Strategy

The project should not rely mainly on manually prepared CSV files.

CSV upload can be used for testing and fallback, but the real product should have automatic job collection.

### Recommended Sources

#### Tier 1: Structured / Public Job Sources

- Greenhouse job board data
- Lever job postings
- USAJOBS
- Public company career pages when allowed

#### Tier 2: Job APIs

Possible later additions:

- Adzuna
- The Muse
- Remotive
- Other compliant job APIs

#### Tier 3: Company Career Page Parser

Later version can parse public career pages with structured job posting data.

### Sources to Avoid

Avoid building the project around:

- LinkedIn scraping
- Indeed scraping
- Browser automation for job boards
- Auto-login scraping
- Auto-apply scripts

These create ethical, legal, and platform compliance risks.

## 10. Job Collector Module

### Goal

Automatically collect job postings from selected companies and public job sources.

### Inputs

- Company name
- Source type
- ATS board token or site identifier
- Search keywords
- Target role categories

### Target Keywords

Initial keywords:

- data analyst
- analytics
- business intelligence
- risk analyst
- credit risk
- fraud
- compliance
- AML
- data scientist
- machine learning
- AI
- product analyst

### Collector Responsibilities

Each collector should:

- Fetch raw jobs
- Normalize source-specific fields
- Save raw JSON
- Save source job ID
- Save job URL and apply URL
- Log collection status
- Avoid duplicate raw inserts

### Folder Structure

```text
backend/app/services/collectors/
    base_collector.py
    greenhouse_collector.py
    lever_collector.py
    usajobs_collector.py
    company_registry.py
    collector_runner.py
```

## 11. Raw Job Storage

The system should separate raw jobs from cleaned / canonical jobs.

### `raw_jobs` Table

Purpose: store every job posting collected from every source.

Important fields:

- `raw_job_id`
- `source`
- `external_job_id`
- `company`
- `title`
- `location`
- `job_url`
- `apply_url`
- `description`
- `date_posted`
- `date_collected`
- `raw_json`
- `content_hash`

### Why Raw Storage Matters

Raw job data should be preserved because:

- The same job may appear across multiple sources
- Job descriptions may change over time
- Cleaning logic may improve later
- The project should be transparent and auditable

## 12. Job Cleaning & Normalization

### Goal

Convert messy job postings into structured fields.

### Cleaning Tasks

1. Normalize company names
2. Normalize job titles
3. Normalize locations
4. Detect work mode
5. Parse salary range
6. Extract experience requirements
7. Classify seniority level
8. Clean HTML from job descriptions
9. Standardize date fields

### Example Normalized Title Categories

- `data_analyst`
- `risk_data_analyst`
- `financial_data_analyst`
- `product_analyst`
- `bi_analyst`
- `data_scientist`
- `ml_engineer`
- `compliance_analyst`
- `fraud_analyst`
- `unknown`

### Work Mode Categories

- `remote`
- `hybrid`
- `onsite`
- `unknown`

### Seniority Categories

- `intern`
- `entry`
- `junior`
- `mid`
- `senior`
- `lead`
- `unknown`

## 13. Job Deduplication & Canonicalization

### Goal

Remove duplicate positions from market analysis while preserving source history.

This is a core project highlight.

### Why Deduplication Is Needed

The same job may appear:

- On a company website
- On Greenhouse or Lever
- In a public job API
- Multiple times across daily collection runs
- With slightly different titles or URLs

If duplicates are not removed, dashboards will overcount skills and distort market trends.

### Deduplication Design

Use three layers:

#### Level 1: Source-Level Exact Match

If source and external job ID are the same, treat it as the same raw job.

Example:

```text
source = greenhouse
external_job_id = 12345
```

#### Level 2: Normalized Fingerprint Match

Generate a fingerprint based on:

- Normalized company
- Normalized title
- Normalized location
- Apply URL if available

Example:

```text
capital one | data analyst intern | mclean va
```

#### Level 3: Fuzzy Matching

Use fuzzy matching for cases where titles or descriptions are similar but not identical.

Possible methods:

- `rapidfuzz` for title similarity
- TF-IDF + cosine similarity for description similarity
- Company exact or near-exact match
- Apply URL comparison

### Deduplication Rules

Likely duplicate if:

- Same apply URL
- Same company + very similar title + similar description
- Same source job ID

Do not automatically merge if:

- Same company and title but different team
- Same company and title but clearly different locations
- Seniority levels differ
- Job descriptions are meaningfully different

### Canonical Jobs

After deduplication, dashboard and fit score should use `canonical_jobs`, not raw jobs.

### Suggested Tables

- `raw_jobs`
- `canonical_jobs`
- `job_source_map`
- `collection_runs`
- `duplicate_review_queue`

## 14. Skill & Requirement Extraction

### Goal

Extract structured requirements from job descriptions.

### First Version

Use keyword-based extraction first.

Skill categories:

- Programming: SQL, Python, R, Java, Scala
- Data tools: Excel, Tableau, Power BI, Looker
- Database: PostgreSQL, MySQL, Snowflake, BigQuery
- ML: machine learning, classification, regression, XGBoost
- Cloud: AWS, Azure, GCP
- AI: LLM, GenAI, RAG, prompt engineering
- Finance / Risk: credit risk, fraud, AML, compliance, model risk
- Soft skills: communication, stakeholder management, presentation

### Second Version

Use LLM structured extraction to improve coverage.

LLM should extract:

- Required skills
- Preferred skills
- Domain skills
- Soft skills
- Minimum years of experience
- Seniority level
- Whether the role is entry-level friendly

### Evaluation

Create a small human-labeled sample of job descriptions.

Compare:

- Keyword extraction
- LLM extraction
- Human labels

Metrics:

- Precision
- Recall
- F1 score

This can become a strong ML / NLP project component.

## 15. Market Intelligence Dashboard

### Goal

Show job market trends for data / risk / AI analytics roles.

### Dashboard Metrics

Show:

- Total raw jobs collected
- Total canonical jobs after deduplication
- Duplicate rate
- Top role types
- Top required skills
- Top missing skills
- Work mode distribution
- Location distribution
- Seniority distribution
- Entry-level friendly rate
- Fake entry-level rate
- Salary range distribution when available
- Data source coverage

### Important Analysis: Fake Entry-Level Jobs

Define fake entry-level as:

> A job labeled entry / junior / new grad / intern, but requiring 3+ years of experience or senior-level responsibilities.

This analysis is valuable because it directly answers a real job market question.

### Source Coverage Report

Add a page showing:

- Jobs collected by source
- Jobs collected by company
- Salary missing rate by source
- Description length by source
- Duplicate rate by source
- Source bias discussion

This turns incomplete coverage into an analytical feature.

## 16. User Profile / Resume Parser

### Goal

Let the user input their background and skills.

### MVP Input

Start with pasted resume text.

Do not start with PDF parsing.

### Extracted User Profile Fields

- Technical skills
- Domain skills
- Soft skills
- Work experience
- Projects
- Education
- Target roles
- Target locations
- Work authorization notes, if user chooses to store them

### Later Version

Add:

- Resume PDF upload
- Multiple resume versions
- Project portfolio import
- LinkedIn profile text import

## 17. Fit Score & Skill Gap Analyzer

### Goal

Compare each job with the user profile and calculate a fit score.

### Fit Score Dimensions

Total score: 100

Suggested weights:

| Dimension | Weight |
| --- | ---: |
| Required skills match | 40 |
| Preferred skills match | 15 |
| Domain match | 15 |
| Seniority match | 15 |
| Location / work mode match | 10 |
| Interest match | 5 |

### Output for Each Job

The system should show:

- Fit score
- Match level
- Matched skills
- Missing required skills
- Missing preferred skills
- Domain match explanation
- Seniority risk
- Suggested resume emphasis
- Whether the job is worth applying to

### Match Levels

| Match Level | Score |
| --- | --- |
| Strong Match | 80+ |
| Good Match | 65-79 |
| Stretch Match | 50-64 |
| Low Match | Below 50 |

### Example Output

```text
Fit Score: 78/100
Match Level: Good Match

Strengths:
- SQL and Python match the role requirements.
- Finance and risk consulting background is relevant.
- Project experience can support the analytics requirement.

Gaps:
- Tableau is missing.
- No direct credit risk modeling project yet.
- Need stronger dashboard evidence.

Recommendation:
This is a reasonable role to apply to. Emphasize risk consulting, SQL/Python, and data project experience.
```

## 18. Resume Tailoring Assistant

### Decision

Use existing LLM APIs first.

Do not train a resume rewriting model during MVP.

### Why Not Train First

Training a good resume rewriting model would require:

- Many high-quality resume/JD pairs
- Human-written improved versions
- Evaluation data
- Safety checks
- Time and compute resources

This is not the best use of summer project time.

### Better Approach

Use LLM API for controlled rewriting, but build your own:

- Structured extraction
- Resume fact database
- Skill matching logic
- Prompt templates
- Claim verification
- Human review workflow
- Version management

### Resume Tailoring Pipeline

```text
Resume Text + Job Description
    |
    v
Extract resume facts
    |
    v
Extract JD requirements
    |
    v
Match skills and responsibilities
    |
    v
Generate resume suggestions
    |
    v
Verify unsupported claims
    |
    v
Human review
    |
    v
Save resume version
```

### Important Principle

The system should not invent experience.

Every generated suggestion should include:

- Original bullet
- Suggested bullet
- Related JD keyword
- Evidence from user resume
- Risk level: safe / needs review / unsupported

### Claim Verification

If the LLM suggests a skill or experience not found in the resume profile, mark it as unsupported.

Example:

```text
Suggested claim:
Built Tableau dashboards for executive stakeholders.

Risk:
Unsupported.

Reason:
Tableau is found in the job description but not in the candidate profile.
```

### Product Positioning

Call this module:

> Truth-preserving Resume Tailoring Assistant

or:

> Human-in-the-loop Resume Tailoring Assistant

## 19. Application Assistant

### Goal

Help users prepare thoughtful applications without automatically submitting them.

### Features

For each job, generate:

- Resume tailoring suggestions
- Cover letter draft
- Referral request message
- LinkedIn outreach message
- Application checklist
- Follow-up reminder

### Do Not Include

- Auto-submit application
- Auto-login
- Easy Apply automation
- CAPTCHA bypass
- Bulk spam application

### Human-in-the-Loop Statement

The app should clearly say:

> This system prepares application materials, but the user must review and submit applications manually.

## 20. Application Tracker

### Goal

Track the user's job search workflow.

### Status Flow

```text
Discovered
-> Saved
-> Ready to Apply
-> Applied
-> Referral Requested
-> Interview
-> Offer / Rejected / Withdrawn
```

### Tracker Fields

- Company
- Role
- Fit score
- Job URL
- Apply URL
- Status
- Resume version
- Cover letter version
- Referral contact
- Applied date
- Follow-up date
- Notes

### Tracker Dashboard

Show:

- Applications this week
- Total saved jobs
- Total applied jobs
- Interviews
- Rejections
- Response rate
- Top missing skills
- Follow-ups due this week

## 21. Suggested Database Tables

Core tables:

1. `raw_jobs`
2. `canonical_jobs`
3. `job_source_map`
4. `collection_runs`
5. `job_skills`
6. `user_profiles`
7. `resume_versions`
8. `job_fit_scores`
9. `applications`
10. `duplicate_review_queue`

## 22. Suggested API Endpoints

### Jobs

```text
GET /jobs
GET /jobs/{job_id}
POST /jobs/collect
POST /jobs/deduplicate
GET /jobs/market-summary
GET /jobs/source-coverage
```

### Profile

```text
POST /profile
GET /profile
PATCH /profile
```

### Fit Score

```text
POST /fit-score
GET /jobs/{job_id}/fit-score
```

### Resume Assistant

```text
POST /assistant/resume-suggestions
POST /assistant/cover-letter
POST /assistant/referral-message
POST /assistant/verify-claims
```

### Applications

```text
POST /applications
GET /applications
PATCH /applications/{application_id}
DELETE /applications/{application_id}
```

## 23. Web Pages

### Page 1: Home

Show:

- Raw jobs collected
- Canonical jobs after deduplication
- Duplicate rate
- Strong matches
- Applications submitted
- Top missing skill

### Page 2: Job Collector

Show:

- Source list
- Collection run button
- Collection logs
- Jobs found by source
- Errors

### Page 3: Job Market Dashboard

Show:

- Top skills
- Role distribution
- Work mode distribution
- Seniority distribution
- Fake entry-level rate
- Source coverage

### Page 4: Job List

Show:

- Company
- Title
- Location
- Work mode
- Fit score
- Seniority
- Status
- Save button

### Page 5: Job Detail

Show:

- Job description
- Extracted skills
- Required experience
- Salary if available
- Fit score
- Missing skills
- Apply URL

### Page 6: Resume / Profile

Show:

- Resume text input
- Extracted skills
- Projects
- Domain experience
- Target roles

### Page 7: Resume Tailoring Assistant

Show:

- Original bullet
- Suggested bullet
- Evidence
- JD keyword
- Risk level
- Accept / reject suggestion

### Page 8: Application Tracker

Show:

- Saved jobs
- Applied jobs
- Follow-up dates
- Interview status
- Notes
- Weekly progress

## 24. 8-Week Development Plan

### Week 1: Project Setup + Basic Collector

Goals:

- Create GitHub repo
- Set up FastAPI backend
- Set up React frontend
- Set up SQLite database
- Implement first Greenhouse or Lever collector
- Store raw jobs
- Show raw jobs in web UI

Deliverables:

- Backend project structure
- Frontend project structure
- `raw_jobs` table
- First collector working
- Job list page showing collected jobs

### Week 2: Multi-Source Collection + Collection Logs

Goals:

- Add second source collector
- Add company registry
- Add `collection_runs` table
- Add keyword filtering
- Add basic error logging

Deliverables:

- Greenhouse + Lever or another source working
- Source coverage count
- Collection logs visible in UI

### Week 3: Cleaning + Normalization

Goals:

- Normalize job titles
- Normalize company names
- Normalize locations
- Detect work mode
- Extract salary when available
- Extract years of experience
- Classify seniority level

Deliverables:

- Cleaned job fields
- Normalization functions
- Job detail page with cleaned fields

### Week 4: Deduplication MVP

Goals:

- Create `canonical_jobs` table
- Create `job_source_map` table
- Implement exact deduplication
- Implement normalized fingerprint deduplication
- Show raw vs canonical job count
- Show duplicate rate

Deliverables:

- Deduplication pipeline
- Canonical jobs created
- Dashboard showing duplicate rate

### Week 5: Skill Extraction + Market Dashboard

Goals:

- Build skill dictionary
- Extract skills from job descriptions
- Create `job_skills` table
- Build top skills dashboard
- Build role distribution chart
- Build fake entry-level analysis

Deliverables:

- Skill extraction module
- Market dashboard MVP
- Entry-level reality check

### Week 6: User Profile + Fit Score

Goals:

- Add resume text input
- Extract user skills
- Build fit score logic
- Show matched skills and missing skills
- Rank jobs by fit score

Deliverables:

- User profile page
- Fit Analyzer
- Job list sorted by fit score

### Week 7: LLM Resume Assistant + Application Assistant

Goals:

- Connect OpenAI or Gemini API
- Extract JD requirements with structured output
- Extract resume facts
- Generate resume suggestions
- Add claim verification
- Generate referral message and cover letter draft
- Keep all outputs human-reviewed

Deliverables:

- Resume Tailoring Assistant page
- Claim risk labels
- Application checklist
- Referral message generator

### Week 8: Application Tracker + Polish

Goals:

- Add `applications` table
- Add application status update
- Add follow-up date
- Add tracker dashboard
- Improve README
- Add screenshots
- Record 3-minute demo video
- Write project summary and resume bullets

Deliverables:

- Application Tracker
- Finished README
- Demo screenshots
- Demo video script
- Resume-ready bullet points

## 25. MVP Scope

The MVP should include:

- Automatic job collection from at least one or two sources
- Raw job storage
- Job cleaning
- Job deduplication
- Skill extraction
- Market dashboard
- User resume/profile input
- Fit score
- Resume suggestion generation
- Application tracker

The MVP does not need:

- Native mobile app
- Full PDF resume parser
- Full job market coverage
- Fine-tuned model
- Automatic application submission
- Complex authentication
- Paid SaaS features

## 26. Future Improvements

Possible future features:

- Mobile app with Expo / React Native
- PWA notification reminders
- Resume PDF parsing
- Multiple resume versions
- Job alert emails
- More job APIs
- JobPosting structured data parser
- Embedding-based semantic job matching
- Trained role classifier
- Fake entry-level classifier
- Skill extraction evaluation dashboard
- User feedback loop for fit score improvement
- Calendar integration for interview tracking
- Gmail integration for application status parsing

## 27. Project Ethics

The project should clearly state:

- It does not auto-submit applications.
- It does not scrape restricted platforms.
- It does not bypass authentication, CAPTCHA, or platform controls.
- It does not invent resume experience.
- It requires users to review all generated application materials.
- It is designed to improve application quality, not spam job postings.

## 28. Portfolio Story

The story for interviews:

> I built this project because I wanted to understand the changing data job market more systematically. Instead of manually browsing job boards, I created a system that collects public job postings, cleans and deduplicates them, extracts skills and experience requirements, analyzes market trends, and helps candidates compare jobs with their own backgrounds. I also designed a human-in-the-loop resume assistant that generates suggestions without inventing unsupported experience.

## 29. Resume Bullets

Possible resume bullets:

- Built an AI-powered job search copilot that collects public data / risk / AI analytics job postings, extracts job requirements, ranks roles by candidate fit, and tracks applications.
- Designed a multi-source job data pipeline with raw job storage, collection logs, normalized fields, and deduplication across repeated or cross-posted positions.
- Implemented a job deduplication pipeline using source-level IDs, normalized fingerprints, and fuzzy matching to prevent duplicate postings from inflating market analytics.
- Developed dashboards to analyze top skills, role distribution, work mode, seniority level, source coverage, and fake entry-level job patterns.
- Integrated an LLM-based resume tailoring assistant with claim verification and human review to generate truthful resume suggestions, cover letter drafts, and referral messages.
- Built an application tracker to manage saved jobs, application status, referral progress, follow-up dates, and recurring skill gaps.

## 30. Short Demo Script

Hi, this is my project AI Job Search Copilot.

I built this project to better understand the changing job market for entry-level data, risk, and AI analytics candidates.

The system first collects job postings from public and compliant sources. It stores raw job data, cleans job titles and descriptions, and deduplicates repeated positions across sources. Then it extracts skills, experience requirements, work mode, and seniority level from job descriptions.

The dashboard shows market trends such as top skills, role distribution, fake entry-level rates, and source coverage. Users can also paste their resume, and the system compares their background with each job to calculate a fit score and identify missing skills.

Finally, the application assistant generates resume suggestions, cover letter drafts, referral messages, and application checklists. I designed this workflow to be human-in-the-loop: the system helps users prepare better applications, but it does not automatically submit them or invent unsupported experience.

Through this project, I practiced data collection, data cleaning, deduplication, SQL/database design, NLP-based skill extraction, LLM integration, dashboard design, API development, and product thinking.
