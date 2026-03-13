import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.toString();
  const path = query ? `/v1/models/proving-ground?${query}` : "/v1/models/proving-ground";
  return proxyAgentJson(path, undefined, "Failed to fetch proving-ground snapshot");
}

export async function POST(request: NextRequest) {
  const body = await request.text();
  return proxyAgentJson(
    "/v1/models/proving-ground/run",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    },
    "Failed to run proving ground",
    60_000
  );
}
