import { NextRequest, NextResponse } from "next/server";
import type { Job, JobCreateInput, ApiResult } from "@/types";

// POST /api/inspections — Create new inspection job
export async function POST(request: NextRequest) {
  try {
    const body: JobCreateInput = await request.json();

    if (!body.address) {
      return NextResponse.json(
        { error: "Address is required" },
        { status: 400 }
      );
    }

    // TODO: Insert into PostgreSQL
    const job: Job = {
      id: crypto.randomUUID(),
      address: body.address,
      builder: body.builder ?? null,
      inspector: body.inspector ?? "Shaun",
      status: "draft",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    return NextResponse.json({ data: job } satisfies ApiResult<Job>, {
      status: 201,
    });
  } catch {
    return NextResponse.json(
      { error: "Failed to create inspection" },
      { status: 500 }
    );
  }
}

// GET /api/inspections — List jobs with optional filters
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const status = searchParams.get("status");
  const builder = searchParams.get("builder");
  const _limit = parseInt(searchParams.get("limit") ?? "50", 10);
  const _offset = parseInt(searchParams.get("offset") ?? "0", 10);

  // TODO: Query PostgreSQL with filters
  void status;
  void builder;

  const jobs: Job[] = [];

  return NextResponse.json({ data: jobs } satisfies ApiResult<Job[]>);
}
