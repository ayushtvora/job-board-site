import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { effectivePostedDate, serializeJob } from "@/lib/serializeJob";
import { Prisma } from "@/generated/prisma/client";

function parseBoolParam(value: string | null): boolean | undefined {
  if (value === null) return undefined;
  return value === "true";
}

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const showHidden = params.get("showHidden") === "true";

  const where: Prisma.JobWhereInput = { willApply: true };
  if (!showHidden) {
    where.isActive = true;
    where.applied = false;
  }

  const company = params.get("company");
  if (company) where.companyId = company;

  const field = params.get("field");
  if (field) where.field = field;

  const city = params.get("city");
  if (city) where.cities = { has: city };

  const sector = params.get("sector");
  if (sector) where.company = { sectors: { has: sector } };

  // postedWithin=N keeps jobs whose *effective* posted date (see
  // effectivePostedDate) is within the last N days, compared by calendar
  // date (UTC, same as the displayed date) since posted_date has no time.
  const postedWithin = Number(params.get("postedWithin"));
  if (Number.isInteger(postedWithin) && postedWithin > 0) {
    const cutoff = new Date();
    cutoff.setUTCHours(0, 0, 0, 0);
    cutoff.setUTCDate(cutoff.getUTCDate() - postedWithin);
    where.OR = [
      { postedDate: { gte: cutoff } },
      { postedDate: null, firstSeenAt: { gte: cutoff } },
    ];
  }

  const isActiveOverride = parseBoolParam(params.get("is_active"));
  if (isActiveOverride !== undefined) where.isActive = isActiveOverride;

  const appliedOverride = parseBoolParam(params.get("applied"));
  if (appliedOverride !== undefined) where.applied = appliedOverride;

  const willApplyOverride = parseBoolParam(params.get("will_apply"));
  if (willApplyOverride !== undefined) where.willApply = willApplyOverride;

  const jobs = await prisma.job.findMany({
    where,
    include: { company: true },
    // Descriptions are only for scoring and the detail panel
    // (GET /api/jobs/:id); the table loads every job at once.
    omit: { description: true },
  });

  // Sorted in JS rather than via Prisma's orderBy: the effective date (see
  // effectivePostedDate) coalesces posted_date with first_seen_at, which
  // isn't expressible as a plain column sort, and the row counts here are
  // small enough that this costs nothing.
  jobs.sort((a, b) => {
    const dateDiff = effectivePostedDate(b).getTime() - effectivePostedDate(a).getTime();
    if (dateDiff !== 0) return dateDiff;
    const companyDiff = a.company.name.localeCompare(b.company.name);
    if (companyDiff !== 0) return companyDiff;
    return a.title.localeCompare(b.title);
  });

  return NextResponse.json(jobs.map(serializeJob));
}
