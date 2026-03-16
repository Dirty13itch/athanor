import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ projectId: string }> }
) {
  const { projectId } = await params;
  return proxyAgentJson(
    `/v1/projects/${encodeURIComponent(projectId)}/state`,
    undefined,
    "Failed to fetch project state"
  );
}
