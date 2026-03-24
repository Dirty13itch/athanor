import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ projectId: string }> }
) {
  const { projectId } = await params;
  return proxyAgentJson(
    `/v1/projects/${encodeURIComponent(projectId)}/advance`,
    { method: "POST" },
    "Failed to advance project",
    15_000
  );
}
