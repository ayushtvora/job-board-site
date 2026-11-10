"use client";

import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import FilterSelect from "./FilterSelect";
import styles from "./page.module.css";

type Job = {
  id: number;
  company: string;
  title: string;
  externalId: string;
  location: string;
  cities: string[];
  url: string;
  platform: string;
  field: string;
  postedDate: string;
  applied: boolean;
  willApply: boolean;
  score: number | null;
  scoreReason: string | null;
  scoreBasis: "description" | "title" | null;
};

type JobDetail = Job & {
  description: string | null;
  matchedSkills: string[];
  missingSkills: string[];
};

type ScoringStatus = {
  scored: number;
  total: number;
  lastError: string | null;
  lastErrorAt: string | null;
};

// Column the table is sorted by, chosen by clicking a header. "default" is
// the API's order (effective posted date, then company, then title).
type SortKey = "default" | "score" | "posted";
type Sort = { key: SortKey; descending: boolean };

type ScrapeStatus = {
  company: string;
  status: "success" | "error";
  errorMessage: string | null;
  finishedAt: string | null;
};

type ScrapeRequest = {
  id: number;
  status: "pending" | "running" | "done" | "error";
  errorMessage: string | null;
  requestedAt: string;
  finishedAt: string | null;
};

type Company = {
  slug: string;
  name: string;
  sectors: string[];
};

const SCAN_POLL_INTERVAL_MS = 3000;
// A posting can list many cities (Deloitte's go up to 20); the rest are
// collapsed into "+N more", with the full list on hover.
const MAX_CITIES_SHOWN = 3;
const PAGE_SIZE = 50;
const SCORING_POLL_INTERVAL_MS = 60_000;

// Values are days, sent as the API's postedWithin param; "" means any date.
const POSTED_WITHIN_OPTIONS = [
  { value: "", label: "Any time" },
  { value: "1", label: "Past 24 hours" },
  { value: "7", label: "Past week" },
  { value: "30", label: "Past month" },
];

// Sent as the API's field param; "" means both.
const FIELD_OPTIONS = [
  { value: "", label: "All fields" },
  { value: "Software", label: "Software" },
  { value: "Data", label: "Data" },
];

