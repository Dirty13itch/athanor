import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const query = new URL(request.url).searchParams.toString();
  return proxyAgentJson(`/v1/bootstrap/handoffs${query ? `?${query}` : ""}`, undefined, "Failed to fetch bootstrap handoffs");
}
