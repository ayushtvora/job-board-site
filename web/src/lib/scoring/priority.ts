import { REFERRAL_PRIORITY_BONUS } from "@/lib/referral";
import type { Field } from "./resume";

// A cheap local estimate of how well a job fits the resume, used only to
// order the scoring queue so likely matches reach the model first (the
// Gemini free tier allows 500 scores a day). It's never shown.
//
// Checked on 2026-11-10 against the 328 jobs Gemini had scored so far
// (12 of them 70+): ordering by this put 11 of those 12 in the top 20%,
// where a random order puts about 2. Seniority in the title is the
// strongest signal, as in the scoring rubric (scoreJob.ts). The weights
// were fitted on that same small sample, so treat them as rough. Jobs at a
// company where I have a referral get REFERRAL_PRIORITY_BONUS on top.
//
// Bump PRIORITY_VERSION after changing anything here, so every job's
// priority is recomputed. (Changing which companies are referrals
// recomputes them too: the referral list is part of the priority key.)
export const PRIORITY_VERSION = 2;

const SENIOR_TITLE =
  /\b(senior|sr\.?|staff|principal|lead|manager|director|head|architect|vp|chief|expert|specialist [3-9]|iii|iv|[3-9])\b/i;
const JUNIOR_TITLE =
  /\b(intern(ship)?|co-?op|new grad|graduate|junior|jr\.?|entry|associate|student|early career|i|1|ii|2)\b/i;
// "5+ years", "3-5 years", "2 yrs", "5 ans": the smallest one found is
// taken as the requirement.
const YEARS_REQUIRED = /(\d{1,2})\s*\+?\s*(?:-\s*\d+\s*)?(?:years|yrs|ans)\b/gi;
const WORD = /[a-z][a-z0-9+#.]*[a-z0-9+#]|[a-z]/gi;

export type PriorityModel = {
  idf: Map<string, number>;
  defaultIdf: number;
  resumeVectors: Map<Field, Map<string, number>>;
  resumeSkills: Map<Field, string[]>;
};

/**
 * Word weights (IDF) from a corpus of job descriptions, plus each
 * resume's word vector and skill terms.
 */
export function buildPriorityModel(resumes: Map<Field, string>, descriptions: string[]): PriorityModel {
  const documentFrequency = new Map<string, number>();
  for (const description of descriptions) {
    for (const word of new Set(tokens(description))) {
      documentFrequency.set(word, (documentFrequency.get(word) ?? 0) + 1);
    }
  }
  const n = descriptions.length;
  const idf = new Map<string, number>();
  for (const [word, count] of documentFrequency) idf.set(word, Math.log((n + 1) / (count + 1)) + 1);
  const model: PriorityModel = {
    idf,
    defaultIdf: Math.log(n + 1) + 1,
    resumeVectors: new Map(),
    resumeSkills: new Map(),
  };
  for (const [field, text] of resumes) {
    model.resumeVectors.set(field, tfidf(model, tokens(text)));
    model.resumeSkills.set(field, skillTerms(text));
  }
  return model;
}

export function jobPriority(
  model: PriorityModel,
  job: { title: string; description: string | null; field: string; referral: boolean },
): number {
  const field = job.field as Field;
  const description = job.description ?? "";
  const lower = description.toLowerCase();

  const years = [...description.matchAll(YEARS_REQUIRED)].map((m) => Number(m[1])).filter((y) => y <= 20);
  const minYears = years.length ? Math.min(...years) : 0;
  const skills = model.resumeSkills.get(field) ?? [];
  const overlap = skills.filter((skill) =>
    new RegExp(`(?<![a-z0-9])${escapeRegExp(skill)}(?![a-z0-9])`).test(lower),
  ).length;
  const resumeVector = model.resumeVectors.get(field);
  const similarity = resumeVector && description ? cosine(tfidf(model, tokens(description)), resumeVector) : 0;

  return (
    (job.referral ? REFERRAL_PRIORITY_BONUS : 0) +
    (SENIOR_TITLE.test(job.title) ? -3 : 0) +
    (JUNIOR_TITLE.test(job.title) ? 2 : 0) -
    0.6 * Math.min(minYears, 10) +
    8 * similarity +
    0.15 * overlap
  );
}

function tokens(text: string): string[] {
  return (text.match(WORD) ?? []).map((word) => word.toLowerCase());
}

function tfidf(model: PriorityModel, words: string[]): Map<string, number> {
  const vector = new Map<string, number>();
  for (const word of words) vector.set(word, (vector.get(word) ?? 0) + 1);
  for (const [word, count] of vector) vector.set(word, count * (model.idf.get(word) ?? model.defaultIdf));
  return vector;
}

function cosine(a: Map<string, number>, b: Map<string, number>): number {
  let dot = 0;
  for (const [word, value] of a) dot += value * (b.get(word) ?? 0);
  const norm = (v: Map<string, number>) => Math.sqrt([...v.values()].reduce((sum, x) => sum + x * x, 0));
  const denominator = norm(a) * norm(b);
  return denominator ? dot / denominator : 0;
}

/**
 * Skill terms from the resume: the pieces of every list-like line (skills
 * sections and "Project - Tech, Tech, Tech" lines), lowercased.
 */
function skillTerms(resume: string): string[] {
  const terms = new Set<string>();
  for (const line of resume.split("\n")) {
    if (!line.includes(":") && !line.includes(",")) continue;
    for (const part of line.split(/[,:()/|]/)) {
      const term = part.replace(/^[\s.-]+|[\s.-]+$/g, "").toLowerCase();
      if (term.length > 1 && term.length <= 25 && term.split(/\s+/).length <= 3) terms.add(term);
    }
  }
  return [...terms];
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
