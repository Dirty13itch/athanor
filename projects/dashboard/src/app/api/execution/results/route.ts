import { NextRequest, NextResponse } from "next/server";
import { loadExecutionResults } from "@/lib/executive-kernel";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const rawLimit = Number.parseInt(params.get("limit") ?? "50", 10);
  const results = await loadExecutionResults({
    status: params.get("status"),
    family: params.get("family"),
    outcome: params.get("outcome"),
    limit: Number.isFinite(rawLimit) && rawLimit > 0 ? rawLimit : 50,
  });

  return NextResponse.json({
    results,
    count: results.length,
  });
}
