import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.toString();
  const path = query ? `/v1/improvement/benchmarks/history?${query}` : "/v1/improvement/benchmarks/history";
  const response = await proxyAgentJson(path, undefined, "Failed to fetch benchmark history");
  if (response.status === 401 || response.status === 403) {
    return Response.json({ entries: [] }, { status: 200 });
  }
  return response;
}
