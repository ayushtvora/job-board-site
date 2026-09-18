import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

function serializeRequest(request: {
  id: number;
  status: string;
  errorMessage: string | null;
  requestedAt: Date;
  finishedAt: Date | null;
}) {
  return {
    id: request.id,
    status: request.status,
    errorMessage: request.errorMessage,
    requestedAt: request.requestedAt.toISOString(),
    finishedAt: request.finishedAt ? request.finishedAt.toISOString() : null,
  };
}

export async function GET() {
  const latest = await prisma.scrapeRequest.findFirst({
    orderBy: { requestedAt: "desc" },
  });

  return NextResponse.json(latest ? serializeRequest(latest) : null);
}

export async function POST() {
  // Reuse an in-flight request instead of queuing a duplicate if the button
  // is clicked again while a scan is still pending/running.
  const inFlight = await prisma.scrapeRequest.findFirst({
    where: { status: { in: ["pending", "running"] } },
    orderBy: { requestedAt: "desc" },
  });
  if (inFlight) {
    return NextResponse.json(serializeRequest(inFlight));
  }

  const created = await prisma.scrapeRequest.create({ data: {} });
  return NextResponse.json(serializeRequest(created), { status: 201 });
}