export default function Home() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [showHidden, setShowHidden] = useState(false);
  const [postedWithin, setPostedWithin] = useState("");
  const [field, setField] = useState("");
  const [sector, setSector] = useState("");
  const [company, setCompany] = useState("");
  const [city, setCity] = useState("");
  const [cities, setCities] = useState<string[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [savingIds, setSavingIds] = useState<Set<number>>(new Set());
  const [scrapeStatuses, setScrapeStatuses] = useState<ScrapeStatus[]>([]);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [scanRequest, setScanRequest] = useState<ScrapeRequest | null>(null);
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState<Sort>({ key: "default", descending: true });
  const [openJobId, setOpenJobId] = useState<number | null>(null);
  const [openJob, setOpenJob] = useState<JobDetail | null>(null);
  const [scoringStatus, setScoringStatus] = useState<ScoringStatus | null>(null);
  const scanInFlight = scanRequest?.status === "pending" || scanRequest?.status === "running";

  const loadJobs = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (showHidden) params.set("showHidden", "true");
    if (postedWithin) params.set("postedWithin", postedWithin);
    if (field) params.set("field", field);
    if (sector) params.set("sector", sector);
    if (company) params.set("company", company);
    if (city) params.set("city", city);
    const query = params.toString();
    const res = await fetch(`/api/jobs${query ? `?${query}` : ""}`);
    const data: Job[] = await res.json();
    setJobs(data);
    setLoading(false);
  }, [showHidden, postedWithin, field, sector, company, city]);

  const loadScrapeStatus = useCallback(async () => {
    const res = await fetch("/api/scrape-status");
    const data: ScrapeStatus[] = await res.json();
    setScrapeStatuses(data);
  }, []);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    loadScrapeStatus();
  }, [loadScrapeStatus]);

  // Scores arrive in the background, so the progress line refreshes on an
  // interval, and the table too whenever more jobs have been scored.
  const lastScored = useRef<number | null>(null);
  useEffect(() => {
    const poll = () =>
      fetch("/api/scoring-status")
        .then((res) => res.json())
        .then((data: ScoringStatus) => {
          if (lastScored.current !== null && lastScored.current !== data.scored) loadJobs();
          lastScored.current = data.scored;
          setScoringStatus(data);
        });
    poll();
    const interval = setInterval(poll, SCORING_POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [loadJobs]);

  useEffect(() => {
    fetch("/api/companies")
      .then((res) => res.json())
      .then((data: Company[]) => setCompanies(data));
    fetch("/api/cities")
      .then((res) => res.json())
      .then((data: string[]) => setCities(data));
  }, []);

  // Pick up an already in-flight scan on page load, so refreshing the page
  // mid-scan still shows "Scanning…" instead of losing track of it.
  useEffect(() => {
    fetch("/api/scrape-requests")
      .then((res) => res.json())
      .then((data: ScrapeRequest | null) => {
        if (data && (data.status === "pending" || data.status === "running")) {
          setScanRequest(data);
        }
      });
  }, []);

  useEffect(() => {
    if (!scanInFlight) return;

    const interval = setInterval(async () => {
      const res = await fetch("/api/scrape-requests");
      const data: ScrapeRequest | null = await res.json();
      setScanRequest(data);
      if (data && data.status !== "pending" && data.status !== "running") {
        await Promise.all([loadJobs(), loadScrapeStatus()]);
      }
    }, SCAN_POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [scanInFlight, loadJobs, loadScrapeStatus]);

  const scrapeErrors = scrapeStatuses.filter((run) => run.status === "error");

  const sectors = [...new Set(companies.flatMap((c) => c.sectors))].sort();
  // Picking a sector narrows the Company dropdown to that sector's companies.
  const companyOptions = sector ? companies.filter((c) => c.sectors.includes(sector)) : companies;

  // Re-fetching after a checkbox edit can shrink the list, so the page is
  // clamped rather than trusted.
  const sortedJobs = sortJobs(jobs, sort);
  const pageCount = Math.max(1, Math.ceil(sortedJobs.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount - 1);
  const pageJobs = sortedJobs.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE);

  // Clicking a sortable header sorts by it, highest/newest first; clicking
  // it again flips the direction. Back to page 1 either way.
  function sortBy(key: SortKey) {
    setSort((prev) => (prev.key === key ? { key, descending: !prev.descending } : { key, descending: true }));
    setPage(0);
  }

  async function toggleDetails(id: number) {
    if (openJobId === id) {
      setOpenJobId(null);
      return;
    }
    setOpenJobId(id);
    setOpenJob(null);
    const res = await fetch(`/api/jobs/${id}`);
    if (res.ok) {
      const data: JobDetail = await res.json();
      setOpenJob(data);
    }
  }

  // A click anywhere on a row opens its details, except on the link and
  // checkboxes, which keep doing their own thing.
  function onRowClick(event: React.MouseEvent, id: number) {
    if ((event.target as HTMLElement).closest("a, input, button, label")) return;
    toggleDetails(id);
  }

  // Wraps a filter's setter so changing the filter goes back to page 1.
  function resettingPage<T>(set: (value: T) => void) {
    return (value: T) => {
      set(value);
      setPage(0);
    };
  }

  function changeSector(next: string) {
    setSector(next);
    setPage(0);
    // Drop a selected company that isn't in the new sector, rather than
    // leaving a hidden filter that makes the table silently empty.
    if (next && company && !companies.find((c) => c.slug === company)?.sectors.includes(next)) {
      setCompany("");
    }
  }

  // The most recent finishedAt across all companies' last scrape_runs row —
  // reflects the last time any scan completed, whether kicked off by the
  // button or the scraper's own daily 6am schedule.
  const lastRunAt = scrapeStatuses.reduce<string | null>((latest, run) => {
    if (!run.finishedAt) return latest;
    if (!latest || run.finishedAt > latest) return run.finishedAt;
    return latest;
  }, null);

  async function startScan() {
    const res = await fetch("/api/scrape-requests", { method: "POST" });
    const data: ScrapeRequest = await res.json();
    setScanRequest(data);
  }

  async function updateJob(id: number, patch: Partial<Pick<Job, "applied" | "willApply">>) {
    setSavingIds((prev) => new Set(prev).add(id));
    // Apply the checkbox change immediately so it's visible before the
    // round-trip completes — otherwise a row leaving the current filter
    // (e.g. checking "Applied") just vanishes with no visual feedback.
    setJobs((prev) => prev.map((job) => (job.id === id ? { ...job, ...patch } : job)));
    try {
      await fetch(`/api/jobs/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      // Re-fetch after that: whether a row still belongs in the current view
      // depends on the server's filter logic, so the server is the source
      // of truth for what the list looks like next.
      await loadJobs();
    } finally {
      setSavingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }

  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <h1>Job Board</h1>

        {scrapeErrors.length > 0 && !bannerDismissed && (
          <div className={styles.banner}>
            <span>
              Scrape failed for: {scrapeErrors.map((run) => run.company).join(", ")}
            </span>
            <button
              type="button"
              className={styles.bannerDismiss}
              onClick={() => setBannerDismissed(true)}
            >
              Dismiss
            </button>
          </div>
        )}

        <div className={styles.scanRow}>
          <button
            type="button"
            className={styles.scanButton}
            onClick={startScan}
            disabled={scanInFlight}
          >
            {scanInFlight ? "Scanning…" : "Run Job Scan"}
          </button>
          <span className={styles.lastRun}>
            Last run: {lastRunAt ? new Date(lastRunAt).toLocaleString() : "never"}
          </span>
          {scanRequest?.status === "error" && (
            <span className={styles.scanError}>
              Last scan failed{scanRequest.errorMessage ? `: ${scanRequest.errorMessage}` : ""}
            </span>
          )}
        </div>

        {scoringStatus && scoringStatus.total > 0 && (
          <div className={styles.scoringStatus}>
            <span>
              Scored {scoringStatus.scored.toLocaleString()} of {scoringStatus.total.toLocaleString()} jobs
            </span>
            {scoringStatus.lastError && (
              <span className={styles.scanError} title={scoringStatus.lastError}>
                Scoring error
                {scoringStatus.lastErrorAt ? ` (${new Date(scoringStatus.lastErrorAt).toLocaleString()})` : ""}:{" "}
                {scoringStatus.lastError.slice(0, 160)}
              </span>
            )}
          </div>
        )}

        <div className={styles.filters}>
          <FilterSelect label="Field" value={field} options={FIELD_OPTIONS} onChange={resettingPage(setField)} />
          <FilterSelect
            label="Posted"
            value={postedWithin}
            options={POSTED_WITHIN_OPTIONS}
            onChange={resettingPage(setPostedWithin)}
          />
          <FilterSelect
            label="Sector"
            value={sector}
            options={[
              { value: "", label: "All sectors" },
              ...sectors.map((s) => ({ value: s, label: s })),
            ]}
            onChange={changeSector}
            searchable
          />
          <FilterSelect
            label="Company"
            value={company}
            options={[
              { value: "", label: "All companies" },
              ...companyOptions.map((c) => ({ value: c.slug, label: c.name })),
            ]}
            onChange={resettingPage(setCompany)}
            searchable
          />
          <FilterSelect
            label="City"
            value={city}
            options={[
              { value: "", label: "All cities" },
              ...cities.map((c) => ({ value: c, label: c })),
            ]}
            onChange={resettingPage(setCity)}
            searchable
          />
          <label className={styles.showHidden}>
            <input
              type="checkbox"
              checked={showHidden}
              onChange={(e) => resettingPage(setShowHidden)(e.target.checked)}
            />
            Show hidden jobs (expired or applied)
          </label>
        </div>

        {loading ? (
          <p>Loading…</p>
        ) : jobs.length === 0 ? (
          <p>No jobs to show.</p>
        ) : (
          <>
            {renderPager(sortedJobs.length, currentPage, pageCount, setPage)}
            <table className={styles.table}>
              <thead>
                <tr>
                  {renderSortHeader("Score", "score", sort, sortBy)}
                  <th>Company</th>
                  <th>Job Title</th>
                  <th>Location</th>
                  <th>Job ID</th>
                  <th>Link</th>
                  {renderSortHeader("Posted Date", "posted", sort, sortBy)}
                  <th>Applied</th>
                  <th>Will Apply</th>
                </tr>
              </thead>
              <tbody>
                {pageJobs.map((job) => (
                  <Fragment key={job.id}>
                  <tr
                    className={`${styles.jobRow} ${openJobId === job.id ? styles.openRow : ""}`}
                    onClick={(e) => onRowClick(e, job.id)}
                  >
                    <td className={styles.scoreCell}>{renderScore(job)}</td>
                    <td className={styles.company}>{job.company}</td>
                    <td>
                      <span className={styles.clamp} title={job.title}>
                        {job.title}
                      </span>
                    </td>
                    <td className={styles.location}>{renderLocation(job)}</td>
                    <td className={styles.jobId}>{job.externalId}</td>
                    <td className={styles.nowrap}>
                      <a
                        href={job.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.link}
                      >
                        {job.platform}
                      </a>
                    </td>
                    <td className={styles.nowrap}>{job.postedDate}</td>
                    <td className={styles.checkbox}>
                      <input
                        type="checkbox"
                        checked={job.applied}
                        disabled={savingIds.has(job.id)}
                        onChange={(e) => updateJob(job.id, { applied: e.target.checked })}
                      />
                    </td>
                    <td className={styles.checkbox}>
                      <input
                        type="checkbox"
                        checked={job.willApply}
                        disabled={savingIds.has(job.id)}
                        onChange={(e) => updateJob(job.id, { willApply: e.target.checked })}
                      />
                    </td>
                  </tr>
                  {openJobId === job.id && (
                    <tr className={styles.detailRow}>
                      <td colSpan={COLUMN_COUNT}>{renderDetails(job, openJob?.id === job.id ? openJob : null)}</td>
                    </tr>
                  )}
                  </Fragment>
                ))}
              </tbody>
            </table>
            {renderPager(sortedJobs.length, currentPage, pageCount, (next) => {
              setPage(next);
              window.scrollTo({ top: 0 });
            })}
          </>
        )}
      </main>
    </div>
  );
}

const COLUMN_COUNT = 9;

// Unscored jobs always sort last, in either direction. Ties keep the
// API's order (Array.prototype.sort is stable).
function sortJobs(jobs: Job[], sort: Sort): Job[] {
  if (sort.key === "default") return sort.descending ? jobs : [...jobs].reverse();
  const sign = sort.descending ? -1 : 1;
  return [...jobs].sort((a, b) => {
    if (sort.key === "score") {
      if (a.score === null || b.score === null) return (a.score === null ? 1 : 0) - (b.score === null ? 1 : 0);
      return sign * (a.score - b.score);
    }
    return sign * a.postedDate.localeCompare(b.postedDate);
  });
}

function renderSortHeader(label: string, key: SortKey, sort: Sort, sortBy: (key: SortKey) => void) {
  const active = sort.key === key;
  return (
    <th aria-sort={active ? (sort.descending ? "descending" : "ascending") : "none"}>
      <button
        type="button"
        className={`${styles.sortHeader} ${active ? styles.sortActive : ""}`}
        onClick={() => sortBy(key)}
      >
        {label}
        <span className={styles.sortArrow}>{active ? (sort.descending ? "\u25BC" : "\u25B2") : "\u2195"}</span>
      </button>
    </th>
  );
}

// 70+ is a good match, 50-69 a stretch, under 50 weak (see the rubric in
// src/lib/scoring/scoreJob.ts). "~" marks a score from the title alone.
function renderScore(job: Job) {
  if (job.score === null) {
    return (
      <span className={styles.unscored} title="Not scored yet">
        {"\u2013"}
      </span>
    );
  }
  const level = job.score >= 70 ? styles.scoreHigh : job.score >= 50 ? styles.scoreMid : styles.scoreLow;
  const titleOnly = job.scoreBasis === "title";
  const hover = (titleOnly ? "Scored from the title only (no description). " : "") + (job.scoreReason ?? "");
  return (
    <span className={`${styles.score} ${level}`} title={hover}>
      {titleOnly && "~"}
      {job.score}
    </span>
  );
}

function renderDetails(job: Job, detail: JobDetail | null) {
  return (
    <div className={styles.details}>
      {job.scoreReason && (
        <p className={styles.detailReason}>
          <strong>{job.scoreBasis === "title" ? "Score (from the title only): " : "Score: "}</strong>
          {job.scoreReason}
        </p>
      )}
      {!detail ? (
        <p className={styles.muted}>Loading{"\u2026"}</p>
      ) : (
        <>
          {(detail.matchedSkills.length > 0 || detail.missingSkills.length > 0) && (
            <div className={styles.skills}>
              {detail.matchedSkills.length > 0 && (
                <div>
                  <span className={styles.skillsLabel}>You have</span>
                  {detail.matchedSkills.map((skill) => (
                    <span key={skill} className={`${styles.skill} ${styles.skillMatched}`}>
                      {skill}
                    </span>
                  ))}
                </div>
              )}
              {detail.missingSkills.length > 0 && (
                <div>
                  <span className={styles.skillsLabel}>Missing</span>
                  {detail.missingSkills.map((skill) => (
                    <span key={skill} className={`${styles.skill} ${styles.skillMissing}`}>
                      {skill}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
          {detail.description ? (
            <div className={styles.description}>{detail.description}</div>
          ) : (
            <p className={styles.muted}>No description available.</p>
          )}
        </>
      )}
    </div>
  );
}

// The job's cities, or its raw location when no city could be picked out
// of it (e.g. just "Canada"). Hovering shows the source site's own text.
function renderLocation(job: Job) {
  if (job.cities.length === 0) {
    return (
      <span className={`${styles.clamp} ${styles.rawLocation}`} title={job.location}>
        {job.location}
      </span>
    );
  }
  const shown = job.cities.slice(0, MAX_CITIES_SHOWN).join(", ");
  const hidden = job.cities.length - MAX_CITIES_SHOWN;
  return (
    <span className={styles.clamp} title={job.location}>
      {shown}
      {hidden > 0 && <span className={styles.moreCities}> +{hidden} more</span>}
    </span>
  );
}

function renderPager(
  total: number,
  currentPage: number,
  pageCount: number,
  goTo: (page: number) => void,
) {
  const first = currentPage * PAGE_SIZE + 1;
  const last = Math.min(total, (currentPage + 1) * PAGE_SIZE);
  return (
    <div className={styles.pager}>
      <span className={styles.pagerCount}>
        Showing {first}–{last} of {total} jobs
      </span>
      {pageCount > 1 && (
        <div className={styles.pagerButtons}>
          <button type="button" disabled={currentPage === 0} onClick={() => goTo(currentPage - 1)}>
            Prev
          </button>
          <span>
            Page {currentPage + 1} of {pageCount}
          </span>
          <button
            type="button"
            disabled={currentPage === pageCount - 1}
            onClick={() => goTo(currentPage + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
