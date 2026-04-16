import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const limit = request.nextUrl.searchParams.get("limit") ?? "30";
  const response = await proxyAgentJson(
    `/v1/subscriptions/routing-log?limit=${encodeURIComponent(limit)}`,
    undefined,
    "Failed to fetch routing log"
  );
  if (response.status === 401 || response.status === 403) {
    return Response.json({ entries: [] }, { status: 200 });
  }
  return response;
}
