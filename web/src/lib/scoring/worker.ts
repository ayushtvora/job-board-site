import { createHash } from "node:crypto";
import { APICallError } from "ai";
import type { Prisma } from "@/generated/prisma/client";
import { prisma } from "@/lib/prisma";
import { scoringModelConfigured, scoringModelId } from "./model";
import { buildPriorityModel, jobPriority, PRIORITY_VERSION, type PriorityModel } from "./priority";
import { type Field, FIELDS, type LoadedResume, loadResumes, resumeUrlsConfigured } from "./resume";
import { PROMPT_VERSION, scoreJob } from "./scoreJob";

// Background scoring loop, started once per server by src/instrumentation.ts.
// It scores one job at a time, at most SCORING_RPM per minute (the Gemini
// free tier allows ~15/min on Flash-Lite), the jobs most likely to score
// high first (see priority.ts), and sleeps when there's nothing to do. Scores only ever change here: the
// scraper never writes the score columns.

const DEFAULT_RPM = 10;
const IDLE_MS = 60_000;
// After a rate-limit (429) response. A free tier's daily quota shows up as
// a 429 too, so this also paces a quota-exhausted worker until it resets.
const RATE_LIMIT_BACKOFF_MS = 5 * 60_000;
// When a 429 says when the quota resets (a free tier's daily quota does),
// the worker sleeps until then, up to this long.
const MAX_QUOTA_WAIT_MS = 24 * 60 * 60_000;
// After a server error, e.g. Gemini's 503 "high demand", which is usually
// gone within a minute, or a resume fetch or database error.
const ERROR_BACKOFF_MS = 60_000;
// A job whose scoring fails this many times (e.g. the model never returns
// valid output for it) is skipped until the server restarts.
const MAX_JOB_FAILURES = 3;
// Jobs the scraper never fetches a description for (e.g. Meta and Uber)
// are scored on their title once they're this old, rather than waiting.
const DESCRIPTION_WAIT_MS = 12 * 60 * 60_000;
// Jobs given a priority per transaction; the first run after deploying has ~3,200.
const PRIORITY_BATCH = 500;
// How long the word statistics behind the priority (priority.ts) are reused.
const PRIORITY_MODEL_TTL_MS = 6 * 60 * 60_000;

/**
 * The jobs whose score is shown in the default view, i.e. the ones worth
 * paying (or spending free quota) to score.
 */
export const IN_SCOPE: Prisma.JobWhereInput = { isActive: true, applied: false, willApply: true };

/**
 * Each field's current score key: a job whose score_key differs was scored
 * with an older resume, model or prompt (or never), and gets (re-)scored.
 * Changing one resume only re-scores that field's jobs.
 */
export function scoreKeys(resumeHashes: Map<Field, string>): Map<Field, string> {
  const keys = new Map<Field, string>();
  for (const [field, hash] of resumeHashes) {
    const key = createHash("sha256")
      .update(`${hash}|${scoringModelId()}|v${PROMPT_VERSION}`)
      .digest("hex")
      .slice(0, 16);
    keys.set(field, key);
  }
  return keys;
}

/** Score keys from the stored resumes, without fetching (for the status API). */
export async function storedScoreKeys(): Promise<Map<Field, string>> {
  const rows = await prisma.resume.findMany();
  return scoreKeys(new Map(rows.map((row) => [row.field as Field, row.hash])));
}

const globalForWorker = globalThis as unknown as { scoringWorkerStarted?: boolean };

export function startScoringWorker() {
  if (globalForWorker.scoringWorkerStarted) return;
  if (!resumeUrlsConfigured() || !scoringModelConfigured()) {
    console.log("[scoring] Not starting: set RESUME_URL_SOFTWARE/RESUME_URL_DATA and the SCORING_MODEL provider's API key");
    return;
  }
  globalForWorker.scoringWorkerStarted = true;
  console.log(`[scoring] Worker started (${scoringModelId()}, ${rpm()} requests/min)`);
  void runForever();
}

