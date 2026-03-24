import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const status = request.nextUrl.searchParams.get("status") ?? "pending";
  return proxyAgentJson(`/v1/plans?status=${status}`, undefined, "Failed to fetch plans");
}
