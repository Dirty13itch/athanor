import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

type Context = { params: Promise<{ projectId: string }> };

function getBodyRecord(body: unknown): Record<string, unknown> {
  return body && typeof body === "object" && !Array.isArray(body)
    ? (body as Record<string, unknown>)
    : {};
}

export async function POST(
  request: NextRequest,
  { params }: Context
) {
  const { projectId } = await params;
  const body = getBodyRecord(await request.json().catch(() => ({})));
  return proxyAgentOperatorJson(
    request,
    `/v1/projects/${encodeURIComponent(projectId)}/promote`,
    "Failed to promote deploy candidate",
    {
      privilegeClass: "admin",
      defaultReason: `Promoted deploy candidate for ${projectId} from dashboard`,
      bodyOverride: {
        ...body,
        reason:
          typeof body.reason === "string" && body.reason.trim().length > 0
            ? body.reason
            : `Promoted deploy candidate for ${projectId} from dashboard`,
      },
    }
  );
}
