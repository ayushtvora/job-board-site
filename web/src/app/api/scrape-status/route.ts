import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET() {
  const latestRuns = await prisma.scrapeRun.findMany({
    distinct: ["companyId"],
    orderBy: [{ companyId: "asc" }, { startedAt: "desc" }],
    include: { company: true },
  });

  return NextResponse.json(
    latestRuns.map((run) => ({
      company: run.company.name,
      status: run.status,
      errorMessage: run.errorMessage,
      finishedAt: run.finishedAt ? run.finishedAt.toISOString() : null,
    })),
  );
}
