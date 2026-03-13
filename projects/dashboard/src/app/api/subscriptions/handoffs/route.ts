import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.toString();
  const path = query ? `/v1/subscriptions/handoffs?${query}` : "/v1/subscriptions/handoffs";
  return proxyAgentJson(path, undefined, "Failed to fetch subscription handoffs");
}

export async function POST(request: NextRequest) {
  const body = await request.text();
  return proxyAgentJson(
    "/v1/subscriptions/handoffs",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    },
    "Failed to create subscription handoff",
    30_000
  );
}
