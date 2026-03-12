import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function POST(
  _request: NextRequest,
  context: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await context.params;
  return proxyAgentJson(
    `/v1/research/jobs/${encodeURIComponent(jobId)}/execute`,
    { method: "POST" },
    "Failed to execute research job"
  );
}
