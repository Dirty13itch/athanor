import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const params = new URLSearchParams(request.nextUrl.searchParams);
  const response = await proxyAgentJson(
    `/v1/activity/stats?${params.toString()}`,
    undefined,
    "Failed to fetch activity stats"
  );
  if (response.status === 401 || response.status === 403) {
    return Response.json({ stats: null }, { status: 200 });
  }
  return response;
}
