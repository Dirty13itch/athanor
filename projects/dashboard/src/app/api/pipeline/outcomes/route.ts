import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const limit = request.nextUrl.searchParams.get("limit") ?? "20";
  return proxyAgentJson(`/v1/pipeline/outcomes?limit=${limit}`, undefined, "Failed to fetch pipeline outcomes");
}
