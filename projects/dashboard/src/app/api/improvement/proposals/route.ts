import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  const response = await proxyAgentJson(
    "/v1/improvement/proposals",
    undefined,
    "Failed to fetch improvement proposals"
  );
  if (response.status === 401 || response.status === 403) {
    return Response.json({ proposals: [] }, { status: 200 });
  }
  return response;
}
