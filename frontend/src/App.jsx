import { useEffect, useMemo, useRef, useState } from "react";
import {
  BriefcaseBusiness,
  ChartColumn,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Database,
  Eye,
  EyeOff,
  FileText,
  LayoutDashboard,
  SlidersHorizontal,
  UserRound,
  X,
} from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const JOB_DISCOVERY_SESSION_KEY = "job-search-copilot:new-jobs-since";

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "jobs", label: "Jobs", icon: BriefcaseBusiness },
  { id: "profile", label: "Profile", icon: UserRound },
  { id: "documents", label: "Documents", icon: FileText },
  { id: "skill_gaps", label: "Skill Gaps", icon: ChartColumn },
  { id: "tracker", label: "Tracker", icon: ClipboardCheck },
  { id: "data_sources", label: "Data Sources", icon: Database },
];

const APPLICATION_STATUS_OPTIONS = [
  { value: "saved", label: "Saved" },
  { value: "ready_to_apply", label: "Ready to Apply" },
  { value: "applied", label: "Applied" },
  { value: "interview", label: "Interview" },
  { value: "offer", label: "Offer" },
  { value: "rejected", label: "Rejected" },
  { value: "withdrawn", label: "Withdrawn" },
];

const LABELS = {
  ai_ml: "AI / ML",
  ashby: "Ashby",
  analytics_adjacent: "Analytics Adjacent",
  data_analytics: "Data Analytics",
  data_engineering: "Data Engineering",
  engineering: "Engineering",
  finance_accounting: "Finance / Accounting",
  failed: "Failed",
  greenhouse: "Greenhouse",
  manual_handshake: "Handshake",
  manual_linkedin: "LinkedIn",
  manual_other: "Other",
  hybrid: "Hybrid",
  intern: "Intern",
  junior: "Junior",
  lead: "Lead",
  lever: "Lever",
  manual: "Manual",
  mid: "Mid",
  onsite: "Onsite",
  entry_friendly: "Entry Friendly",
  possible_stretch: "Possible Stretch",
  partial_success: "Partial Success",
  too_senior: "Too Senior",
  product: "Product",
  remote: "Remote",
  risk_compliance: "Risk / Compliance",
  sales_gtm: "Sales / GTM",
  senior: "Senior",
  scheduled: "Scheduled",
  success: "Success",
  sync_all: "Sync All",
  running: "Running",
  saved: "Saved",
  ready_to_apply: "Ready to Apply",
  applied: "Applied",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
  unknown: "Unknown",
};

