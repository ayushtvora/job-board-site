import type { Company, Job } from "@/generated/prisma/client";

// Fall back to first_seen_at (the scrape that first found this job) when the
// source site doesn't expose a posted date, so the column is never empty in
// the UI — first_seen_at itself stays untouched as the actual
// scrape-discovery timestamp. Shared with the default sort so a row's
// position always matches the date it displays.
export function effectivePostedDate(job: Pick<Job, "postedDate" | "firstSeenAt">): Date {
  return job.postedDate ?? job.firstSeenAt;
}

export function serializeJob(job: Job & { company: Company }) {
  return {
    id: job.id,
    company: job.company.name,
    title: job.title,
    externalId: job.externalId,
    url: job.url,
    platform: job.platform,
    postedDate: effectivePostedDate(job).toISOString().slice(0, 10),
    applied: job.applied,
    willApply: job.willApply,
  };
}