function rpm(): number {
  const value = Number(process.env.SCORING_RPM);
  return Number.isFinite(value) && value > 0 ? value : DEFAULT_RPM;
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

async function runForever() {
  const failures = new Map<number, number>();
  let errorShown = false;

  for (;;) {
    let waitMs = 60_000 / rpm();
    try {
      const outcome = await scoreNextJob(failures);
      if (outcome === "idle") {
        waitMs = IDLE_MS;
      } else if (errorShown) {
        // Scoring works again, so the UI stops showing the old error.
        await prisma.scoringState.upsert({
          where: { id: 1 },
          create: { id: 1 },
          update: { lastError: null, lastErrorAt: null },
        });
        errorShown = false;
      }
    } catch (err) {
      const { message, backOffMs, jobId } = describeError(err);
      console.error("[scoring]", message);
      if (jobId !== undefined) failures.set(jobId, (failures.get(jobId) ?? 0) + 1);
      if (backOffMs) waitMs = backOffMs;
      await recordError(message);
      errorShown = true;
    }
    await sleep(waitMs);
  }
}

class JobScoringError extends Error {
  constructor(
    readonly jobId: number,
    readonly cause: unknown,
  ) {
    super(`Scoring job ${jobId} failed`);
  }
}

async function scoreNextJob(failures: Map<number, number>): Promise<"scored" | "idle"> {
  const resumes = await loadResumes();
  const keys = scoreKeys(new Map([...resumes].map(([field, resume]) => [field, resume.hash])));
  if (keys.size === 0) return "idle";

  // Wait for the scraper's description pass, unless it gave up.
  const ready: Prisma.JobWhereInput = {
    OR: [
      { description: { not: null } },
      { descriptionAttempts: { gt: 0 } },
      { firstSeenAt: { lt: new Date(Date.now() - DESCRIPTION_WAIT_MS) } },
    ],
  };
  await fillPriorities(resumes, ready);

  const skip = [...failures].filter(([, count]) => count >= MAX_JOB_FAILURES).map(([id]) => id);
  const where: Prisma.JobWhereInput = {
    ...IN_SCOPE,
    id: { notIn: skip },
    OR: FIELDS.filter((field) => keys.has(field)).map((field) => ({
      field,
      OR: [
        { scoreKey: null },
        { scoreKey: { not: keys.get(field) } },
        // Scored from the title before the scraper found a description
        // (e.g. jobs that existed before descriptions were scraped).
        { scoreBasis: "title", description: { not: null } },
      ],
    })),
    AND: ready,
  };
  // Most likely to score high first (priority.ts); a job not given a
  // priority yet goes last, then newest posting first.
  const job = await prisma.job.findFirst({
    where,
    orderBy: [
      { scorePriority: { sort: "desc", nulls: "last" } },
      { postedDate: { sort: "desc", nulls: "last" } },
      { firstSeenAt: "desc" },
    ],
    select: {
      id: true,
      title: true,
      location: true,
      description: true,
      field: true,
      company: { select: { name: true } },
    },
  });
  if (!job) return "idle";

  const field = job.field as Field;
  let result;
  try {
    result = await scoreJob(
      { title: job.title, company: job.company.name, location: job.location, description: job.description },
      resumes.get(field)!.text,
    );
  } catch (err) {
    throw new JobScoringError(job.id, err);
  }

  await prisma.job.update({
    where: { id: job.id },
    data: {
      score: result.score,
      scoreReason: result.reason,
      matchedSkills: result.matchedSkills,
      missingSkills: result.missingSkills,
      scoreBasis: result.basis,
      scoreKey: keys.get(field),
      scoredAt: new Date(),
    },
  });
  return "scored";
}

export /**
 * Each field's current priority key: a job whose priority_key differs was
 * given its priority with an older resume, heuristic or referral list (or
 * never).
 */
async function priorityKeys(resumes: Map<Field, LoadedResume>): Promise<Map<Field, string>> {
  const referrals = await prisma.company.findMany({
    where: { referral: true },
    select: { slug: true },
    orderBy: { slug: "asc" },
  });
  const referralList = referrals.map((company) => company.slug).join(",");
  const keys = new Map<Field, string>();
  for (const [field, resume] of resumes) {
    keys.set(
      field,
      createHash("sha256").update(`${resume.hash}|p${PRIORITY_VERSION}|r${referralList}`).digest("hex").slice(0, 16),
    );
  }
  return keys;
}

let cachedModel: { model: PriorityModel; resumeHashes: string; builtAt: number } | null = null;

/**
 * The priority heuristic's word statistics, from every job in the default
 * view, rebuilt when a resume changes or after PRIORITY_MODEL_TTL_MS.
 */
async function priorityModel(resumes: Map<Field, LoadedResume>): Promise<PriorityModel> {
  const resumeHashes = [...resumes].map(([field, resume]) => `${field}:${resume.hash}`).join(",");
  if (cachedModel && cachedModel.resumeHashes === resumeHashes && Date.now() - cachedModel.builtAt < PRIORITY_MODEL_TTL_MS) {
    return cachedModel.model;
  }
  const corpus = await prisma.job.findMany({
    where: { ...IN_SCOPE, description: { not: null } },
    select: { description: true },
  });
  const model = buildPriorityModel(
    new Map([...resumes].map(([field, resume]) => [field, resume.text])),
    corpus.map((job) => job.description!),
  );
  cachedModel = { model, resumeHashes, builtAt: Date.now() };
  return model;
}

/**
 * Gives a priority to every job ready to score that doesn't have a current
 * one, PRIORITY_BATCH per transaction. Only ready jobs, so the priority is
 * computed from the description the job will be scored with.
 */
async function fillPriorities(resumes: Map<Field, LoadedResume>, ready: Prisma.JobWhereInput) {
  const keys = await priorityKeys(resumes);
  for (;;) {
    const pending = await prisma.job.findMany({
      where: {
        ...IN_SCOPE,
        OR: [...keys].map(([field, key]) => ({ field, OR: [{ priorityKey: null }, { priorityKey: { not: key } }] })),
        AND: ready,
      },
      select: { id: true, title: true, description: true, field: true, company: { select: { referral: true } } },
      take: PRIORITY_BATCH,
    });
    if (pending.length === 0) return;
    const model = await priorityModel(resumes);
    await prisma.$transaction(
      pending.map((job) =>
        prisma.job.update({
          where: { id: job.id },
          data: { scorePriority: jobPriority(model, { ...job, referral: job.company.referral }), priorityKey: keys.get(job.field as Field) },
        }),
      ),
    );
    if (pending.length < PRIORITY_BATCH) return;
  }
}

function describeError(err: unknown): { message: string; backOffMs?: number; jobId?: number } {
  const jobId = err instanceof JobScoringError ? err.jobId : undefined;
  const cause = err instanceof JobScoringError ? err.cause : err;
  if (APICallError.isInstance(cause)) {
    const status = cause.statusCode;
    if (status === 429) {
      const quota = quotaDetails(cause);
      if (quota.retryMs && quota.retryMs > RATE_LIMIT_BACKOFF_MS) {
        // A used-up daily quota: sleep until it resets instead of retrying
        // every few minutes all night.
        const resumesAt = new Date(Date.now() + quota.retryMs);
        const limit = quota.limit ? ` (${quota.limit} requests)` : "";
        return {
          message: `Daily quota${limit} for ${scoringModelId()} is used up; scoring resumes around ${resumesAt.toLocaleString("en-CA", { timeZone: process.env.TZ || "America/Toronto", dateStyle: "medium", timeStyle: "short" })}`,
          backOffMs: Math.min(quota.retryMs + 60_000, MAX_QUOTA_WAIT_MS),
        };
      }
    }
    const backOffMs =
      status === 429 ? RATE_LIMIT_BACKOFF_MS : status !== undefined && status >= 500 ? ERROR_BACKOFF_MS : undefined;
    // Only the message: the error also carries the whole request, resume included.
    return {
      message: `${status ?? "API"} error from ${scoringModelId()}: ${cause.message.slice(0, 300)}`,
      backOffMs,
      // A rate limit or outage isn't the job's fault, so it doesn't count
      // toward skipping it.
      jobId: backOffMs ? undefined : jobId,
    };
  }
  const text = cause instanceof Error ? cause.message : String(cause);
  return {
    message: jobId !== undefined ? `Job ${jobId}: ${text.slice(0, 300)}` : text.slice(0, 300),
    // Not a model call (e.g. a resume fetch or database error): wait a bit.
    backOffMs: jobId === undefined ? ERROR_BACKOFF_MS : undefined,
    jobId,
  };
}

/**
 * How long a 429 says to wait, and the quota's size if it names one. Gemini
 * puts both in the error body (RetryInfo.retryDelay "33834s", and
 * QuotaFailure violations with a quotaValue, e.g. the free tier's 500
 * requests per day per model); other providers send a Retry-After header.
 */
function quotaDetails(error: APICallError): { retryMs?: number; limit?: string } {
  let retryMs: number | undefined;
  let limit: string | undefined;
  try {
    const details = JSON.parse(error.responseBody ?? "{}")?.error?.details ?? [];
    for (const detail of details) {
      const delay = /^(\d+(?:\.\d+)?)s$/.exec(detail?.retryDelay ?? "");
      if (delay) retryMs = Number(delay[1]) * 1000;
      for (const violation of detail?.violations ?? []) {
        if (violation?.quotaValue) limit = String(violation.quotaValue);
      }
    }
  } catch {
    // Not JSON; fall back to the header.
  }
  const header = Number(error.responseHeaders?.["retry-after"]);
  if (retryMs === undefined && Number.isFinite(header) && header > 0) retryMs = header * 1000;
  return { retryMs, limit };
}

async function recordError(message: string) {
  try {
    await prisma.scoringState.upsert({
      where: { id: 1 },
      create: { id: 1, lastError: message, lastErrorAt: new Date() },
      update: { lastError: message, lastErrorAt: new Date() },
    });
  } catch (err) {
    console.error("[scoring] Couldn't record the error:", err);
  }
}
