import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const params = new URLSearchParams(request.nextUrl.searchParams);
  return proxyAgentJson(`/v1/tasks/runs?${params.toString()}`, undefined, "Failed to fetch execution runs");
}
