import { createHash } from "node:crypto";
import { prisma } from "@/lib/prisma";

// Each job is scored against the resume for its `field` (set by the
// scraper: "Software" or "Data"). The URLs point at the raw LaTeX source
// in the resume's GitHub repo.
export const RESUME_URL_ENV = {
  Software: "RESUME_URL_SOFTWARE",
  Data: "RESUME_URL_DATA",
} as const;
export type Field = keyof typeof RESUME_URL_ENV;
export const FIELDS = Object.keys(RESUME_URL_ENV) as Field[];

// How long a fetched resume is reused before it's fetched again.
const REFRESH_MS = 60 * 60 * 1000;

export type LoadedResume = { text: string; hash: string };

export function resumeUrlsConfigured(): boolean {
  return FIELDS.some((field) => process.env[RESUME_URL_ENV[field]]);
}

/**
 * The current resume per field, fetched from its URL at most hourly and
 * stored in the `resumes` table. A field whose URL is unset is left out
 * (its jobs stay unscored). If a fetch fails, the last stored copy is used
 * and the error is thrown only when there's no stored copy at all.
 */
export async function loadResumes(): Promise<Map<Field, LoadedResume>> {
  const stored = new Map((await prisma.resume.findMany()).map((row) => [row.field, row]));
  const resumes = new Map<Field, LoadedResume>();
  for (const field of FIELDS) {
    const url = process.env[RESUME_URL_ENV[field]];
    if (!url) continue;
    const row = stored.get(field);
    if (row && Date.now() - row.fetchedAt.getTime() < REFRESH_MS) {
      resumes.set(field, { text: row.text, hash: row.hash });
      continue;
    }
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(30_000), cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const text = latexToText(await response.text());
      if (text.length < 200) throw new Error("resume text is suspiciously short");
      const hash = createHash("sha256").update(text).digest("hex");
      await prisma.resume.upsert({
        where: { field },
        create: { field, text, hash, fetchedAt: new Date() },
        update: { text, hash, fetchedAt: new Date() },
      });
      resumes.set(field, { text, hash });
    } catch (err) {
      if (!row) throw new Error(`Couldn't fetch the ${field} resume from ${url}: ${String(err)}`);
      console.warn(`[scoring] Couldn't refresh the ${field} resume, using the stored copy:`, err);
      resumes.set(field, { text: row.text, hash: row.hash });
    }
  }
  return resumes;
}

/**
 * A LaTeX resume as plain text, close enough for a model to read: the
 * document body only, without the contact header (name, email, phone and
 * links don't help scoring and needn't be sent with every request), with
 * sections as "## Title" and \item as "- ". Plain text or Markdown passes
 * through unchanged.
 */
export function latexToText(source: string): string {
  const begin = source.indexOf("\\begin{document}");
  if (begin === -1) return source.trim();
  const end = source.indexOf("\\end{document}");
  let text = source.slice(begin + "\\begin{document}".length, end === -1 ? undefined : end);

  text = text
    .replace(/(?<!\\)%.*$/gm, "")
    .replace(/\\begin\{header\}[\s\S]*?\\end\{header\}/g, "")
    // Macro definitions at the top of the body.
    .replace(/^\s*\\(?:newcommand|renewcommand|newsavebox|sbox|cleaders|ignorespaces|unskip)\b.*$/gm, "")
    .replace(/\\section\*?\{([^}]*)\}/g, "\n## $1\n")
    .replace(/\\item\b/g, "\n- ")
    .replace(/\\(?:href|hrefWithoutArrow|url)\{[^}]*\}\{([^}]*)\}/g, "$1")
    // Environment arguments are content in resume templates (dates and
    // places of twocolentry), so keep them and drop only the name.
    .replace(/\\begin\{[^}]*\}((?:\{[^}]*\})*)/g, (_m, args: string) => " " + args.replace(/[{}]/g, " ") + " ")
    .replace(/\\end\{[^}]*\}/g, "\n");

  // Formatting commands that wrap text: keep the text. Repeated for nesting.
  for (let i = 0; i < 5; i++) {
    text = text.replace(/\\(?:textbf|textit|emph|underline|mbox|textsc|small|large|Large|normalsize)\{([^{}]*)\}/g, "$1");
  }
  return text
    // Any other command (and its optional/length arguments) is layout.
    .replace(/\\(?:vspace|hspace|kern|fontsize)\*?\s*\{[^}]*\}(?:\{[^}]*\})?/g, "")
    .replace(/\\kern\s*[\d.]+\s*pt/g, "")
    .replace(/\\([#&%$_])/g, "$1")
    .replace(/\\\\/g, "\n")
    .replace(/\\[a-zA-Z]+\*?/g, "")
    .replace(/[{}]/g, "")
    .replace(/[ \t]+/g, " ")
    .split("\n")
    .map((line) => line.trim())
    .filter((line, i, lines) => line || (lines[i - 1] ?? "") !== "")
    .join("\n")
    .trim();
}
