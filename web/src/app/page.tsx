"use client";

import { useCallback, useEffect, useState } from "react";
import FilterSelect from "./FilterSelect";
import styles from "./page.module.css";

type Job = {
  id: number;
  company: string;
  title: string;
  externalId: string;
  url: string;
  platform: string;
  postedDate: string;
  applied: boolean;
  willApply: boolean;
};

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

// Values are days, sent as the API's postedWithin param; "" means any date.
const POSTED_WITHIN_OPTIONS = [
  { value: "", label: "Any time" },
  { value: "1", label: "Past 24 hours" },
  { value: "7", label: "Past week" },
  { value: "30", label: "Past month" },
];

export default function Home() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [showHidden, setShowHidden] = useState(false);
  const [postedWithin, setPostedWithin] = useState("");
  const [sector, setSector] = useState("");
  const [company, setCompany] = useState("");
  const [companies, setCompanies] = useState<Company[]>([]);
  const [savingIds, setSavingIds] = useState<Set<number>>(new Set());
  const [scrapeStatuses, setScrapeStatuses] = useState<ScrapeStatus[]>([]);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [scanRequest, setScanRequest] = useState<ScrapeRequest | null>(null);
  const scanInFlight = scanRequest?.status === "pending" || scanRequest?.status === "running";

  const loadJobs = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (showHidden) params.set("showHidden", "true");
    if (postedWithin) params.set("postedWithin", postedWithin);
    if (sector) params.set("sector", sector);
    if (company) params.set("company", company);
    const query = params.toString();
    const res = await fetch(`/api/jobs${query ? `?${query}` : ""}`);
    const data: Job[] = await res.json();
    setJobs(data);
    setLoading(false);
  }, [showHidden, postedWithin, sector, company]);

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

  useEffect(() => {
    fetch("/api/companies")
      .then((res) => res.json())
      .then((data: Company[]) => setCompanies(data));
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

  function changeSector(next: string) {
    setSector(next);
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

        <div className={styles.filters}>
          <FilterSelect
            label="Posted"
            value={postedWithin}
            options={POSTED_WITHIN_OPTIONS}
            onChange={setPostedWithin}
          />
          <FilterSelect
            label="Sector"
            value={sector}
            options={[
              { value: "", label: "All sectors" },
              ...sectors.map((s) => ({ value: s, label: s })),
            ]}
            onChange={changeSector}
          />
          <FilterSelect
            label="Company"
            value={company}
            options={[
              { value: "", label: "All companies" },
              ...companyOptions.map((c) => ({ value: c.slug, label: c.name })),
            ]}
            onChange={setCompany}
          />
          <label className={styles.showHidden}>
            <input
              type="checkbox"
              checked={showHidden}
              onChange={(e) => setShowHidden(e.target.checked)}
            />
            Show hidden jobs (expired or applied)
          </label>
        </div>

        {loading ? (
          <p>Loading…</p>
        ) : jobs.length === 0 ? (
          <p>No jobs to show.</p>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Company</th>
                <th>Job Title</th>
                <th>Job ID</th>
                <th>Link</th>
                <th>Posted Date</th>
                <th>Applied</th>
                <th>Will Apply</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id}>
                  <td>{job.company}</td>
                  <td>{job.title}</td>
                  <td>{job.externalId}</td>
                  <td>
                    <a
                      href={job.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={styles.link}
                    >
                      {job.platform}
                    </a>
                  </td>
                  <td>{job.postedDate}</td>
                  <td>
                    <input
                      type="checkbox"
                      checked={job.applied}
                      disabled={savingIds.has(job.id)}
                      onChange={(e) => updateJob(job.id, { applied: e.target.checked })}
                    />
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      checked={job.willApply}
                      disabled={savingIds.has(job.id)}
                      onChange={(e) => updateJob(job.id, { willApply: e.target.checked })}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </main>
    </div>
  );
}
