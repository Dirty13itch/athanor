import { NextRequest } from "next/server";
import { proxyOperatorReadJson } from "@/app/api/operator/fail-soft";

export async function GET(request: NextRequest) {
  const params = new URLSearchParams(request.nextUrl.searchParams);
  const query = params.toString();
  return proxyOperatorReadJson(`/v1/operator/approvals${query ? `?${query}` : ""}`, "Failed to fetch operator approvals", {
    approvals: [],
    count: 0,
  });
}
