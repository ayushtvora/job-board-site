import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
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

  const isActiveOverride = parseBoolParam(params.get("is_active"));
  if (isActiveOverride !== undefined) where.isActive = isActiveOverride;

  const appliedOverride = parseBoolParam(params.get("applied"));
  if (appliedOverride !== undefined) where.applied = appliedOverride;

  const willApplyOverride = parseBoolParam(params.get("will_apply"));
  if (willApplyOverride !== undefined) where.willApply = willApplyOverride;

  const jobs = await prisma.job.findMany({
    where,
    include: { company: true },
    orderBy: [
      { postedDate: { sort: "desc", nulls: "last" } },
      { company: { name: "asc" } },
      { title: "asc" },
    ],
  });

  return NextResponse.json(
    jobs.map((job) => ({
      id: job.id,
      company: job.company.name,
      title: job.title,
      externalId: job.externalId,
      url: job.url,
      platform: job.platform,
      postedDate: job.postedDate
        ? job.postedDate.toISOString().slice(0, 10)
        : null,
      applied: job.applied,
      willApply: job.willApply,
    })),
  );
}
