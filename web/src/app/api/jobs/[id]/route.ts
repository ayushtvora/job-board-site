import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { serializeJob } from "@/lib/serializeJob";
import type { Prisma } from "@/generated/prisma/client";

const ALLOWED_FIELDS = new Set(["applied", "willApply"]);

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id: idParam } = await params;
  const id = Number(idParam);
  if (!Number.isInteger(id)) {
    return NextResponse.json({ error: "Invalid job id" }, { status: 400 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return NextResponse.json(
      { error: "Body must be a JSON object" },
      { status: 400 },
    );
  }

  const fields = body as Record<string, unknown>;
  const unsupported = Object.keys(fields).filter((key) => !ALLOWED_FIELDS.has(key));
  if (unsupported.length > 0) {
    return NextResponse.json(
      { error: `Unsupported field(s): ${unsupported.join(", ")}` },
      { status: 400 },
    );
  }

  const { applied, willApply } = fields;
  if (applied !== undefined && typeof applied !== "boolean") {
    return NextResponse.json({ error: "applied must be a boolean" }, { status: 400 });
  }
  if (willApply !== undefined && typeof willApply !== "boolean") {
    return NextResponse.json({ error: "willApply must be a boolean" }, { status: 400 });
  }

  const existing = await prisma.job.findUnique({ where: { id } });
  if (!existing) {
    return NextResponse.json({ error: "Job not found" }, { status: 404 });
  }

  const data: Prisma.JobUpdateInput = {};
  if (willApply !== undefined) {
    data.willApply = willApply as boolean;
  }
  if (applied !== undefined) {
    const nextApplied = applied as boolean;
    data.applied = nextApplied;
    if (nextApplied && !existing.applied) {
      data.appliedAt = new Date();
    } else if (!nextApplied && existing.applied) {
      data.appliedAt = null;
    }
  }

  const updated = await prisma.job.update({
    where: { id },
    data,
    include: { company: true },
  });

  return NextResponse.json(serializeJob(updated));
}
