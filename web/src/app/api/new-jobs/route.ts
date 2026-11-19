import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

// How many new jobs the last scan found: per company, the jobs first seen
// since its most recent scrape run started (a run saves its jobs right
// after it finishes, so those are exactly that run's new ones), summed.
// The UI loads it with the scrape status (page load, finished scan).
export async function GET() {
  const [{ count }] = await prisma.$queryRaw<{ count: number }[]>`
    SELECT count(*)::int AS count
    FROM jobs j
    JOIN (
      SELECT DISTINCT ON (company_id) company_id, started_at
      FROM scrape_runs
      ORDER BY company_id, started_at DESC
    ) latest ON latest.company_id = j.company_id
    WHERE j.first_seen_at >= latest.started_at
  `;
  return NextResponse.json({ count });
}
