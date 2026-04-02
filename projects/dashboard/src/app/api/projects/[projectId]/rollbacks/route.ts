import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

type Context = { params: Promise<{ projectId: string }> };

export async function GET(request: NextRequest, { params }: Context) {
  const { projectId } = await params;
  const query = request.nextUrl.searchParams.toString();
  return proxyAgentJson(
    `/v1/projects/${encodeURIComponent(projectId)}/rollbacks${query ? `?${query}` : ""}`,
    undefined,
    "Failed to fetch rollback events"
  );
}
