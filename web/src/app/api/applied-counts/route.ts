import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

const DAY_MS = 24 * 60 * 60 * 1000;

// How many jobs I marked applied in the past 24 hours and 7 days, by
// applied_at (cleared when a job is unchecked, so those don't count). The UI
// loads it on page load and after each Applied checkbox change.
export async function GET() {
  const now = Date.now();
  const appliedSince = (ms: number) =>
    prisma.job.count({ where: { applied: true, appliedAt: { gte: new Date(now - ms) } } });
  const [last24h, last7d] = await Promise.all([appliedSince(DAY_MS), appliedSince(7 * DAY_MS)]);
  return NextResponse.json({ last24h, last7d });
}
