import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

type Context = { params: Promise<{ projectId: string }> };

function getBodyRecord(body: unknown): Record<string, unknown> {
  return body && typeof body === "object" && !Array.isArray(body)
    ? (body as Record<string, unknown>)
    : {};
}

export async function POST(request: NextRequest, { params }: Context) {
  const { projectId } = await params;
  const body = getBodyRecord(await request.json().catch(() => ({})));
  return proxyAgentOperatorJson(
    request,
    `/v1/projects/${encodeURIComponent(projectId)}/rollback`,
    "Failed to roll back deploy candidate",
    {
      privilegeClass: "destructive-admin",
      defaultReason: `Rolled back deploy candidate for ${projectId} from dashboard`,
      bodyOverride: {
        ...body,
        protected_mode: true,
        reason:
          typeof body.reason === "string" && body.reason.trim().length > 0
            ? body.reason
            : `Rolled back deploy candidate for ${projectId} from dashboard`,
      },
    }
  );
}
