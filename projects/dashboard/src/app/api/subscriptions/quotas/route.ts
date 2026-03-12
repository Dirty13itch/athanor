import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.toString();
  const path = query ? `/v1/subscriptions/quotas?${query}` : "/v1/subscriptions/quotas";
  return proxyAgentJson(path, undefined, "Failed to fetch subscription quotas");
}
