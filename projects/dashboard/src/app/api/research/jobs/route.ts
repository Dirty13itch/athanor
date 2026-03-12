import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.toString();
  const path = query ? `/v1/research/jobs?${query}` : "/v1/research/jobs";
  return proxyAgentJson(path, undefined, "Failed to fetch research jobs");
}

export async function POST(request: NextRequest) {
  const body = await request.text();
  return proxyAgentJson(
    "/v1/research/jobs",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    },
    "Failed to create research job"
  );
}
