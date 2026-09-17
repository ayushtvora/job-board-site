import type { Company, Job } from "@/generated/prisma/client";

export function serializeJob(job: Job & { company: Company }) {
  return {
    id: job.id,
    company: job.company.name,
    title: job.title,
    externalId: job.externalId,
    url: job.url,
    platform: job.platform,
    postedDate: job.postedDate ? job.postedDate.toISOString().slice(0, 10) : null,
    applied: job.applied,
    willApply: job.willApply,
  };
}
