import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.toString();
  const path = query ? `/v1/review/judges?${query}` : "/v1/review/judges";
  return proxyAgentJson(path, undefined, "Failed to fetch judge-plane snapshot");
}
