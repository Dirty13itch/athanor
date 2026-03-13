import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.toString();
  const path = query
    ? `/v1/models/governance/promotions?${query}`
    : "/v1/models/governance/promotions";
  return proxyAgentJson(path, undefined, "Failed to fetch promotion controls");
}

export async function POST(request: NextRequest) {
  const body = await request.text();
  return proxyAgentJson(
    "/v1/models/governance/promotions",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    },
    "Failed to stage promotion candidate"
  );
}
