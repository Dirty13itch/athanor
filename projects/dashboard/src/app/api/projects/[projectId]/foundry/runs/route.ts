import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { proxyAgentJson } from "@/lib/server-agent";

type Context = { params: Promise<{ projectId: string }> };

function getBodyRecord(body: unknown): Record<string, unknown> {
  return body && typeof body === "object" && !Array.isArray(body)
    ? (body as Record<string, unknown>)
    : {};
}

export async function GET(
  request: NextRequest,
  { params }: Context
) {
  const { projectId } = await params;
  const query = request.nextUrl.searchParams.toString();
  return proxyAgentJson(
    `/v1/projects/${encodeURIComponent(projectId)}/foundry/runs${query ? `?${query}` : ""}`,
    undefined,
    "Failed to fetch foundry runs"
  );
}

export async function POST(
  request: NextRequest,
  { params }: Context
) {
  const { projectId } = await params;
  const body = getBodyRecord(await request.json().catch(() => ({})));
  return proxyAgentOperatorJson(
    request,
    `/v1/projects/${encodeURIComponent(projectId)}/foundry/runs`,
    "Failed to record foundry run",
    {
      privilegeClass: "operator",
      defaultReason: `Recorded foundry run for ${projectId} from dashboard`,
      bodyOverride: {
        ...body,
        reason:
          typeof body.reason === "string" && body.reason.trim().length > 0
            ? body.reason
            : `Recorded foundry run for ${projectId} from dashboard`,
      },
    }
  );
}
