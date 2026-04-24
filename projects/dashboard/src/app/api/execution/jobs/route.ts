import { NextRequest, NextResponse } from "next/server";
import { loadExecutionJobs } from "@/lib/executive-kernel";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const rawLimit = Number.parseInt(params.get("limit") ?? "50", 10);
  const jobs = await loadExecutionJobs({
    status: params.get("status"),
    family: params.get("family"),
    limit: Number.isFinite(rawLimit) && rawLimit > 0 ? rawLimit : 50,
  });

  return NextResponse.json({
    jobs,
    count: jobs.length,
  });
}
