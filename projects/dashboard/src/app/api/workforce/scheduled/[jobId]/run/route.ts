import { proxyAgentJson } from "@/lib/server-agent";

export async function POST(
  request: Request,
  context: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await context.params;
  const body = await request.text();
  return proxyAgentJson(
    `/v1/tasks/scheduled/${encodeURIComponent(jobId)}/run`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body || JSON.stringify({ actor: "dashboard-operator" }),
    },
    "Failed to run scheduled job"
  );
}
