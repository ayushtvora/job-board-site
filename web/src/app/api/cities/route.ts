import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

// Feeds the City filter dropdown: every city any job is in, sorted, with
// "Remote" last.
export async function GET() {
  const rows = await prisma.$queryRaw<{ city: string }[]>`
    SELECT DISTINCT unnest(cities) AS city FROM jobs
  `;
  const cities = rows
    .map((row) => row.city)
    .sort((a, b) => Number(a === "Remote") - Number(b === "Remote") || a.localeCompare(b));
  return NextResponse.json(cities);
}
