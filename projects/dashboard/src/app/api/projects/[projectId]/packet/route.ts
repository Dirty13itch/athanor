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
  _request: NextRequest,
  { params }: Context
) {
  const { projectId } = await params;
  return proxyAgentJson(
    `/v1/projects/${encodeURIComponent(projectId)}/packet`,
    undefined,
    "Failed to fetch project packet"
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
    `/v1/projects/${encodeURIComponent(projectId)}/packet`,
    "Failed to update project packet",
    {
      privilegeClass: "admin",
      defaultReason: `Updated project packet for ${projectId} from dashboard`,
      bodyOverride: {
        ...body,
        reason:
          typeof body.reason === "string" && body.reason.trim().length > 0
            ? body.reason
            : `Updated project packet for ${projectId} from dashboard`,
      },
    }
  );
}
