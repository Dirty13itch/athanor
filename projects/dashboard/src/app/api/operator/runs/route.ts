import { NextRequest, NextResponse } from "next/server";
import { proxyOperatorReadJson } from "@/app/api/operator/fail-soft";
import { listBuilderSyntheticRuns } from "@/lib/builder-store";

export async function GET(request: NextRequest) {
  const params = new URLSearchParams(request.nextUrl.searchParams);
  const query = params.toString();
  const response = await proxyOperatorReadJson(
    `/v1/operator/runs${query ? `?${query}` : ""}`,
    "Failed to fetch operator runs",
    {
      runs: [],
      count: 0,
    },
  );

  const limit = Number(params.get("limit") ?? "50");
  const payload = (await response.json().catch(() => ({}))) as {
    runs?: Array<Record<string, unknown>>;
    count?: number;
    [key: string]: unknown;
  };
  const builderRuns = await listBuilderSyntheticRuns(params.get("status"), Number.isFinite(limit) ? limit : 50);
  const mergedRuns = [...builderRuns, ...((Array.isArray(payload.runs) ? payload.runs : []) as Array<Record<string, unknown>>)]
    .sort((left, right) => Number(right.updated_at ?? 0) - Number(left.updated_at ?? 0))
    .slice(0, Number.isFinite(limit) ? limit : 50);

  return NextResponse.json({
    ...payload,
    runs: mergedRuns,
    count: mergedRuns.length,
  });
}
