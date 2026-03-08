import { NextRequest, NextResponse } from "next/server";
import type { Inspection, JobUpdateInput, ApiResult } from "@/types";

// GET /api/inspections/[id] — Get full inspection with all related data
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  // TODO: Query PostgreSQL — join job with all child tables
  void id;

  return NextResponse.json(
    { error: "Not found" } satisfies ApiResult<Inspection>,
    { status: 404 }
  );
}

// PUT /api/inspections/[id] — Update job and/or related data
export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  try {
    const body: JobUpdateInput = await request.json();

    // TODO: Update PostgreSQL — transaction across all affected tables
    void id;
    void body;

    return NextResponse.json({ data: { updated: true } });
  } catch {
    return NextResponse.json(
      { error: "Failed to update inspection" },
      { status: 500 }
    );
  }
}
