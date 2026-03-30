import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  const response = await proxyAgentJson(
    "/v1/improvement/summary",
    undefined,
    "Failed to fetch improvement summary"
  );
  if (response.status === 401 || response.status === 403) {
    return Response.json(
      {
        total_proposals: 0,
        pending: 0,
        validated: 0,
        deployed: 0,
        failed: 0,
        benchmark_results: 0,
        last_cycle: null,
      },
      { status: 200 }
    );
  }
  return response;
}
