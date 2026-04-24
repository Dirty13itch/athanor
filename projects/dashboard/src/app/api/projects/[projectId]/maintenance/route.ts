import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { proxyAgentJson } from "@/lib/server-agent";

type Context = { params: Promise<{ projectId: string }> };

function getBodyRecord(body: unknown): Record<string, unknown> {
  return body && typeof body === "object" && !Array.isArray(body)
    ? (body as Record<string, unknown>)
    : {};
}

function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

export async function GET(request: NextRequest, { params }: Context) {
  const { projectId } = await params;
  const query = request.nextUrl.searchParams.toString();
  return proxyAgentJson(
    `/v1/projects/${encodeURIComponent(projectId)}/maintenance${query ? `?${query}` : ""}`,
    undefined,
    "Failed to fetch maintenance runs"
  );
}

export async function POST(request: NextRequest, { params }: Context) {
  const { projectId } = await params;
  const body = getBodyRecord(await request.json().catch(() => ({})));
  const recurrenceProgramId = text(body.recurrence_program_id);
  const kind = text(body.kind) || "maintenance";
  const trigger = text(body.trigger) || "manual";
  const sourceRef =
    text(body.source_ref) ||
    (recurrenceProgramId
      ? `maintenance:${projectId}:program:${recurrenceProgramId}`
      : `maintenance:${projectId}:kind:${kind}:trigger:${trigger}`);
  return proxyAgentOperatorJson(
    request,
    `/v1/projects/${encodeURIComponent(projectId)}/maintenance`,
    "Failed to record maintenance run",
    {
      privilegeClass: "operator",
      defaultReason: `Recorded maintenance run for ${projectId} from dashboard`,
      bodyOverride: {
        ...body,
        trigger,
        materialize_backlog:
          typeof body.materialize_backlog === "boolean" ? body.materialize_backlog : true,
        source_ref: sourceRef,
        reason:
          typeof body.reason === "string" && body.reason.trim().length > 0
            ? body.reason
            : `Recorded maintenance run for ${projectId} from dashboard`,
      },
    }
  );
}
