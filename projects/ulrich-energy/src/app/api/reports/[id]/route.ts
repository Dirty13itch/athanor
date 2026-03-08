import { NextRequest, NextResponse } from "next/server";
import type { Report, ApiResult } from "@/types";

// GET /api/reports/[id] — Get report by job ID (including narrative and PDF path)
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  // TODO: Query PostgreSQL reports table by job_id
  void id;

  return NextResponse.json(
    { error: "Report not found" } satisfies ApiResult<Report>,
    { status: 404 }
  );
}
