import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

// Feeds the Company and Sector filter dropdowns.
export async function GET() {
  const companies = await prisma.company.findMany({
    orderBy: { name: "asc" },
  });

  return NextResponse.json(
    companies.map((company) => ({
      slug: company.slug,
      name: company.name,
      sectors: company.sectors,
    })),
  );
}
