import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const limit = request.nextUrl.searchParams.get("limit") ?? "30";
  return proxyAgentJson(
    `/v1/subscriptions/routing-log?limit=${encodeURIComponent(limit)}`,
    undefined,
    "Failed to fetch routing log"
  );
}
