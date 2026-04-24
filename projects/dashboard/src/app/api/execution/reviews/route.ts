import { NextRequest, NextResponse } from "next/server";
import { loadExecutionReviews } from "@/lib/executive-kernel";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const rawLimit = Number.parseInt(params.get("limit") ?? "50", 10);
  const reviews = await loadExecutionReviews({
    status: params.get("status"),
    family: params.get("family"),
    limit: Number.isFinite(rawLimit) && rawLimit > 0 ? rawLimit : 50,
  });

  return NextResponse.json({
    reviews,
    count: reviews.length,
  });
}
