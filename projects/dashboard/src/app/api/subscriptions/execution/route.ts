import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.toString();
  const path = query ? `/v1/subscriptions/execution?${query}` : "/v1/subscriptions/execution";
  return proxyAgentJson(path, undefined, "Failed to fetch subscription execution snapshot");
}

export async function POST(request: NextRequest) {
  const body = await request.text();
  return proxyAgentJson(
    "/v1/subscriptions/execution",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    },
    "Failed to execute provider request",
    120_000
  );
}
