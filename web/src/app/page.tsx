"use client";

import { useCallback, useEffect, useState } from "react";
import styles from "./page.module.css";

type Job = {
  id: number;
  company: string;
  title: string;
  externalId: string;
  url: string;
  platform: string;
  postedDate: string | null;
  applied: boolean;
  willApply: boolean;
};

type ScrapeStatus = {
  company: string;
  status: "success" | "error";
  errorMessage: string | null;
  finishedAt: string | null;
};

export default function Home() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [showHidden, setShowHidden] = useState(false);
  const [savingIds, setSavingIds] = useState<Set<number>>(new Set());
  const [scrapeErrors, setScrapeErrors] = useState<ScrapeStatus[]>([]);
  const [bannerDismissed, setBannerDismissed] = useState(false);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    const res = await fetch(`/api/jobs${showHidden ? "?showHidden=true" : ""}`);
    const data: Job[] = await res.json();
    setJobs(data);
    setLoading(false);
  }, [showHidden]);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    fetch("/api/scrape-status")
      .then((res) => res.json())
      .then((data: ScrapeStatus[]) => {
        setScrapeErrors(data.filter((run) => run.status === "error"));
      });
  }, []);

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

        <label className={styles.showHidden}>
          <input
            type="checkbox"
            checked={showHidden}
            onChange={(e) => setShowHidden(e.target.checked)}
          />
          Show hidden jobs (expired or applied)
        </label>

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
                  <td>{job.postedDate ?? "—"}</td>
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
