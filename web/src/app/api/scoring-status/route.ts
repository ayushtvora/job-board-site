import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { FIELDS } from "@/lib/scoring/resume";
import { IN_SCOPE, storedScoreKeys } from "@/lib/scoring/worker";

// Scoring progress for the status line above the table: how many of the
// default view's jobs have a current score, and the worker's last error.
export async function GET() {
  const [keys, total, state] = await Promise.all([
    storedScoreKeys(),
    prisma.job.count({ where: IN_SCOPE }),
    prisma.scoringState.findUnique({ where: { id: 1 } }),
  ]);
  const scored = keys.size
    ? await prisma.job.count({
        where: {
          ...IN_SCOPE,
          OR: FIELDS.filter((field) => keys.has(field)).map((field) => ({ field, scoreKey: keys.get(field) })),
        },
      })
    : 0;

  return NextResponse.json({
    scored,
    total,
    lastError: state?.lastError ?? null,
    lastErrorAt: state?.lastErrorAt?.toISOString() ?? null,
  });
}