function formatDate(value) {
  if (!value) {
    return "Not listed";
  }

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

function isNewSince(job, cutoff) {
  if (!job.first_seen_at || !cutoff) {
    return false;
  }

  return new Date(job.first_seen_at).getTime() >= new Date(cutoff).getTime();
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatDuration(startedAt, completedAt) {
  if (!startedAt) {
    return "-";
  }

  const seconds = Math.max(
    0,
    Math.round(
      (new Date(completedAt || Date.now()) - new Date(startedAt)) / 1000,
    ),
  );
  if (seconds < 60) {
    return `${seconds}s`;
  }

  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function formatLabel(value) {
  return LABELS[value] ?? value ?? "Unknown";
}

function formatFitScore(job) {
  if (job.fit_score === null || job.fit_score === undefined) {
    return "No profile";
  }

  return `${job.fit_score}`;
}

function formatPostingAge(job) {
  if (job.posting_age_days === null || job.posting_age_days === undefined) {
    return "Unknown age";
  }

  return `${job.posting_age_days}d`;
}

function formatPercentChange(value) {
  if (value === null || value === undefined) {
    return "N/A";
  }

  const percentage = Math.round(value * 100);
  return `${percentage > 0 ? "+" : ""}${percentage}%`;
}

function cleanDescription(value) {
  if (!value) {
    return "No description available.";
  }

  const parser = new DOMParser();
  const decoded = parser.parseFromString(value, "text/html").documentElement.textContent ?? value;
  const withoutTags = decoded.replace(/<[^>]+>/g, " ");
  return withoutTags.replace(/\s+/g, " ").trim();
}

function DistributionList({ title, items }) {
  const total = items.reduce((sum, item) => sum + item.count, 0);

  return (
    <article className="distribution-card">
      <h3>{title}</h3>
      <div className="distribution-list">
        {items.map((item) => {
          const percentage = total ? Math.round((item.count / total) * 100) : 0;

          return (
            <div className="distribution-row" key={item.name}>
              <div className="distribution-label">
                <span>{formatLabel(item.name)}</span>
                <strong>{item.count}</strong>
              </div>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${percentage}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </article>
  );
}

function App() {
  const discoverySessionStarted = useRef(false);
  const [activeView, setActiveView] = useState("jobs");
  const [collectorSource, setCollectorSource] = useState("greenhouse");
  const [boardTokens, setBoardTokens] = useState("");
  const [maxJobs, setMaxJobs] = useState(100);
  const [company, setCompany] = useState("");
  const [location, setLocation] = useState("");
  const [jobState, setJobState] = useState("");
  const [usOnly, setUsOnly] = useState(true);
  const [targetRelevantOnly, setTargetRelevantOnly] = useState(true);
  const [careerEligibleOnly, setCareerEligibleOnly] = useState(true);
  const [activeOnly, setActiveOnly] = useState(true);
  const [workMode, setWorkMode] = useState("");
  const [seniority, setSeniority] = useState("");
  const [entryFitLevel, setEntryFitLevel] = useState("");
  const [roleCategory, setRoleCategory] = useState("");
  const [dashboardRoleCategory, setDashboardRoleCategory] = useState("");
  const [search, setSearch] = useState("");
  const [titleSearch, setTitleSearch] = useState("");
  const [sortBy, setSortBy] = useState("first_seen");
  const [matchLevel, setMatchLevel] = useState("");
  const [minFitScore, setMinFitScore] = useState("");
  const [hasFitScore, setHasFitScore] = useState(false);
  const [maxPostingAgeDays, setMaxPostingAgeDays] = useState("180");
  const [freshness, setFreshness] = useState("");
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [discoveryFilter, setDiscoveryFilter] = useState("visible");
  const [newJobsSince, setNewJobsSince] = useState(
    () => window.sessionStorage.getItem(JOB_DISCOVERY_SESSION_KEY),
  );
  const [sources, setSources] = useState([]);
  const [collectionRuns, setCollectionRuns] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [jobPagination, setJobPagination] = useState({
    total: 0,
    page: 1,
    page_size: 25,
    total_pages: 0,
  });
  const [selectedJob, setSelectedJob] = useState(null);
  const [showManualJobForm, setShowManualJobForm] = useState(false);
  const [manualJobForm, setManualJobForm] = useState({
    source: "linkedin",
    company: "",
    title: "",
    location: "",
    job_url: "",
    date_posted: "",
    description: "",
    status: "saved",
    applied_date: "",
    resume_version_id: "",
    notes: "",
  });
  const [trackedApplications, setTrackedApplications] = useState([]);
  const [trackerStatusFilter, setTrackerStatusFilter] = useState("");
  const [resumeVersions, setResumeVersions] = useState([]);
  const [editingResumeVersionId, setEditingResumeVersionId] = useState(null);
  const [resumeSuggestions, setResumeSuggestions] = useState(null);
  const [suggestionResumeVersionId, setSuggestionResumeVersionId] = useState("");
  const [coverLetterDraft, setCoverLetterDraft] = useState(null);
  const [coverLetterResumeVersionId, setCoverLetterResumeVersionId] = useState("");
  const [coverLetterName, setCoverLetterName] = useState("");
  const [coverLetters, setCoverLetters] = useState([]);
  const [editingCoverLetterId, setEditingCoverLetterId] = useState(null);
  const [profile, setProfile] = useState(null);
  const [skillGapSummary, setSkillGapSummary] = useState(null);
  const [profileForm, setProfileForm] = useState({
    name: "",
    source_resume_version_id: "",
    target_roles: "",
    target_locations: "",
  });
  const [applicationForm, setApplicationForm] = useState({
    status: "saved",
    applied_date: "",
    follow_up_date: "",
    resume_version_id: "",
    cover_letter_id: "",
    notes: "",
  });
  const [resumeVersionForm, setResumeVersionForm] = useState({
    name: "",
    target_role: "",
    resume_text: "",
    notes: "",
  });
  const [marketSummary, setMarketSummary] = useState(null);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [loadingJobDetail, setLoadingJobDetail] = useState(false);
  const [loadingApplications, setLoadingApplications] = useState(false);
  const [loadingResumeVersions, setLoadingResumeVersions] = useState(false);
  const [loadingResumeSuggestions, setLoadingResumeSuggestions] = useState(false);
  const [loadingCoverLetter, setLoadingCoverLetter] = useState(false);
  const [loadingCoverLetters, setLoadingCoverLetters] = useState(false);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [loadingSkillGaps, setLoadingSkillGaps] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [uploadingResume, setUploadingResume] = useState(false);
  const [savingManualSkill, setSavingManualSkill] = useState("");
  const [savingApplication, setSavingApplication] = useState(false);
  const [savingQuickTrackJobId, setSavingQuickTrackJobId] = useState(null);
  const [savingJobStateId, setSavingJobStateId] = useState(null);
  const [savingManualJob, setSavingManualJob] = useState(false);
  const [deletingManualJob, setDeletingManualJob] = useState(false);
  const [savingResumeVersion, setSavingResumeVersion] = useState(false);
  const [savingCoverLetter, setSavingCoverLetter] = useState(false);
  const [uploadingResumeVersion, setUploadingResumeVersion] = useState(false);
  const [loadingSources, setLoadingSources] = useState(false);
  const [loadingCollectionRuns, setLoadingCollectionRuns] = useState(false);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [collecting, setCollecting] = useState(false);
  const [syncingAll, setSyncingAll] = useState(false);
  const [deduplicating, setDeduplicating] = useState(false);
  const [profileMessage, setProfileMessage] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  const stats = useMemo(() => {
    return [
      { label: "Raw jobs", value: marketSummary?.total_jobs ?? 0 },
      { label: "Canonical jobs", value: marketSummary?.canonical_jobs ?? 0 },
      {
        label: "Duplicate rate",
        value: marketSummary ? `${Math.round((marketSummary.duplicate_rate ?? 0) * 100)}%` : "0%",
      },
      { label: "Remote US jobs", value: marketSummary?.remote_jobs ?? 0 },
      { label: "Companies", value: marketSummary?.companies ?? 0 },
      { label: "This week", value: marketSummary?.new_jobs_this_week ?? 0 },
      { label: "Last week", value: marketSummary?.new_jobs_last_week ?? 0 },
      {
        label: "WoW change",
        value: formatPercentChange(marketSummary?.week_over_week_change),
      },
      { label: "Active weeks", value: marketSummary?.active_weeks ?? 0 },
      {
        label: "Top category",
        value: formatLabel(marketSummary?.top_role_category),
      },
    ];
  }, [marketSummary]);

  const filteredSources = useMemo(() => {
    return sources.filter((source) => source.source === collectorSource);
  }, [collectorSource, sources]);

  const runningCollectionSources = useMemo(() => {
    return new Set(
      collectionRuns
        .filter((run) => run.status === "running")
        .map((run) => run.source),
    );
  }, [collectionRuns]);

  const hasRunningCollection = runningCollectionSources.size > 0;

  const filteredApplications = useMemo(() => {
    if (!trackerStatusFilter) {
      return trackedApplications;
    }

    return trackedApplications.filter((application) => application.status === trackerStatusFilter);
  }, [trackedApplications, trackerStatusFilter]);

  const trackedJobIds = useMemo(() => {
    return new Set(trackedApplications.map((application) => application.raw_job_id));
  }, [trackedApplications]);

  const activeJobFilters = useMemo(() => [
    company && { id: "company", label: `Company: ${company}` },
    location && { id: "location", label: `Location: ${location}` },
    jobState && { id: "state", label: `State: ${jobState}` },
    workMode && { id: "work_mode", label: formatLabel(workMode) },
    seniority && { id: "seniority", label: formatLabel(seniority) },
    entryFitLevel && { id: "entry_fit", label: formatLabel(entryFitLevel) },
    roleCategory && { id: "role_category", label: formatLabel(roleCategory) },
    search && { id: "search", label: `Text: ${search}` },
    titleSearch && { id: "title", label: `Title: ${titleSearch}` },
    matchLevel && { id: "match_level", label: matchLevel },
    minFitScore && { id: "min_fit", label: `Fit ${minFitScore}+` },
    maxPostingAgeDays && { id: "posting_age", label: `Posted ${maxPostingAgeDays}d` },
    freshness && { id: "freshness", label: freshness },
    usOnly && { id: "us_only", label: "US only" },
    targetRelevantOnly && { id: "target_relevant", label: "Target relevant" },
    careerEligibleOnly && { id: "career_eligible", label: "0-2 years" },
    activeOnly && { id: "active_only", label: "Active" },
    hasFitScore && { id: "has_fit", label: "Has Fit Score" },
  ].filter(Boolean), [
    activeOnly,
    careerEligibleOnly,
    company,
    entryFitLevel,
    freshness,
    hasFitScore,
    jobState,
    location,
    matchLevel,
    maxPostingAgeDays,
    minFitScore,
    roleCategory,
    search,
    seniority,
    targetRelevantOnly,
    titleSearch,
    usOnly,
    workMode,
  ]);

  function clearJobFilter(filterId) {
    const clearActions = {
      active_only: () => setActiveOnly(false),
      career_eligible: () => setCareerEligibleOnly(false),
      company: () => setCompany(""),
      entry_fit: () => setEntryFitLevel(""),
      freshness: () => setFreshness(""),
      has_fit: () => setHasFitScore(false),
      location: () => setLocation(""),
      match_level: () => setMatchLevel(""),
      min_fit: () => setMinFitScore(""),
      posting_age: () => setMaxPostingAgeDays(""),
      role_category: () => setRoleCategory(""),
      search: () => setSearch(""),
      seniority: () => setSeniority(""),
      state: () => setJobState(""),
      target_relevant: () => setTargetRelevantOnly(false),
      title: () => setTitleSearch(""),
      us_only: () => setUsOnly(false),
      work_mode: () => setWorkMode(""),
    };
    clearActions[filterId]?.();
  }

  async function loadJobs(
    requestedPage = 1,
    requestedPageSize = jobPagination.page_size,
    options = {},
  ) {
    setLoadingJobs(true);
    setError("");

    const effectiveDiscoveryFilter = options.discoveryFilter ?? discoveryFilter;
    const effectiveNewJobsSince = options.newJobsSince ?? newJobsSince;

    const params = new URLSearchParams();
    if (company.trim()) params.set("company", company.trim());
    if (location.trim()) params.set("location", location.trim());
    if (jobState.trim()) params.set("state", jobState.trim());
    if (usOnly) params.set("us_only", "true");
    if (careerEligibleOnly) params.set("career_eligible_only", "true");
    params.set("active_only", String(activeOnly));
    if (targetRelevantOnly) params.set("min_target_relevance", "50");
    if (workMode) params.set("work_mode", workMode);
    if (seniority) params.set("seniority", seniority);
    if (entryFitLevel) params.set("entry_fit_level", entryFitLevel);
    if (roleCategory) params.set("role_category", roleCategory);
    if (search.trim()) params.set("search", search.trim());
    if (titleSearch.trim()) params.set("title_search", titleSearch.trim());
    if (sortBy) params.set("sort_by", sortBy);
    if (matchLevel) params.set("match_level", matchLevel);
    if (minFitScore) params.set("min_fit_score", minFitScore);
    if (hasFitScore) params.set("has_fit_score", "true");
    if (maxPostingAgeDays) params.set("max_posting_age_days", maxPostingAgeDays);
    if (freshness) params.set("freshness", freshness);
    if (effectiveDiscoveryFilter === "unseen") params.set("unseen_only", "true");
    if (effectiveDiscoveryFilter === "hidden") params.set("hidden_only", "true");
    if (effectiveDiscoveryFilter === "new" && effectiveNewJobsSince) {
      params.set("new_since", effectiveNewJobsSince);
    }
    params.set("page", String(requestedPage));
    params.set("page_size", String(requestedPageSize));

    try {
      const response = await fetch(`${API_BASE_URL}/jobs?${params.toString()}`);

      if (!response.ok) {
        throw new Error(`GET /jobs failed with ${response.status}`);
      }

      const result = await response.json();
      setJobs(result.items);
      setJobPagination({
        total: result.total,
        page: result.page,
        page_size: result.page_size,
        total_pages: result.total_pages,
      });
      setSelectedJob(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingJobs(false);
    }
  }

  async function startJobDiscoverySession() {
    try {
      const response = await fetch(`${API_BASE_URL}/jobs/discovery-session`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error(`POST /jobs/discovery-session failed with ${response.status}`);
      }

      const session = await response.json();
      setNewJobsSince(session.new_since);
      window.sessionStorage.setItem(JOB_DISCOVERY_SESSION_KEY, session.new_since);
      return session.new_since;
    } catch (err) {
      setError(err.message);
      return null;
    }
  }

  async function selectDiscoveryFilter(nextFilter) {
    setDiscoveryFilter(nextFilter);
    await loadJobs(1, jobPagination.page_size, {
      discoveryFilter: nextFilter,
    });
  }

  async function writeJobState(jobId, updates) {
    const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/state`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(updates),
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`PUT /jobs/${jobId}/state failed with ${response.status}: ${detail}`);
    }

    return response.json();
  }

  async function loadJobDetail(jobId) {
    setLoadingJobDetail(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`);

      if (!response.ok) {
        throw new Error(`GET /jobs/${jobId} failed with ${response.status}`);
      }

      const job = await response.json();
      let nextJob = job;

      if (!job.is_viewed) {
        const state = await writeJobState(job.id, { viewed: true });
        nextJob = { ...job, ...state };
        setJobs((current) => current.map((item) => (
          item.id === job.id ? { ...item, ...state } : item
        )));
      }

      setSelectedJob(nextJob);
      setResumeSuggestions(null);
      setSuggestionResumeVersionId("");
      setCoverLetterDraft(null);
      setCoverLetterResumeVersionId("");
      setCoverLetterName("");
      setEditingCoverLetterId(null);
      await loadApplicationForJob(job.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingJobDetail(false);
    }
  }

  async function toggleJobHidden(job, event) {
    event?.stopPropagation();
    setSavingJobStateId(job.id);
    setError("");
    setStatus("");

    try {
      const willHide = !job.is_hidden;
      await writeJobState(job.id, { hidden: willHide });
      if (selectedJob?.id === job.id) {
        setSelectedJob(null);
      }

      const currentPage = (
        jobs.length === 1 && jobPagination.page > 1
          ? jobPagination.page - 1
          : jobPagination.page
      );
      await loadJobs(currentPage);
      setStatus(willHide ? "Job hidden from discovery." : "Job restored to discovery.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingJobStateId(null);
    }
  }

  async function loadApplicationForJob(jobId) {
    try {
      const response = await fetch(`${API_BASE_URL}/applications/by-job/${jobId}`);

      if (!response.ok) {
        throw new Error(`GET /applications/by-job/${jobId} failed with ${response.status}`);
      }

      const application = await response.json();

      setApplicationForm({
        status: application?.status ?? "saved",
        applied_date: application?.applied_date ?? "",
        follow_up_date: application?.follow_up_date ?? "",
        resume_version_id: application?.resume_version_id
          ? String(application.resume_version_id)
          : "",
        cover_letter_id: application?.cover_letter_id
          ? String(application.cover_letter_id)
          : "",
        notes: application?.notes ?? "",
      });
    } catch (err) {
      setError(err.message);
    }
  }

  async function saveApplicationTracking(event) {
    event.preventDefault();

    if (!selectedJob) {
      return;
    }

    setSavingApplication(true);
    setError("");

    try {
      const payload = {
        raw_job_id: selectedJob.id,
        status: applicationForm.status,
        applied_date: applicationForm.applied_date || null,
        follow_up_date: applicationForm.follow_up_date || null,
        resume_version_id: applicationForm.resume_version_id
          ? Number(applicationForm.resume_version_id)
          : null,
        cover_letter_id: applicationForm.cover_letter_id
          ? Number(applicationForm.cover_letter_id)
          : null,
        notes: applicationForm.notes || null,
      };

      const response = await fetch(`${API_BASE_URL}/applications/by-job/${selectedJob.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`PUT /applications/by-job/${selectedJob.id} failed with ${response.status}: ${detail}`);
      }

      const application = await response.json();
      setApplicationForm({
        status: application.status,
        applied_date: application.applied_date ?? "",
        follow_up_date: application.follow_up_date ?? "",
        resume_version_id: application.resume_version_id
          ? String(application.resume_version_id)
          : "",
        cover_letter_id: application.cover_letter_id
          ? String(application.cover_letter_id)
          : "",
        notes: application.notes ?? "",
      });
      setStatus("Application tracking saved.");
      await loadTrackedApplications();
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingApplication(false);
    }
  }

  async function saveJobToTracker(job) {
    setSavingQuickTrackJobId(job.id);
    setError("");
    setStatus("");

    try {
      const payload = {
        raw_job_id: job.id,
        status: "saved",
        applied_date: null,
        follow_up_date: null,
        resume_version_id: null,
        cover_letter_id: null,
        notes: null,
      };

      const response = await fetch(`${API_BASE_URL}/applications/by-job/${job.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`PUT /applications/by-job/${job.id} failed with ${response.status}: ${detail}`);
      }

      if (selectedJob?.id === job.id) {
        setApplicationForm({
          status: "saved",
          applied_date: "",
          follow_up_date: "",
          resume_version_id: "",
          cover_letter_id: "",
          notes: "",
        });
      }

      setStatus(`${job.company || "This job"} saved to Tracker.`);
      await loadTrackedApplications();
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingQuickTrackJobId(null);
    }
  }

  async function saveManualJob(event) {
    event.preventDefault();
    setSavingManualJob(true);
    setError("");
    setStatus("");

    try {
      const jobResponse = await fetch(`${API_BASE_URL}/jobs/manual`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          source: manualJobForm.source,
          company: manualJobForm.company.trim(),
          title: manualJobForm.title.trim(),
          location: manualJobForm.location.trim() || null,
          job_url: manualJobForm.job_url.trim() || null,
          date_posted: manualJobForm.date_posted || null,
          description: manualJobForm.description.trim() || null,
        }),
      });

      if (!jobResponse.ok) {
        const detail = await jobResponse.text();
        throw new Error(`POST /jobs/manual failed with ${jobResponse.status}: ${detail}`);
      }

      const job = await jobResponse.json();
      const applicationResponse = await fetch(`${API_BASE_URL}/applications/by-job/${job.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          raw_job_id: job.id,
          status: manualJobForm.status,
          applied_date: manualJobForm.applied_date || null,
          follow_up_date: null,
          resume_version_id: manualJobForm.resume_version_id
            ? Number(manualJobForm.resume_version_id)
            : null,
          cover_letter_id: null,
          notes: manualJobForm.notes.trim() || null,
        }),
      });

      if (!applicationResponse.ok) {
        const detail = await applicationResponse.text();
        await fetch(`${API_BASE_URL}/jobs/manual/${job.id}`, { method: "DELETE" });
        throw new Error(
          `Tracker save failed with ${applicationResponse.status}: ${detail}`,
        );
      }

      setManualJobForm({
        source: "linkedin",
        company: "",
        title: "",
        location: "",
        job_url: "",
        date_posted: "",
        description: "",
        status: "saved",
        applied_date: "",
        resume_version_id: "",
        notes: "",
      });
      setShowManualJobForm(false);
      setStatus(`${job.company || "External job"} added to Jobs and Tracker.`);
      await Promise.all([loadJobs(), loadTrackedApplications(), loadSkillGaps()]);
      await loadJobDetail(job.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingManualJob(false);
    }
  }

  async function deleteManualJob() {
    if (!selectedJob?.is_user_added || !window.confirm("Delete this manually added job and its tracking data?")) {
      return;
    }

    setDeletingManualJob(true);
    setError("");
    setStatus("");

    try {
      const response = await fetch(`${API_BASE_URL}/jobs/manual/${selectedJob.id}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`DELETE /jobs/manual/${selectedJob.id} failed with ${response.status}: ${detail}`);
      }

      setSelectedJob(null);
      setStatus("External job and its tracking data deleted.");
      await Promise.all([loadJobs(), loadTrackedApplications(), loadSkillGaps()]);
    } catch (err) {
      setError(err.message);
    } finally {
      setDeletingManualJob(false);
    }
  }

  async function loadTrackedApplications() {
    setLoadingApplications(true);

    try {
      const response = await fetch(`${API_BASE_URL}/applications`);

      if (!response.ok) {
        throw new Error(`GET /applications failed with ${response.status}`);
      }

      setTrackedApplications(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingApplications(false);
    }
  }

  async function loadResumeVersions() {
    setLoadingResumeVersions(true);

    try {
      const response = await fetch(`${API_BASE_URL}/resume-versions`);

      if (!response.ok) {
        throw new Error(`GET /resume-versions failed with ${response.status}`);
      }

      setResumeVersions(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingResumeVersions(false);
    }
  }

  async function saveResumeVersion(event) {
    event.preventDefault();
    setSavingResumeVersion(true);
    setStatus("");
    setError("");

    const payload = {
      name: resumeVersionForm.name,
      target_role: resumeVersionForm.target_role || null,
      resume_text: resumeVersionForm.resume_text,
      notes: resumeVersionForm.notes || null,
    };
    const url = editingResumeVersionId
      ? `${API_BASE_URL}/resume-versions/${editingResumeVersionId}`
      : `${API_BASE_URL}/resume-versions`;
    const method = editingResumeVersionId ? "PUT" : "POST";

    try {
      const response = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`${method} /resume-versions failed with ${response.status}: ${detail}`);
      }

      setResumeVersionForm({
        name: "",
        target_role: "",
        resume_text: "",
        notes: "",
      });
      setEditingResumeVersionId(null);
      setStatus("Resume version saved.");
      await loadResumeVersions();
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingResumeVersion(false);
    }
  }

  async function uploadResumeVersionFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";

    if (!file) {
      return;
    }

    setUploadingResumeVersion(true);
    setError("");
    setStatus("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE_URL}/resume-versions/parse-upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`POST /resume-versions/parse-upload failed with ${response.status}: ${detail}`);
      }

      const result = await response.json();
      const fallbackName = result.filename.replace(/\.[^.]+$/, "");
      setResumeVersionForm((current) => ({
        ...current,
        name: current.name || fallbackName,
        resume_text: result.resume_text,
      }));
      setStatus(`Loaded ${result.filename}. Review and save this resume version.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploadingResumeVersion(false);
    }
  }

  function editResumeVersion(version) {
    setEditingResumeVersionId(version.id);
    setResumeVersionForm({
      name: version.name ?? "",
      target_role: version.target_role ?? "",
      resume_text: version.resume_text ?? "",
      notes: version.notes ?? "",
    });
  }

  async function deleteResumeVersion(versionId) {
    setError("");
    setStatus("");

    try {
      const response = await fetch(`${API_BASE_URL}/resume-versions/${versionId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`DELETE /resume-versions/${versionId} failed with ${response.status}: ${detail}`);
      }

      if (editingResumeVersionId === versionId) {
        setEditingResumeVersionId(null);
        setResumeVersionForm({
          name: "",
          target_role: "",
          resume_text: "",
          notes: "",
        });
      }
      setApplicationForm((current) => ({
        ...current,
        resume_version_id:
          String(current.resume_version_id) === String(versionId)
            ? ""
            : current.resume_version_id,
      }));
      setStatus("Resume version deleted.");
      await Promise.all([
        loadResumeVersions(),
        loadCoverLetters(),
        loadTrackedApplications(),
      ]);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadResumeSuggestions() {
    if (!selectedJob) {
      return;
    }

    setLoadingResumeSuggestions(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/assistant/resume-suggestions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          raw_job_id: selectedJob.id,
          resume_version_id: suggestionResumeVersionId
            ? Number(suggestionResumeVersionId)
            : null,
        }),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`POST /assistant/resume-suggestions failed with ${response.status}: ${detail}`);
      }

      setResumeSuggestions(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingResumeSuggestions(false);
    }
  }

  async function loadCoverLetterDraft() {
    if (!selectedJob) {
      return;
    }

    setLoadingCoverLetter(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/assistant/cover-letter`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          raw_job_id: selectedJob.id,
          resume_version_id: coverLetterResumeVersionId
            ? Number(coverLetterResumeVersionId)
            : null,
        }),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`POST /assistant/cover-letter failed with ${response.status}: ${detail}`);
      }

      const draft = await response.json();
      setCoverLetterDraft(draft);
      setCoverLetterName(`${draft.company || "Company"} - ${draft.job_title}`);
      setEditingCoverLetterId(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingCoverLetter(false);
    }
  }

  async function loadCoverLetters() {
    setLoadingCoverLetters(true);

    try {
      const response = await fetch(`${API_BASE_URL}/cover-letters`);

      if (!response.ok) {
        throw new Error(`GET /cover-letters failed with ${response.status}`);
      }

      setCoverLetters(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingCoverLetters(false);
    }
  }

  async function saveCoverLetter() {
    if (!coverLetterDraft || !coverLetterName.trim()) {
      return;
    }

    setSavingCoverLetter(true);
    setError("");
    setStatus("");

    const payload = {
      name: coverLetterName.trim(),
      raw_job_id: coverLetterDraft.raw_job_id,
      resume_version_id: coverLetterDraft.resume_version_id,
      draft: coverLetterDraft.draft,
      evidence: coverLetterDraft.evidence ?? [],
      matched_keywords: coverLetterDraft.matched_keywords ?? [],
      caveats: coverLetterDraft.caveats ?? [],
    };
    const url = editingCoverLetterId
      ? `${API_BASE_URL}/cover-letters/${editingCoverLetterId}`
      : `${API_BASE_URL}/cover-letters`;
    const method = editingCoverLetterId ? "PUT" : "POST";

    try {
      const response = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`${method} /cover-letters failed with ${response.status}: ${detail}`);
      }

      const saved = await response.json();
      setCoverLetterDraft(saved);
      setCoverLetterName(saved.name);
      setEditingCoverLetterId(saved.id);
      setApplicationForm((current) => ({
        ...current,
        cover_letter_id: String(saved.id),
      }));
      setStatus("Cover letter saved to Documents.");
      await loadCoverLetters();
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingCoverLetter(false);
    }
  }

  async function openCoverLetter(coverLetter) {
    setActiveView("jobs");
    await loadJobDetail(coverLetter.raw_job_id);
    setCoverLetterDraft(coverLetter);
    setCoverLetterResumeVersionId(
      coverLetter.resume_version_id ? String(coverLetter.resume_version_id) : "",
    );
    setCoverLetterName(coverLetter.name);
    setEditingCoverLetterId(coverLetter.id);
  }

  async function deleteCoverLetter(coverLetterId) {
    setError("");
    setStatus("");

    try {
      const response = await fetch(`${API_BASE_URL}/cover-letters/${coverLetterId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`DELETE /cover-letters/${coverLetterId} failed with ${response.status}: ${detail}`);
      }

      if (editingCoverLetterId === coverLetterId) {
        setCoverLetterDraft(null);
        setCoverLetterName("");
        setEditingCoverLetterId(null);
      }
      setApplicationForm((current) => ({
        ...current,
        cover_letter_id:
          String(current.cover_letter_id) === String(coverLetterId)
            ? ""
            : current.cover_letter_id,
      }));
      setStatus("Cover letter deleted.");
      await Promise.all([loadCoverLetters(), loadTrackedApplications()]);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadProfile() {
    setLoadingProfile(true);

    try {
      const response = await fetch(`${API_BASE_URL}/profile`);

      if (!response.ok) {
        throw new Error(`GET /profile failed with ${response.status}`);
      }

      const nextProfile = await response.json();
      setProfile(nextProfile);

      if (nextProfile) {
        setProfileForm({
          name: nextProfile.name ?? "",
          source_resume_version_id: nextProfile.source_resume_version_id
            ? String(nextProfile.source_resume_version_id)
            : "",
          target_roles: nextProfile.target_roles ?? "",
          target_locations: nextProfile.target_locations ?? "",
        });
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingProfile(false);
    }
  }

  async function saveProfile(event) {
    event.preventDefault();
    setSavingProfile(true);
    setProfileMessage("");
    setError("");

    try {
      const endpoint = profileForm.source_resume_version_id
        ? `${API_BASE_URL}/profile/from-resume-version`
        : `${API_BASE_URL}/profile`;
      const method = profileForm.source_resume_version_id ? "POST" : "PUT";
      const payload = profileForm.source_resume_version_id
        ? {
            resume_version_id: Number(profileForm.source_resume_version_id),
            name: profileForm.name || null,
            target_roles: profileForm.target_roles || null,
            target_locations: profileForm.target_locations || null,
          }
        : {
            name: profileForm.name || null,
            resume_text: profile?.resume_text ?? "",
            target_roles: profileForm.target_roles || null,
            target_locations: profileForm.target_locations || null,
          };
      const response = await fetch(endpoint, {
        method,
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`${method} ${endpoint} failed with ${response.status}: ${detail}`);
      }

      const nextProfile = await response.json();
      setProfile(nextProfile);
      setProfileMessage("Profile built from the selected resume version.");
      await loadSkillGaps();
      await loadJobs();
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingProfile(false);
    }
  }

  async function uploadResume(event) {
    const file = event.target.files?.[0];
    event.target.value = "";

    if (!file) {
      return;
    }

    setUploadingResume(true);
    setProfileMessage("");
    setError("");

    const formData = new FormData();
    formData.append("file", file);
    if (profileForm.name) formData.append("name", profileForm.name);
    if (profileForm.target_roles) formData.append("target_roles", profileForm.target_roles);
    if (profileForm.target_locations) {
      formData.append("target_locations", profileForm.target_locations);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/profile/upload-resume`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`POST /profile/upload-resume failed with ${response.status}: ${detail}`);
      }

      const nextProfile = await response.json();
      setProfile(nextProfile);
      setProfileForm({
        name: nextProfile.name ?? "",
        source_resume_version_id: nextProfile.source_resume_version_id
          ? String(nextProfile.source_resume_version_id)
          : "",
        target_roles: nextProfile.target_roles ?? "",
        target_locations: nextProfile.target_locations ?? "",
      });
      setProfileMessage(`Uploaded ${file.name}. Profile saved from resume file.`);
      await loadSkillGaps();
      await loadJobs();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploadingResume(false);
    }
  }

  async function markSkillAsKnown(item) {
    const skillKey = `${item.category}:${item.skill}`;
    setSavingManualSkill(skillKey);
    setProfileMessage("");
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/profile/skills`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          skill: item.skill,
          category: item.category,
        }),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`POST /profile/skills failed with ${response.status}: ${detail}`);
      }

      setProfile(await response.json());
      setProfileMessage(`${item.skill} marked as a skill you already know.`);
      await loadSkillGaps();
      await loadJobs();
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingManualSkill("");
    }
  }

  async function loadSources() {
    setLoadingSources(true);

    try {
      const response = await fetch(`${API_BASE_URL}/jobs/sources`);

      if (!response.ok) {
        throw new Error(`GET /jobs/sources failed with ${response.status}`);
      }

      setSources(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingSources(false);
    }
  }

  async function loadCollectionRuns() {
    setLoadingCollectionRuns(true);

    try {
      const response = await fetch(`${API_BASE_URL}/jobs/collection-runs?limit=20`);

      if (!response.ok) {
        throw new Error(`GET /jobs/collection-runs failed with ${response.status}`);
      }

      setCollectionRuns(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingCollectionRuns(false);
    }
  }

  async function loadSkillGaps() {
    setLoadingSkillGaps(true);

    const params = new URLSearchParams();
    params.set("us_only", "true");
    params.set("career_eligible_only", String(careerEligibleOnly));
    params.set("min_target_relevance", targetRelevantOnly ? "50" : "0");
    if (maxPostingAgeDays) params.set("max_posting_age_days", maxPostingAgeDays);

    try {
      const response = await fetch(`${API_BASE_URL}/profile/skill-gaps?${params.toString()}`);

      if (!response.ok) {
        throw new Error(`GET /profile/skill-gaps failed with ${response.status}`);
      }

      setSkillGapSummary(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingSkillGaps(false);
    }
  }

  async function loadMarketSummary() {
    setLoadingSummary(true);

    try {
      const params = new URLSearchParams();
      if (usOnly) params.set("us_only", "true");
      params.set("career_eligible_only", String(careerEligibleOnly));
      if (dashboardRoleCategory) params.set("role_category", dashboardRoleCategory);
      if (targetRelevantOnly) params.set("min_target_relevance", "50");
      if (maxPostingAgeDays) params.set("max_posting_age_days", maxPostingAgeDays);
      const response = await fetch(`${API_BASE_URL}/jobs/market-summary?${params.toString()}`);

      if (!response.ok) {
        throw new Error(`GET /jobs/market-summary failed with ${response.status}`);
      }

      setMarketSummary(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingSummary(false);
    }
  }

  async function collectJobs(event) {
    event.preventDefault();
    setCollecting(true);
    setStatus("");
    setError("");

    const tokens = boardTokens
      .split(",")
      .map((token) => token.trim())
      .filter(Boolean);

    try {
      const response = await fetch(`${API_BASE_URL}/jobs/collect`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          source: collectorSource,
          board_tokens: tokens.length ? tokens : undefined,
          max_jobs_per_board: Number(maxJobs),
        }),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`POST /jobs/collect failed with ${response.status}: ${detail}`);
      }

      const result = await response.json();
      const failedBoardMessage = result.failed_boards.length
        ? ` Failed boards: ${result.failed_boards.join(", ")}.`
        : "";
      setStatus(
        `Collection ${formatLabel(result.status)}. Processed ${result.boards_requested} boards. Fetched ${result.fetched}. Inserted ${result.inserted}. Updated ${result.updated}. Reactivated ${result.reactivated}. Closed ${result.closed}. Reconciled ${result.boards_reconciled} complete boards.${failedBoardMessage}`,
      );
      await loadJobs();
      await loadMarketSummary();
      await loadSkillGaps();
    } catch (err) {
      setError(err.message);
    } finally {
      await loadCollectionRuns();
      setCollecting(false);
    }
  }

  async function syncAllSources() {
    setSyncingAll(true);
    setStatus("");
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/jobs/sync-all`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          max_jobs_per_board: Number(maxJobs),
        }),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`POST /jobs/sync-all failed with ${response.status}: ${detail}`);
      }

      const runs = await response.json();
      const completedRuns = runs.filter((run) =>
        ["success", "partial_success"].includes(run.status),
      );
      const partialRuns = runs.filter((run) => run.status === "partial_success");
      const failedRuns = runs.filter((run) => run.status === "failed");
      const runningRuns = runs.filter((run) => run.status === "running");
      const totals = completedRuns.reduce(
        (current, run) => ({
          fetched: current.fetched + run.fetched,
          inserted: current.inserted + run.inserted,
          updated: current.updated + run.updated,
          closed: current.closed + run.closed,
        }),
        { fetched: 0, inserted: 0, updated: 0, closed: 0 },
      );
      setStatus(
        `Synced ${completedRuns.length} sources. Fetched ${totals.fetched}. Inserted ${totals.inserted}. Updated ${totals.updated}. Closed ${totals.closed}.${partialRuns.length ? ` ${partialRuns.length} source partially succeeded; review board details.` : ""}${failedRuns.length ? ` ${failedRuns.length} source failed; review Collection History.` : ""}${runningRuns.length ? ` ${runningRuns.length} source was already running and was skipped.` : ""}`,
      );
      await Promise.all([
        loadJobs(),
        loadMarketSummary(),
        loadSkillGaps(),
        loadCollectionRuns(),
      ]);
    } catch (err) {
      setError(err.message);
      await loadCollectionRuns();
    } finally {
      setSyncingAll(false);
    }
  }

  async function deduplicateJobs() {
    setDeduplicating(true);
    setStatus("");
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/jobs/deduplicate`, {
        method: "POST",
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`POST /jobs/deduplicate failed with ${response.status}: ${detail}`);
      }

      const result = await response.json();
      setStatus(
        `Deduplicated ${result.raw_jobs} raw jobs into ${result.canonical_jobs} canonical jobs. Duplicate rate ${Math.round(result.duplicate_rate * 100)}%.`,
      );
      await loadMarketSummary();
    } catch (err) {
      setError(err.message);
    } finally {
      setDeduplicating(false);
    }
  }

  useEffect(() => {
    loadSources();
    loadCollectionRuns();
    loadMarketSummary();
    loadJobs();
    if (!newJobsSince && !discoverySessionStarted.current) {
      discoverySessionStarted.current = true;
      startJobDiscoverySession();
    }
    loadTrackedApplications();
    loadResumeVersions();
    loadCoverLetters();
    loadProfile();
    loadSkillGaps();
  }, []);

  useEffect(() => {
    if (activeView !== "data_sources") {
      return undefined;
    }

    loadCollectionRuns();
    const intervalId = window.setInterval(loadCollectionRuns, 15000);
    return () => window.clearInterval(intervalId);
  }, [activeView]);

  return (
    <main className="app-shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">AI Job Search Copilot</p>
          <h1>{NAV_ITEMS.find((item) => item.id === activeView)?.label}</h1>
        </div>
        <button
          className="secondary-button"
          onClick={() => {
            loadJobs();
            loadMarketSummary();
            loadSkillGaps();
            loadCoverLetters();
          }}
          disabled={loadingJobs || loadingSummary}
        >
          {loadingJobs || loadingSummary ? "Refreshing" : "Refresh"}
        </button>
      </section>

      <nav className="app-nav" aria-label="Primary">
        {NAV_ITEMS.map((item) => (
          <button
            className={activeView === item.id ? "active" : ""}
            key={item.id}
            type="button"
            onClick={() => setActiveView(item.id)}
          >
            <item.icon aria-hidden="true" />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      {error && <div className="message error global-message">{error}</div>}
      {!error && status && <div className="message global-message">{status}</div>}

      {activeView === "dashboard" && (
        <>
      <section className="metrics" aria-label="Job metrics">
        {stats.map((item) => (
          <div className="metric" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
      </section>

      <section className="panel dashboard-controls">
        <div className="panel-header">
          <h2>Market Dashboard</h2>
          <span>{loadingSummary ? "Loading" : formatLabel(dashboardRoleCategory || "all roles")}</span>
        </div>
        <div className="dashboard-filter-row">
          <label>
            Dashboard role
            <select
              value={dashboardRoleCategory}
              onChange={(event) => setDashboardRoleCategory(event.target.value)}
            >
              <option value="">All roles</option>
              <option value="data_analytics">Data Analytics</option>
              <option value="data_engineering">Data Engineering</option>
              <option value="ai_ml">AI / ML</option>
              <option value="risk_compliance">Risk / Compliance</option>
              <option value="finance_accounting">Finance / Accounting</option>
              <option value="product">Product</option>
              <option value="engineering">Engineering</option>
              <option value="sales_gtm">Sales / GTM</option>
              <option value="analytics_adjacent">Analytics Adjacent</option>
              <option value="unknown">Unknown</option>
            </select>
          </label>
          <button
            className="secondary-button"
            type="button"
            onClick={loadMarketSummary}
            disabled={loadingSummary}
          >
            Apply Dashboard Filter
          </button>
        </div>
      </section>

      {marketSummary && (
        <section className="summary-grid" aria-label="Market summary">
          <DistributionList title="Role Categories" items={marketSummary.role_categories} />
          <DistributionList title="Top Skills" items={marketSummary.top_skills} />
          <DistributionList title="Top States" items={marketSummary.top_states} />
        </section>
      )}
        </>
      )}

      {activeView === "profile" && (
      <section className="panel profile-panel">
        <div className="panel-header">
          <h2>Candidate Profile</h2>
          <span>{loadingProfile ? "Loading" : profile ? "Saved" : "Not created"}</span>
        </div>

        <form className="profile-form" onSubmit={saveProfile}>
          <div className="profile-grid">
            <label>
              Name
              <input
                value={profileForm.name}
                onChange={(event) =>
                  setProfileForm((current) => ({
                    ...current,
                    name: event.target.value,
                  }))
                }
                placeholder="Your name"
              />
            </label>
            <label>
              Target roles
              <input
                value={profileForm.target_roles}
                onChange={(event) =>
                  setProfileForm((current) => ({
                    ...current,
                    target_roles: event.target.value,
                  }))
                }
                placeholder="Data analyst, risk analyst, product analyst"
              />
            </label>
            <label>
              Target locations
              <input
                value={profileForm.target_locations}
                onChange={(event) =>
                  setProfileForm((current) => ({
                    ...current,
                    target_locations: event.target.value,
                  }))
                }
                placeholder="US, New York, Bay Area, Remote"
              />
            </label>
            <label>
              Source resume
              <select
                value={profileForm.source_resume_version_id}
                onChange={(event) =>
                  setProfileForm((current) => ({
                    ...current,
                    source_resume_version_id: event.target.value,
                  }))
                }
                required
              >
                <option value="">Select a document</option>
                {resumeVersions.map((version) => (
                  <option value={version.id} key={version.id}>
                    {version.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="profile-actions">
            <button
              className="primary-button"
              type="submit"
              disabled={savingProfile || !profileForm.source_resume_version_id}
            >
              {savingProfile ? "Saving" : "Build Profile"}
            </button>
            {profileMessage && <span>{profileMessage}</span>}
          </div>
        </form>

        {profile && (
          <div className="structured-profile">
            <section className="profile-section">
              <h3>Work Experience</h3>
              <div className="profile-card-list">
                {profile.work_experience.map((item, index) => (
                  <article className="profile-info-card" key={`${item.company}-${item.title}-${index}`}>
                    <div>
                      <h4>{item.title}</h4>
                      <p>{item.company}</p>
                      <span>{[item.location, item.period].filter(Boolean).join(" / ")}</span>
                    </div>
                    <ul>
                      {item.bullets.slice(0, 3).map((bullet) => (
                        <li key={bullet}>{bullet}</li>
                      ))}
                    </ul>
                  </article>
                ))}
                {!profile.work_experience.length && (
                  <p className="panel-copy">No work experience parsed yet.</p>
                )}
              </div>
            </section>

            <section className="profile-section">
              <h3>Education</h3>
              <div className="profile-card-list">
                {profile.education.map((item, index) => (
                  <article className="profile-info-card" key={`${item.school}-${index}`}>
                    <h4>{item.school}</h4>
                    <p>{item.degree || "Degree not parsed"}</p>
                    {item.period && <span>{item.period}</span>}
                  </article>
                ))}
                {!profile.education.length && (
                  <p className="panel-copy">No education parsed yet.</p>
                )}
              </div>
            </section>

            <section className="profile-section">
              <h3>Domain Experience</h3>
              <div className="profile-card-list">
                {profile.domain_experience.map((item) => (
                  <article className="profile-info-card" key={item.domain}>
                    <h4>{item.domain}</h4>
                    <ul>
                      {item.evidence.slice(0, 3).map((evidence) => (
                        <li key={evidence}>{evidence}</li>
                      ))}
                    </ul>
                  </article>
                ))}
                {!profile.domain_experience.length && (
                  <p className="panel-copy">No domain experience parsed yet.</p>
                )}
              </div>
            </section>
          </div>
        )}

        {profile?.extracted_skills?.length > 0 && (
          <div className="profile-skills">
            <h3>Extracted Skills</h3>
            <div className="skill-chips">
              {profile.extracted_skills.map((item) => (
                <span key={`${item.category}-${item.skill}`}>
                  {item.skill}
                </span>
              ))}
            </div>
          </div>
        )}

        {profile?.manual_skills?.length > 0 && (
          <div className="profile-skills">
            <h3>Confirmed Skills</h3>
            <div className="skill-chips">
              {profile.manual_skills.map((item) => (
                <span key={`manual-${item.category}-${item.skill}`}>
                  {item.skill}
                </span>
              ))}
            </div>
          </div>
        )}
      </section>
      )}

      {activeView === "documents" && (
      <section className="documents-layout">
        <section className="panel">
          <div className="panel-header">
            <h2>{editingResumeVersionId ? "Edit Resume Version" : "New Resume Version"}</h2>
            <span>{savingResumeVersion ? "Saving" : `${resumeVersions.length} versions`}</span>
          </div>

          <form className="profile-form" onSubmit={saveResumeVersion}>
            <div className="profile-grid">
              <label>
                Version name
                <input
                  value={resumeVersionForm.name}
                  onChange={(event) =>
                    setResumeVersionForm((current) => ({
                      ...current,
                      name: event.target.value,
                    }))
                  }
                  placeholder="Data Analytics Resume v1"
                  required
                />
              </label>
              <label>
                Target role
                <input
                  value={resumeVersionForm.target_role}
                  onChange={(event) =>
                    setResumeVersionForm((current) => ({
                      ...current,
                      target_role: event.target.value,
                    }))
                  }
                  placeholder="Data Analyst, Data Engineer, Risk Analytics"
                />
              </label>
              <label>
                Start from profile
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() =>
                    setResumeVersionForm((current) => ({
                      ...current,
                      resume_text: profile?.resume_text ?? current.resume_text,
                    }))
                  }
                  disabled={!profile?.resume_text}
                >
                  Use Profile Resume
                </button>
              </label>
            </div>

            <label>
              Resume text
              <div className="resume-upload-row">
                <input
                  type="file"
                  accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
                  onChange={uploadResumeVersionFile}
                  disabled={uploadingResumeVersion || savingResumeVersion}
                />
                <span>
                  {uploadingResumeVersion ? "Uploading resume" : "Upload PDF, TXT, or MD"}
                </span>
              </div>
              <textarea
                className="resume-textarea"
                value={resumeVersionForm.resume_text}
                onChange={(event) =>
                  setResumeVersionForm((current) => ({
                    ...current,
                    resume_text: event.target.value,
                  }))
                }
                placeholder="Paste this resume version here."
                required
              />
            </label>

            <label>
              Notes
              <textarea
                value={resumeVersionForm.notes}
                onChange={(event) =>
                  setResumeVersionForm((current) => ({
                    ...current,
                    notes: event.target.value,
                  }))
                }
                placeholder="What this version is optimized for, changed bullets, or keywords."
              />
            </label>

            <div className="profile-actions">
              <button
                className="primary-button"
                type="submit"
                disabled={
                  savingResumeVersion ||
                  !resumeVersionForm.name.trim() ||
                  !resumeVersionForm.resume_text.trim()
                }
              >
                {savingResumeVersion ? "Saving" : "Save Resume Version"}
              </button>
              {editingResumeVersionId && (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => {
                    setEditingResumeVersionId(null);
                    setResumeVersionForm({
                      name: "",
                      target_role: "",
                      resume_text: "",
                      notes: "",
                    });
                  }}
                >
                  Cancel Edit
                </button>
              )}
            </div>
          </form>
        </section>

        <section className="panel">
          <div className="panel-header">
            <h2>Resume Versions</h2>
            <span>{loadingResumeVersions ? "Loading" : `${resumeVersions.length} saved`}</span>
          </div>

          <div className="resume-version-list">
            {resumeVersions.map((version) => (
              <article className="resume-version-card" key={version.id}>
                <div>
                  <h3>{version.name}</h3>
                  <p>{version.target_role || "No target role set"}</p>
                </div>
                <div className="resume-version-meta">
                  <span>{formatDate(version.updated_at)}</span>
                  <span>{version.resume_text.length.toLocaleString()} chars</span>
                </div>
                {version.notes && <p className="panel-copy">{version.notes}</p>}
                <div className="resume-version-actions">
                  <button className="secondary-button" type="button" onClick={() => editResumeVersion(version)}>
                    Edit
                  </button>
                  <button className="table-button" type="button" onClick={() => deleteResumeVersion(version.id)}>
                    Delete
                  </button>
                </div>
              </article>
            ))}
            {!resumeVersions.length && (
              <div className="empty-card">
                No resume versions yet. Create versions for data analytics, data engineering, risk analytics, or AI roles.
              </div>
            )}
          </div>
        </section>

        <section className="panel cover-letter-library">
          <div className="panel-header">
            <h2>Cover Letters</h2>
            <span>{loadingCoverLetters ? "Loading" : `${coverLetters.length} saved`}</span>
          </div>

          <div className="cover-letter-library-list">
            {coverLetters.map((coverLetter) => (
              <article className="cover-letter-library-card" key={coverLetter.id}>
                <div className="cover-letter-library-heading">
                  <div>
                    <h3>{coverLetter.name}</h3>
                    <p>
                      {coverLetter.company || "Unknown company"} / {coverLetter.job_title}
                    </p>
                  </div>
                  <span>{formatDate(coverLetter.updated_at)}</span>
                </div>
                <p className="cover-letter-preview">
                  {coverLetter.draft.slice(0, 240)}
                  {coverLetter.draft.length > 240 ? "..." : ""}
                </p>
                <div className="resume-version-meta">
                  <span>{coverLetter.resume_version_name || "Profile only"}</span>
                  <span>{coverLetter.draft.length.toLocaleString()} chars</span>
                </div>
                <div className="resume-version-actions">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => openCoverLetter(coverLetter)}
                  >
                    Open and Edit
                  </button>
                  <button
                    className="table-button"
                    type="button"
                    onClick={() => deleteCoverLetter(coverLetter.id)}
                  >
                    Delete
                  </button>
                </div>
              </article>
            ))}
            {!coverLetters.length && (
              <div className="empty-card">
                Generate a cover letter from a job detail page, then save it here.
              </div>
            )}
          </div>
        </section>
      </section>
      )}

      {activeView === "skill_gaps" && (
      <section className="panel skill-gap-panel">
        <div className="panel-header">
          <h2>Skill Gap Summary</h2>
          <span>
            {loadingSkillGaps
              ? "Loading"
              : `${skillGapSummary?.analyzed_jobs_count ?? 0} jobs analyzed`}
          </span>
        </div>

        {!skillGapSummary?.profile_exists && (
          <p className="panel-copy">
            Save your resume profile first to compare your skills with target jobs.
          </p>
        )}

        {skillGapSummary?.profile_exists && (
          <div className="skill-gap-content">
            <div className="gap-overview">
              <div className="metric compact-metric">
                <span>Profile skills</span>
                <strong>{skillGapSummary.profile_skills_count}</strong>
              </div>
              <div className="metric compact-metric">
                <span>Analyzed jobs</span>
                <strong>{skillGapSummary.analyzed_jobs_count}</strong>
              </div>
            </div>

            <div className="gap-grid">
              <article className="gap-card">
                <h3>Top Missing Skills</h3>
                <div className="gap-list">
                  {skillGapSummary.top_missing_skills.map((item) => (
                    <div className="gap-row" key={`${item.category}-${item.skill}`}>
                      <span>{item.skill}</span>
                      <strong>{item.missing_count}</strong>
                      <button
                        className="inline-skill-button"
                        type="button"
                        onClick={() => markSkillAsKnown(item)}
                        disabled={savingManualSkill === `${item.category}:${item.skill}`}
                      >
                        {savingManualSkill === `${item.category}:${item.skill}`
                          ? "Saving"
                          : "I know this"}
                      </button>
                    </div>
                  ))}
                  {!skillGapSummary.top_missing_skills.length && (
                    <p className="panel-copy">No missing skills found for the current filters.</p>
                  )}
                </div>
              </article>

              <article className="gap-card">
                <h3>By Role Category</h3>
                <div className="role-gap-list">
                  {skillGapSummary.gaps_by_role.slice(0, 4).map((role) => (
                    <div className="role-gap" key={role.role_category}>
                      <div className="role-gap-header">
                        <span>{formatLabel(role.role_category)}</span>
                        <strong>{role.analyzed_jobs_count} jobs</strong>
                      </div>
                      <div className="skill-chips">
                        {role.top_missing_skills.slice(0, 4).map((item) => (
                          <span key={`${role.role_category}-${item.skill}`}>
                            {item.skill} ({item.missing_count})
                          </span>
                        ))}
                        {!role.top_missing_skills.length && <span>No gaps</span>}
                      </div>
                    </div>
                  ))}
                  {!skillGapSummary.gaps_by_role.length && (
                    <p className="panel-copy">No role-specific gaps found.</p>
                  )}
                </div>
              </article>
            </div>
          </div>
        )}
      </section>
      )}

      {activeView === "data_sources" && (
      <section className="workspace data-sources-workspace">
        <aside className="panel">
          <h2>Collector</h2>
          <p className="panel-copy">
            Uses the built-in public job board registry by default. Add board tokens only
            when you want to override the registry.
          </p>
          <form onSubmit={collectJobs} className="form-stack">
            <label>
              Source
              <select
                value={collectorSource}
                onChange={(event) => {
                  setCollectorSource(event.target.value);
                  setBoardTokens("");
                }}
              >
                <option value="greenhouse">Greenhouse</option>
                <option value="lever">Lever</option>
                <option value="ashby">Ashby</option>
              </select>
            </label>
            <label>
              Optional board tokens
              <input
                value={boardTokens}
                onChange={(event) => setBoardTokens(event.target.value)}
                placeholder={
                  collectorSource === "lever"
                    ? "plaid"
                    : collectorSource === "ashby"
                      ? "ramp, sentilink"
                      : "stripe, databricks"
                }
              />
            </label>

            <label>
              Max jobs per board
              <input
                min="1"
                max="250"
                type="number"
                value={maxJobs}
                onChange={(event) => setMaxJobs(event.target.value)}
              />
            </label>

            <button
              className="primary-button"
              type="button"
              onClick={syncAllSources}
              disabled={syncingAll || collecting || hasRunningCollection}
            >
              {syncingAll
                ? "Syncing All Sources"
                : hasRunningCollection
                  ? "A Source Is Already Running"
                  : "Sync All Sources"}
            </button>
            <button
              className="secondary-button"
              type="submit"
              disabled={
                collecting
                || syncingAll
                || runningCollectionSources.has(collectorSource)
              }
            >
              {collecting
                ? "Collecting"
                : runningCollectionSources.has(collectorSource)
                  ? `${formatLabel(collectorSource)} Is Running`
                  : "Collect Selected Source"}
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={deduplicateJobs}
              disabled={deduplicating || hasRunningCollection}
            >
              {deduplicating ? "Deduplicating" : "Deduplicate Jobs"}
            </button>
          </form>

          {(status || error) && (
            <div className={error ? "message error" : "message"}>{error || status}</div>
          )}

          <div className="source-list">
            <div className="source-list-header">
              <h3>Built-in Sources</h3>
              <span>{loadingSources ? "Loading" : `${filteredSources.length} companies`}</span>
            </div>
            <div className="source-chips">
              {filteredSources.map((source) => (
                <button
                  className="source-chip"
                  key={`${source.source}-${source.board_token}`}
                  type="button"
                  onClick={() => setBoardTokens(source.board_token)}
                >
                  {source.name}
                </button>
              ))}
            </div>
          </div>

          <section className="collection-history">
            <div className="collection-history-header">
              <div>
                <h3>Collection History</h3>
                <p>Recent manual, full, and scheduled source runs.</p>
              </div>
              <button
                className="secondary-button"
                type="button"
                onClick={loadCollectionRuns}
                disabled={loadingCollectionRuns}
              >
                {loadingCollectionRuns ? "Refreshing" : "Refresh"}
              </button>
            </div>
            <div className="table-wrap collection-runs-table">
              <table>
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Trigger</th>
                    <th>Status</th>
                    <th>Started</th>
                    <th>Duration</th>
                    <th>Boards</th>
                    <th>Fetched</th>
                    <th>Inserted</th>
                    <th>Updated</th>
                    <th>Closed</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {collectionRuns.map((run) => (
                    <tr key={run.id}>
                      <td>{formatLabel(run.source)}</td>
                      <td>{formatLabel(run.trigger)}</td>
                      <td>
                        <span className={`run-status ${run.status}`}>
                          {formatLabel(run.status)}
                        </span>
                      </td>
                      <td>{formatDateTime(run.started_at)}</td>
                      <td>{formatDuration(run.started_at, run.completed_at)}</td>
                      <td>
                        {run.board_runs?.length ? (
                          <details className="board-run-details">
                            <summary>
                              {run.boards_completed}/{run.boards_requested}
                              {run.board_runs.some((board) => board.status === "failed")
                                ? ` (${run.board_runs.filter((board) => board.status === "failed").length} failed)`
                                : ""}
                            </summary>
                            <div className="board-run-list">
                              {run.board_runs.map((board) => (
                                <div className="board-run-item" key={board.id}>
                                  <span className={`run-status ${board.status}`}>
                                    {formatLabel(board.status)}
                                  </span>
                                  <strong>{board.company_name}</strong>
                                  <span>{board.fetched} jobs</span>
                                  {board.error_message && (
                                    <span title={board.error_message}>{board.error_message}</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </details>
                        ) : (
                          `${run.boards_completed}/${run.boards_requested}`
                        )}
                      </td>
                      <td>{run.fetched}</td>
                      <td>{run.inserted}</td>
                      <td>{run.updated}</td>
                      <td>{run.closed}</td>
                      <td className="collection-error" title={run.error_message || ""}>
                        {run.error_message || "-"}
                      </td>
                    </tr>
                  ))}
                  {!collectionRuns.length && (
                    <tr>
                      <td className="empty-cell" colSpan="11">
                        {loadingCollectionRuns ? "Loading collection history" : "No collection runs yet"}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </aside>
      </section>
      )}

      {activeView === "jobs" && (
      <section className="jobs-view">
        <section className="panel results-panel">
          <div className="panel-header">
            <h2>Jobs</h2>
            <div className="panel-header-actions">
              <span>
                {loadingJobs ? "Loading" : `${jobs.length} shown`}
                {loadingJobDetail ? " / Opening detail" : ""}
              </span>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setShowManualJobForm((current) => !current)}
              >
                {showManualJobForm ? "Close Form" : "Add External Job"}
              </button>
            </div>
          </div>

          {showManualJobForm && (
            <form className="manual-job-form" onSubmit={saveManualJob}>
              <div className="manual-job-form-heading">
                <div>
                  <h3>Add External Job</h3>
                  <p>Add a job found or applied to outside the built-in data sources.</p>
                </div>
                <span>Private to your account</span>
              </div>
              <div className="manual-job-grid">
                <label>
                  Source
                  <select
                    value={manualJobForm.source}
                    onChange={(event) =>
                      setManualJobForm((current) => ({ ...current, source: event.target.value }))
                    }
                  >
                    <option value="linkedin">LinkedIn</option>
                    <option value="handshake">Handshake</option>
                    <option value="other">Other</option>
                  </select>
                </label>
                <label>
                  Company
                  <input
                    required
                    value={manualJobForm.company}
                    onChange={(event) =>
                      setManualJobForm((current) => ({ ...current, company: event.target.value }))
                    }
                    placeholder="Company name"
                  />
                </label>
                <label>
                  Job title
                  <input
                    required
                    value={manualJobForm.title}
                    onChange={(event) =>
                      setManualJobForm((current) => ({ ...current, title: event.target.value }))
                    }
                    placeholder="Data Analyst"
                  />
                </label>
                <label>
                  Location
                  <input
                    required
                    value={manualJobForm.location}
                    onChange={(event) =>
                      setManualJobForm((current) => ({ ...current, location: event.target.value }))
                    }
                    placeholder="Palo Alto, CA"
                  />
                </label>
                <label className="manual-job-url">
                  Job URL
                  <input
                    type="url"
                    value={manualJobForm.job_url}
                    onChange={(event) =>
                      setManualJobForm((current) => ({ ...current, job_url: event.target.value }))
                    }
                    placeholder="https://..."
                  />
                </label>
                <label>
                  Posted date
                  <input
                    type="date"
                    value={manualJobForm.date_posted}
                    onChange={(event) =>
                      setManualJobForm((current) => ({ ...current, date_posted: event.target.value }))
                    }
                  />
                </label>
                <label>
                  Tracker status
                  <select
                    value={manualJobForm.status}
                    onChange={(event) =>
                      setManualJobForm((current) => ({ ...current, status: event.target.value }))
                    }
                  >
                    {APPLICATION_STATUS_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Applied date
                  <input
                    type="date"
                    value={manualJobForm.applied_date}
                    onChange={(event) =>
                      setManualJobForm((current) => ({ ...current, applied_date: event.target.value }))
                    }
                  />
                </label>
                <label>
                  Resume used
                  <select
                    value={manualJobForm.resume_version_id}
                    onChange={(event) =>
                      setManualJobForm((current) => ({
                        ...current,
                        resume_version_id: event.target.value,
                      }))
                    }
                  >
                    <option value="">Not selected</option>
                    {resumeVersions.map((version) => (
                      <option key={version.id} value={version.id}>
                        {version.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="manual-job-text-grid">
                <label className="manual-job-description">
                  Job description
                  <textarea
                    value={manualJobForm.description}
                    onChange={(event) =>
                      setManualJobForm((current) => ({ ...current, description: event.target.value }))
                    }
                    placeholder="Paste the job description to enable experience, skill, and Fit Score analysis."
                  />
                </label>
                <label className="manual-job-notes">
                  Tracker notes
                  <textarea
                    value={manualJobForm.notes}
                    onChange={(event) =>
                      setManualJobForm((current) => ({ ...current, notes: event.target.value }))
                    }
                    placeholder="Referral, application channel, or next step."
                  />
                </label>
              </div>
              <div className="manual-job-actions">
                <button className="primary-button" type="submit" disabled={savingManualJob}>
                  {savingManualJob ? "Saving" : "Add to Jobs and Tracker"}
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={savingManualJob}
                  onClick={() => setShowManualJobForm(false)}
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="job-discovery-bar">
            <div className="job-discovery-tabs" role="tablist" aria-label="Job discovery views">
              {[
                { value: "visible", label: "Visible" },
                { value: "new", label: "New" },
                { value: "unseen", label: "Unseen" },
                { value: "hidden", label: "Hidden" },
              ].map((option) => (
                <button
                  className={discoveryFilter === option.value ? "active" : ""}
                  type="button"
                  role="tab"
                  aria-selected={discoveryFilter === option.value}
                  disabled={loadingJobs || (option.value === "new" && !newJobsSince)}
                  key={option.value}
                  onClick={() => selectDiscoveryFilter(option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <span>
              {newJobsSince
                ? `New since ${formatDate(newJobsSince)}`
                : "Starting discovery session"}
            </span>
          </div>

          <div className="active-filter-bar" aria-label="Current job filters">
            <span>Filters</span>
            <div>
              {activeJobFilters.map((filter) => (
                <button
                  type="button"
                  className="filter-chip"
                  key={filter.id}
                  title={`Remove ${filter.label}`}
                  onClick={() => clearJobFilter(filter.id)}
                >
                  {filter.label}
                  <X aria-hidden="true" />
                </button>
              ))}
              {!activeJobFilters.length && <span className="no-active-filters">None</span>}
            </div>
          </div>

          <div className="filters">
            <label className={showAdvancedFilters ? "advanced-filter visible" : "advanced-filter"}>
              Company
              <input
                value={company}
                onChange={(event) => setCompany(event.target.value)}
                placeholder="stripe"
              />
            </label>
            <label>
              Location
              <input
                value={location}
                onChange={(event) => setLocation(event.target.value)}
                placeholder="US, New York, Remote"
              />
            </label>
            <label className={showAdvancedFilters ? "advanced-filter visible" : "advanced-filter"}>
              State
              <input
                value={jobState}
                onChange={(event) => setJobState(event.target.value)}
                placeholder="California, New York, Remote - US"
              />
            </label>
            <label>
              Work mode
              <select value={workMode} onChange={(event) => setWorkMode(event.target.value)}>
                <option value="">Any</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">Onsite</option>
                <option value="unknown">Unknown</option>
              </select>
            </label>
            <label>
              Seniority
              <select value={seniority} onChange={(event) => setSeniority(event.target.value)}>
                <option value="">Any</option>
                <option value="intern">Intern</option>
                <option value="entry">Entry</option>
                <option value="junior">Junior</option>
                <option value="mid">Mid</option>
                <option value="senior">Senior</option>
                <option value="lead">Lead</option>
                <option value="unknown">Unknown</option>
              </select>
            </label>
            <label className={showAdvancedFilters ? "advanced-filter visible" : "advanced-filter"}>
              Entry fit
              <select
                value={entryFitLevel}
                onChange={(event) => setEntryFitLevel(event.target.value)}
              >
                <option value="">Any</option>
                <option value="entry_friendly">Entry Friendly</option>
                <option value="possible_stretch">Possible Stretch</option>
                <option value="too_senior">Too Senior</option>
              </select>
            </label>
            <label>
              Role category
              <select
                value={roleCategory}
                onChange={(event) => setRoleCategory(event.target.value)}
              >
                <option value="">Any</option>
                <option value="data_analytics">Data Analytics</option>
                <option value="data_engineering">Data Engineering</option>
                <option value="ai_ml">AI / ML</option>
                <option value="risk_compliance">Risk / Compliance</option>
                <option value="finance_accounting">Finance / Accounting</option>
                <option value="product">Product</option>
                <option value="engineering">Engineering</option>
                <option value="sales_gtm">Sales / GTM</option>
                <option value="analytics_adjacent">Analytics Adjacent</option>
                <option value="unknown">Unknown</option>
              </select>
            </label>
            <label className={showAdvancedFilters ? "advanced-filter visible" : "advanced-filter"}>
              Full text
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="analytics"
              />
            </label>
            <label>
              Title
              <input
                value={titleSearch}
                onChange={(event) => setTitleSearch(event.target.value)}
                placeholder="analyst"
              />
            </label>
            <label>
              Sort
              <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
                <option value="first_seen">Newest discovered</option>
                <option value="date_collected">Most recently collected</option>
                <option value="target_relevance">Target relevance high to low</option>
                <option value="fit_score">Fit score high to low</option>
                <option value="entry_fit">Entry fit high to low</option>
              </select>
            </label>
            <label className={showAdvancedFilters ? "advanced-filter visible" : "advanced-filter"}>
              Match level
              <select value={matchLevel} onChange={(event) => setMatchLevel(event.target.value)}>
                <option value="">Any</option>
                <option value="Strong Match">Strong Match</option>
                <option value="Good Match">Good Match</option>
                <option value="Stretch Match">Stretch Match</option>
                <option value="Low Match">Low Match</option>
              </select>
            </label>
            <label className={showAdvancedFilters ? "advanced-filter visible" : "advanced-filter"}>
              Min fit score
              <input
                min="0"
                max="100"
                type="number"
                value={minFitScore}
                onChange={(event) => setMinFitScore(event.target.value)}
                placeholder="65"
              />
            </label>
            <label>
              Posted within
              <select
                value={maxPostingAgeDays}
                onChange={(event) => setMaxPostingAgeDays(event.target.value)}
              >
                <option value="30">30 days</option>
                <option value="90">90 days</option>
                <option value="180">180 days</option>
                <option value="365">365 days</option>
                <option value="">All active postings</option>
              </select>
            </label>
            <label className={showAdvancedFilters ? "advanced-filter visible" : "advanced-filter"}>
              Freshness
              <select value={freshness} onChange={(event) => setFreshness(event.target.value)}>
                <option value="">Any</option>
                <option value="Fresh">Fresh</option>
                <option value="Recent">Recent</option>
                <option value="Aging">Aging</option>
                <option value="Stale">Stale / Evergreen</option>
                <option value="Unknown">Unknown</option>
              </select>
            </label>
            <label className={`checkbox-label advanced-filter ${showAdvancedFilters ? "visible" : ""}`}>
              <input
                checked={usOnly}
                type="checkbox"
                onChange={(event) => setUsOnly(event.target.checked)}
              />
              US only
            </label>
            <label className="checkbox-label">
              <input
                checked={targetRelevantOnly}
                type="checkbox"
                onChange={(event) => setTargetRelevantOnly(event.target.checked)}
              />
              Target relevant only
            </label>
            <label className="checkbox-label">
              <input
                checked={careerEligibleOnly}
                type="checkbox"
                onChange={(event) => setCareerEligibleOnly(event.target.checked)}
              />
              0-2 years required
            </label>
            <label className={`checkbox-label advanced-filter ${showAdvancedFilters ? "visible" : ""}`}>
              <input
                checked={activeOnly}
                type="checkbox"
                onChange={(event) => setActiveOnly(event.target.checked)}
              />
              Active only
            </label>
            <label className={`checkbox-label advanced-filter ${showAdvancedFilters ? "visible" : ""}`}>
              <input
                checked={hasFitScore}
                type="checkbox"
                onChange={(event) => setHasFitScore(event.target.checked)}
              />
              Has fit score
            </label>
            <button
              className="secondary-button more-filters-button"
              type="button"
              aria-expanded={showAdvancedFilters}
              onClick={() => setShowAdvancedFilters((current) => !current)}
            >
              <SlidersHorizontal aria-hidden="true" />
              {showAdvancedFilters ? "Fewer Filters" : "More Filters"}
            </button>
            <button
              className="primary-button apply-filters-button"
              type="button"
              onClick={() => {
                loadJobs();
                loadMarketSummary();
                loadSkillGaps();
              }}
              disabled={loadingJobs || loadingSummary}
            >
              Apply
            </button>
          </div>

          <div className="job-browser">
            <aside className="job-list-pane">
              <div className="job-list-toolbar">
                <strong>
                  {loadingJobs
                    ? "Loading jobs"
                    : `${jobPagination.total.toLocaleString()} jobs`}
                </strong>
                <span>{formatLabel(sortBy.replaceAll("_", " "))}</span>
              </div>
              <div className="job-card-list">
                {jobs.map((job) => {
                  const isTracked = trackedJobIds.has(job.id);
                  const isSavingQuickTrack = savingQuickTrackJobId === job.id;
                  const isSavingState = savingJobStateId === job.id;
                  const isNew = isNewSince(job, newJobsSince);

                  return (
                    <article
                      className={`job-card ${selectedJob?.id === job.id ? "selected" : ""} ${job.is_viewed ? "viewed" : "unseen"}`}
                      key={`${job.source}-${job.external_job_id}`}
                      role="button"
                      tabIndex={0}
                      onClick={() => loadJobDetail(job.id)}
                      onKeyDown={(event) => {
                        if (event.target !== event.currentTarget) {
                          return;
                        }

                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          loadJobDetail(job.id);
                        }
                      }}
                    >
                      <div className="job-card-main">
                        <div className="company-avatar">
                          {(job.company || "?").slice(0, 1).toUpperCase()}
                        </div>
                        <div>
                          <div className="job-card-heading-meta">
                            <p>{job.company || "Unknown company"}</p>
                            {!job.is_viewed && <span className="discovery-badge unseen">Unseen</span>}
                            {isNew && <span className="discovery-badge new">New</span>}
                          </div>
                          <h3>{job.title}</h3>
                        </div>
                      </div>
                      <div className="job-card-tags">
                        <span>{formatLabel(job.work_mode)}</span>
                        <span>
                          {job.required_experience_years == null
                            ? "Experience not specified"
                            : `${job.required_experience_years} yrs required`}
                        </span>
                        <span>{job.state || job.country || "Location unknown"}</span>
                      </div>
                      <div className="job-recommendation-row">
                        <span className={`recommendation-badge ${job.application_recommendation}`}>
                          {job.application_recommendation_label || "Tailor First"}
                        </span>
                        <p>{job.application_recommendation_reason}</p>
                      </div>
                      <div className="job-card-scores">
                        <div>
                          <span>Fit</span>
                          <strong>{formatFitScore(job)}</strong>
                        </div>
                        <div>
                          <span>Target</span>
                          <strong>{job.target_relevance_score ?? 0}</strong>
                        </div>
                        <div>
                          <span>Entry</span>
                          <strong>{job.entry_fit_score ?? 0}</strong>
                        </div>
                      </div>
                      <div className="job-card-footer">
                        <div>
                          <span>{formatDate(job.date_posted)}</span>
                          <span>{job.freshness_bucket}</span>
                          <span className={`lifecycle-status ${job.is_active ? "active" : "closed"}`}>
                            {job.is_active ? "Active" : "Closed"}
                          </span>
                          {job.is_user_added && <span>{formatLabel(job.source)}</span>}
                        </div>
                        <div className="job-card-actions">
                          <button
                            className="job-state-button"
                            type="button"
                            title={job.is_hidden ? "Restore job" : "Hide job"}
                            aria-label={job.is_hidden ? "Restore job" : "Hide job"}
                            disabled={isSavingState}
                            onClick={(event) => toggleJobHidden(job, event)}
                          >
                            {job.is_hidden
                              ? <Eye aria-hidden="true" />
                              : <EyeOff aria-hidden="true" />}
                          </button>
                          <button
                            className="save-job-button"
                            type="button"
                            disabled={isTracked || isSavingQuickTrack}
                            onClick={(event) => {
                              event.stopPropagation();
                              saveJobToTracker(job);
                            }}
                          >
                            {isSavingQuickTrack ? "Saving" : isTracked ? "Saved" : "Save"}
                          </button>
                        </div>
                      </div>
                    </article>
                  );
                })}
                {!jobs.length && (
                  <div className="empty-card">
                    No jobs match the current filters.
                  </div>
                )}
              </div>
              <div className="job-pagination" aria-label="Job list pagination">
                <button
                  className="icon-button"
                  type="button"
                  title="Previous page"
                  aria-label="Previous page"
                  disabled={loadingJobs || jobPagination.page <= 1}
                  onClick={() => loadJobs(jobPagination.page - 1)}
                >
                  <ChevronLeft aria-hidden="true" />
                </button>
                <span>
                  Page {jobPagination.page} of {Math.max(jobPagination.total_pages, 1)}
                </span>
                <select
                  aria-label="Jobs per page"
                  value={jobPagination.page_size}
                  disabled={loadingJobs}
                  onChange={(event) => loadJobs(1, Number(event.target.value))}
                >
                  <option value="25">25 / page</option>
                  <option value="50">50 / page</option>
                  <option value="100">100 / page</option>
                </select>
                <button
                  className="icon-button"
                  type="button"
                  title="Next page"
                  aria-label="Next page"
                  disabled={
                    loadingJobs
                    || jobPagination.total_pages === 0
                    || jobPagination.page >= jobPagination.total_pages
                  }
                  onClick={() => loadJobs(jobPagination.page + 1)}
                >
                  <ChevronRight aria-hidden="true" />
                </button>
              </div>
            </aside>

            <section className="job-detail-pane">
              {!selectedJob && (
                <div className="detail-placeholder">
                  <h3>Select a job</h3>
                  <p>Open a card on the left to review fit score, entry-level risk, skills, description, and tracking notes.</p>
                </div>
              )}

              {selectedJob && (
                <div className="job-detail">
                  <div className="job-detail-header">
                    <div>
                      <p>{selectedJob.company || "Unknown company"}</p>
                      <h3>{selectedJob.title}</h3>
                    </div>
                    <div className="detail-actions">
                      <button
                        className="icon-button"
                        type="button"
                        title={selectedJob.is_hidden ? "Restore job" : "Hide job"}
                        aria-label={selectedJob.is_hidden ? "Restore job" : "Hide job"}
                        disabled={savingJobStateId === selectedJob.id}
                        onClick={(event) => toggleJobHidden(selectedJob, event)}
                      >
                        {selectedJob.is_hidden
                          ? <Eye aria-hidden="true" />
                          : <EyeOff aria-hidden="true" />}
                      </button>
                      {selectedJob.job_url && (
                        <a className="primary-link-button" href={selectedJob.job_url} target="_blank" rel="noreferrer">
                          Open
                        </a>
                      )}
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => setSelectedJob(null)}
                      >
                        Close
                      </button>
                      {selectedJob.is_user_added && (
                        <button
                          className="danger-button"
                          type="button"
                          disabled={deletingManualJob}
                          onClick={deleteManualJob}
                        >
                          {deletingManualJob ? "Deleting" : "Delete"}
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="detail-meta">
                    {selectedJob.is_user_added && <span>{formatLabel(selectedJob.source)}</span>}
                    <span className={`lifecycle-status ${selectedJob.is_active ? "active" : "closed"}`}>
                      {selectedJob.is_active ? "Active" : "Closed"}
                    </span>
                    <span>Last seen {formatDate(selectedJob.last_seen_at)}</span>
                    {!selectedJob.is_active && selectedJob.closed_at && (
                      <span>Closed {formatDate(selectedJob.closed_at)}</span>
                    )}
                    <span>{selectedJob.normalized_location || selectedJob.location || "Location unknown"}</span>
                    <span>{selectedJob.freshness_bucket}</span>
                    <span>{formatLabel(selectedJob.work_mode)}</span>
                    <span>{formatLabel(selectedJob.seniority)}</span>
                    <span>
                      {selectedJob.required_experience_years == null
                        ? "Experience not specified"
                        : `${selectedJob.required_experience_years} years required`}
                    </span>
                    <span>{formatLabel(selectedJob.role_category)}</span>
                  </div>

                  <section className={`application-recommendation ${selectedJob.application_recommendation}`}>
                    <span>Recommended action</span>
                    <strong>{selectedJob.application_recommendation_label || "Tailor First"}</strong>
                    <p>{selectedJob.application_recommendation_reason}</p>
                  </section>

                  <div className="detail-score-grid">
                    <div className="detail-score-card">
                      <span>Fit Score</span>
                      <strong>{formatFitScore(selectedJob)}</strong>
                      <p>{selectedJob.match_level || "No profile"}</p>
                    </div>
                    <div className="detail-score-card">
                      <span>Entry Fit</span>
                      <strong>{selectedJob.entry_fit_score ?? 0}</strong>
                      <p>{formatLabel(selectedJob.entry_fit_level)}</p>
                    </div>
                    <div className="detail-score-card">
                      <span>Target</span>
                      <strong>{selectedJob.target_relevance_score ?? 0}</strong>
                      <p>{formatPostingAge(selectedJob)}</p>
                    </div>
                  </div>

                  {selectedJob.entry_fit_reasons && (
                    <p className="entry-fit-reason">{selectedJob.entry_fit_reasons}</p>
                  )}
                  {!selectedJob.career_eligible && (
                    <p className="entry-fit-reason">
                      Excluded: {selectedJob.career_eligibility_reason}
                    </p>
                  )}

                  <div className="fit-panel">
                    {selectedJob.fit_breakdown.length > 0 && (
                      <div className="fit-breakdown">
                        <h4>Score Breakdown</h4>
                        {selectedJob.fit_breakdown.map((dimension) => (
                          <div className="fit-breakdown-row" key={dimension.key}>
                            <div className="fit-breakdown-heading">
                              <span>{dimension.label}</span>
                              <strong>
                                {dimension.score}/{dimension.max_score}
                              </strong>
                            </div>
                            <div className="bar-track">
                              <div
                                className="bar-fill"
                                style={{
                                  width: `${dimension.max_score ? Math.round((dimension.score / dimension.max_score) * 100) : 0}%`,
                                }}
                              />
                            </div>
                            <p>{dimension.explanation}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="fit-skill-grid">
                      <div>
                        <h4>Required matched</h4>
                        <div className="skill-chips">
                          {selectedJob.matched_required_skills.map((skill) => (
                            <span key={`required-matched-${skill}`}>{skill}</span>
                          ))}
                          {!selectedJob.matched_required_skills.length && <span>None</span>}
                        </div>
                      </div>
                      <div>
                        <h4>Required missing</h4>
                        <div className="skill-chips missing-skills">
                          {selectedJob.missing_required_skills.map((skill) => (
                            <span key={`required-missing-${skill}`}>{skill}</span>
                          ))}
                          {!selectedJob.missing_required_skills.length && <span>None</span>}
                        </div>
                      </div>
                      <div>
                        <h4>Preferred matched</h4>
                        <div className="skill-chips preferred-skills">
                          {selectedJob.matched_preferred_skills.map((skill) => (
                            <span key={`preferred-matched-${skill}`}>{skill}</span>
                          ))}
                          {!selectedJob.matched_preferred_skills.length && <span>None</span>}
                        </div>
                      </div>
                      <div>
                        <h4>Preferred missing</h4>
                        <div className="skill-chips missing-skills">
                          {selectedJob.missing_preferred_skills.map((skill) => (
                            <span key={`preferred-missing-${skill}`}>{skill}</span>
                          ))}
                          {!selectedJob.missing_preferred_skills.length && <span>None</span>}
                        </div>
                      </div>
                    </div>

                    {!selectedJob.fit_breakdown.length && selectedJob.fit_notes.length > 0 && (
                      <ul className="fit-notes">
                        {selectedJob.fit_notes.map((note) => (
                          <li key={note}>{note}</li>
                        ))}
                      </ul>
                    )}
                  </div>

                  <section className="suggestion-panel">
                    <div className="suggestion-header">
                      <div>
                        <h4>Resume Suggestions</h4>
                        <p>Position-specific suggestions using profile evidence and the selected resume version.</p>
                      </div>
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={loadResumeSuggestions}
                        disabled={loadingResumeSuggestions}
                      >
                        {loadingResumeSuggestions ? "Generating" : "Generate"}
                      </button>
                    </div>
                    <label>
                      Resume version
                      <select
                        value={suggestionResumeVersionId}
                        onChange={(event) => setSuggestionResumeVersionId(event.target.value)}
                      >
                        <option value="">Use profile only</option>
                        {resumeVersions.map((version) => (
                          <option value={version.id} key={version.id}>
                            {version.name}
                          </option>
                        ))}
                      </select>
                    </label>

                    {resumeSuggestions && (
                      <div className="suggestion-list">
                        {resumeSuggestions.suggestions.map((suggestion) => (
                          <article
                            className={`suggestion-card ${suggestion.risk_level}`}
                            key={`${suggestion.suggestion_type}-${suggestion.title}`}
                          >
                            <div className="suggestion-card-header">
                              <h5>{suggestion.title}</h5>
                              <span>{suggestion.risk_level}</span>
                            </div>
                            <p>{suggestion.suggestion}</p>
                            {suggestion.related_keyword && (
                              <strong>{suggestion.related_keyword}</strong>
                            )}
                            {suggestion.evidence.length > 0 && (
                              <ul>
                                {suggestion.evidence.slice(0, 3).map((evidence) => (
                                  <li key={evidence}>{evidence}</li>
                                ))}
                              </ul>
                            )}
                          </article>
                        ))}
                      </div>
                    )}
                  </section>

                  <section className="suggestion-panel">
                    <div className="suggestion-header">
                      <div>
                        <h4>Cover Letter Draft</h4>
                        <p>Position-specific draft generated from profile evidence. No external LLM API is used.</p>
                      </div>
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={loadCoverLetterDraft}
                        disabled={loadingCoverLetter}
                      >
                        {loadingCoverLetter ? "Generating" : "Generate"}
                      </button>
                    </div>
                    <label>
                      Resume version
                      <select
                        value={coverLetterResumeVersionId}
                        onChange={(event) => setCoverLetterResumeVersionId(event.target.value)}
                      >
                        <option value="">Use profile only</option>
                        {resumeVersions.map((version) => (
                          <option value={version.id} key={version.id}>
                            {version.name}
                          </option>
                        ))}
                      </select>
                    </label>

                    {coverLetterDraft && (
                      <div className="cover-letter-output">
                        <label>
                          Version name
                          <input
                            value={coverLetterName}
                            onChange={(event) => setCoverLetterName(event.target.value)}
                            placeholder="Nubank Compliance Analyst Cover Letter"
                          />
                        </label>
                        <div className="cover-letter-actions">
                          <span>
                            {coverLetterDraft.company || "Company"} / {coverLetterDraft.job_title}
                          </span>
                          <div className="cover-letter-action-buttons">
                            <button
                              className="table-button"
                              type="button"
                              onClick={() => navigator.clipboard.writeText(coverLetterDraft.draft)}
                            >
                              Copy
                            </button>
                            <button
                              className="primary-button"
                              type="button"
                              onClick={saveCoverLetter}
                              disabled={
                                savingCoverLetter ||
                                !coverLetterName.trim() ||
                                !coverLetterDraft.draft.trim()
                              }
                            >
                              {savingCoverLetter
                                ? "Saving"
                                : editingCoverLetterId
                                  ? "Update Saved Letter"
                                  : "Save to Documents"}
                            </button>
                          </div>
                        </div>
                        <textarea
                          className="cover-letter-draft"
                          value={coverLetterDraft.draft}
                          onChange={(event) =>
                            setCoverLetterDraft((current) => ({
                              ...current,
                              draft: event.target.value,
                            }))
                          }
                        />
                        {coverLetterDraft.evidence.length > 0 && (
                          <div className="cover-letter-notes">
                            <strong>Evidence used</strong>
                            <ul>
                              {coverLetterDraft.evidence.map((item) => (
                                <li key={item}>{item}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {coverLetterDraft.caveats.length > 0 && (
                          <div className="cover-letter-notes warning">
                            <strong>Review before using</strong>
                            <ul>
                              {coverLetterDraft.caveats.map((item) => (
                                <li key={item}>{item}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </section>

                  <div className="skill-chips">
                    {selectedJob.skills.map((skill) => (
                      <span
                        className={`skill-level-${skill.requirement_level}`}
                        key={`${skill.category}-${skill.skill}`}
                        title={skill.evidence_snippet || "No JD evidence saved"}
                      >
                        {formatLabel(skill.requirement_level)}: {skill.skill}
                      </span>
                    ))}
                    {!selectedJob.skills.length && <span>No extracted skills yet</span>}
                  </div>

                  <p className="description-preview">
                    {cleanDescription(selectedJob.description)}
                  </p>

                  <form className="tracker-form" onSubmit={saveApplicationTracking}>
                    <h4>Manual Application Tracker</h4>
                    <div className="tracker-grid">
                      <label>
                        Status
                        <select
                          value={applicationForm.status}
                          onChange={(event) =>
                            setApplicationForm((current) => ({
                              ...current,
                              status: event.target.value,
                            }))
                          }
                        >
                          {APPLICATION_STATUS_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Applied date
                        <input
                          type="date"
                          value={applicationForm.applied_date}
                          onChange={(event) =>
                            setApplicationForm((current) => ({
                              ...current,
                              applied_date: event.target.value,
                            }))
                          }
                        />
                      </label>
                      <label>
                        Follow-up date
                        <input
                          type="date"
                          value={applicationForm.follow_up_date}
                          onChange={(event) =>
                            setApplicationForm((current) => ({
                              ...current,
                              follow_up_date: event.target.value,
                            }))
                          }
                        />
                      </label>
                    </div>
                    <div className="tracker-grid">
                      <label>
                        Resume version
                        <select
                          value={applicationForm.resume_version_id}
                          onChange={(event) =>
                            setApplicationForm((current) => ({
                              ...current,
                              resume_version_id: event.target.value,
                            }))
                          }
                        >
                          <option value="">Not selected</option>
                          {resumeVersions.map((version) => (
                            <option value={version.id} key={version.id}>
                              {version.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Cover letter version
                        <select
                          value={applicationForm.cover_letter_id}
                          onChange={(event) =>
                            setApplicationForm((current) => ({
                              ...current,
                              cover_letter_id: event.target.value,
                            }))
                          }
                        >
                          <option value="">Not selected</option>
                          {coverLetters
                            .filter((letter) => letter.raw_job_id === selectedJob.id)
                            .map((letter) => (
                              <option value={letter.id} key={letter.id}>
                                {letter.name}
                              </option>
                            ))}
                        </select>
                      </label>
                    </div>
                    <label>
                      Notes
                      <textarea
                        value={applicationForm.notes}
                        onChange={(event) =>
                          setApplicationForm((current) => ({
                            ...current,
                            notes: event.target.value,
                          }))
                        }
                        placeholder="Record where you applied, resume version, referral notes, or next step."
                      />
                    </label>
                    <button className="primary-button" type="submit" disabled={savingApplication}>
                      {savingApplication ? "Saving" : "Save Tracking Info"}
                    </button>
                  </form>
                </div>
              )}
            </section>
          </div>
        </section>
      </section>
      )}

      {activeView === "tracker" && (
      <section className="panel applications-panel">
        <div className="panel-header">
          <h2>Tracked Applications</h2>
          <span>
            {loadingApplications
              ? "Loading"
              : `${filteredApplications.length} of ${trackedApplications.length} tracked`}
          </span>
        </div>

        <div className="tracker-toolbar">
          <label>
            Status
            <select
              value={trackerStatusFilter}
              onChange={(event) => setTrackerStatusFilter(event.target.value)}
            >
              <option value="">All statuses</option>
              {APPLICATION_STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Company</th>
                <th>Title</th>
                <th>Status</th>
                <th>Location</th>
                <th>Resume</th>
                <th>Cover Letter</th>
                <th>Applied</th>
                <th>Follow-up</th>
                <th>Notes</th>
                <th>Link</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredApplications.map((application) => (
                <tr key={application.id}>
                  <td>{application.company || "Unknown company"}</td>
                  <td>{application.title || "Unknown role"}</td>
                  <td>
                    <span className="status-pill">{formatLabel(application.status)}</span>
                  </td>
                  <td>{application.location || "Location unknown"}</td>
                  <td>{application.resume_version || "Not set"}</td>
                  <td>{application.cover_letter_version || "Not set"}</td>
                  <td>{formatDate(application.applied_date)}</td>
                  <td>{formatDate(application.follow_up_date)}</td>
                  <td>{application.notes || "-"}</td>
                  <td>
                    {application.job_url ? (
                      <a href={application.job_url} target="_blank" rel="noreferrer">
                        Open
                      </a>
                    ) : (
                      "-"
                    )}
                  </td>
                  <td>
                    <button
                      className="table-button"
                      type="button"
                      onClick={() => {
                        setActiveView("jobs");
                        loadJobDetail(application.raw_job_id);
                      }}
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
              {!filteredApplications.length && (
                <tr>
                  <td colSpan="11">No tracked applications for this status.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
      )}
    </main>
  );
}

export default App;
