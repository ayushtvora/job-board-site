import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

// How many jobs the scraper first found in the past 24 hours, whatever their
// status. The UI loads it with the scrape status (page load, finished scan).
export async function GET() {
  const dayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
  const count = await prisma.job.count({ where: { firstSeenAt: { gte: dayAgo } } });
  return NextResponse.json({ count });
}
