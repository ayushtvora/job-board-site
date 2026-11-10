import { generateText, Output } from "ai";
import { z } from "zod";
import { scoringModel } from "./model";

// Bump when the prompt or schema changes, so every job gets re-scored with
// the new one (it's part of each job's score_key).
export const PROMPT_VERSION = 1;

// Descriptions are stored up to 20k chars; this keeps the prompt (and the
// free tier's token quota) in check without losing anything that matters.
const MAX_DESCRIPTION_CHARS = 12_000;

const SYSTEM_PROMPT = `You rate how well a job posting fits a candidate, from their resume.

Score from 0 to 100 using these anchors:
- 90-100: Strong match. The candidate meets nearly all requirements, at the right seniority, and would be a competitive applicant.
- 70-89: Good match. Most core skills line up; a few gaps a hiring manager would likely overlook.
- 50-69: Stretch. Relevant background, but notable gaps in required skills, domain or years of experience.
- 30-49: Weak match. Some overlap, but the role mostly needs things the candidate doesn't have.
- 0-29: Poor match. A different field, or far above the candidate's level.

Weigh, in order:
1. Seniority: compare the years of experience and level the posting asks for with the candidate's actual experience (count co-ops and internships, and note graduation dates). A senior, staff, lead, principal or manager role, or one requiring many more years than the candidate has, should score low even when the skills match.
2. Required skills and technologies versus the resume.
3. Domain and type of work versus the candidate's experience and projects.
Preferred or "nice to have" qualifications count much less than required ones.

Be calibrated: most postings are not strong matches. Judge only from the resume and the posting; don't assume skills the resume doesn't show.

Return:
- score: an integer from 0 to 100.
- reason: one sentence naming the deciding factor(s).
- matchedSkills: up to 8 short names of skills or qualifications the posting asks for that the resume shows.
- missingSkills: up to 8 short names of required skills or qualifications the posting asks for that the resume lacks.
If only the title is available, score from the title alone, keep the score between 20 and 80 unless the title alone makes the fit clear, and return empty skill lists.`;

const schema = z.object({
  score: z.number().int().describe("0 to 100"),
  reason: z.string().describe("One sentence naming the deciding factor(s)"),
  matchedSkills: z.array(z.string()).describe("Up to 8 required skills the resume shows"),
  missingSkills: z.array(z.string()).describe("Up to 8 required skills the resume lacks"),
});

export type JobToScore = {
  title: string;
  company: string;
  location: string;
  description: string | null;
};

export type ScoreResult = {
  score: number;
  reason: string;
  matchedSkills: string[];
  missingSkills: string[];
  basis: "description" | "title";
};

export async function scoreJob(job: JobToScore, resume: string): Promise<ScoreResult> {
  const basis = job.description ? "description" : "title";
  const posting = [
    `Title: ${job.title}`,
    `Company: ${job.company}`,
    `Location: ${job.location}`,
    job.description
      ? `Description:\n${job.description.slice(0, MAX_DESCRIPTION_CHARS)}`
      : "Description: not available (score from the title only).",
  ].join("\n");

  const { output } = await generateText({
    model: scoringModel(),
    system: SYSTEM_PROMPT,
    prompt: `<resume>\n${resume}\n</resume>\n\n<posting>\n${posting}\n</posting>`,
    output: Output.object({ schema }),
    // The worker handles retries (and backs off on rate limits) itself.
    maxRetries: 0,
    abortSignal: AbortSignal.timeout(120_000),
  });

  return {
    score: Math.max(0, Math.min(100, Math.round(output.score))),
    reason: output.reason.trim(),
    matchedSkills: basis === "title" ? [] : output.matchedSkills.slice(0, 8),
    missingSkills: basis === "title" ? [] : output.missingSkills.slice(0, 8),
    basis,
  };
}
