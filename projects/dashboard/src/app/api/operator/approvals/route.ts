import { NextRequest, NextResponse } from "next/server";
import { proxyOperatorReadJson } from "@/app/api/operator/fail-soft";
import { listBuilderSyntheticApprovals } from "@/lib/builder-store";

export async function GET(request: NextRequest) {
  const params = new URLSearchParams(request.nextUrl.searchParams);
  const query = params.toString();
  const response = await proxyOperatorReadJson(
    `/v1/operator/approvals${query ? `?${query}` : ""}`,
    "Failed to fetch operator approvals",
    {
      approvals: [],
      count: 0,
    },
  );

  const payload = (await response.json().catch(() => ({}))) as {
    approvals?: Array<Record<string, unknown>>;
    count?: number;
    [key: string]: unknown;
  };
  const builderApprovals = await listBuilderSyntheticApprovals(params.get("status"));
  const approvals = [...builderApprovals, ...((Array.isArray(payload.approvals) ? payload.approvals : []) as Array<Record<string, unknown>>)]
    .sort((left, right) => Number(right.requested_at ?? 0) - Number(left.requested_at ?? 0));

  return NextResponse.json({
    ...payload,
    approvals,
    count: approvals.length,
  });
}
