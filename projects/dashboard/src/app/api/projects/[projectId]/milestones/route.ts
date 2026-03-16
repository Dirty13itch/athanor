import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ projectId: string }> }
) {
  const { projectId } = await params;
  return proxyAgentJson(
    `/v1/projects/${encodeURIComponent(projectId)}/milestones`,
    undefined,
    "Failed to fetch milestones"
  );
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ projectId: string }> }
) {
  const { projectId } = await params;
  const body = await request.json();
  return proxyAgentJson(
    `/v1/projects/${encodeURIComponent(projectId)}/milestones`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
    "Failed to create milestone",
    15_000
  );
}
