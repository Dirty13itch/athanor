import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

type Context = { params: Promise<{ ideaId: string }> };

export async function POST(request: NextRequest, context: Context) {
  const { ideaId } = await context.params;
  const body = await request.json().catch(() => ({}));
  return proxyAgentOperatorJson(request, `/v1/operator/ideas/${encodeURIComponent(ideaId)}/promote`, "Failed to promote operator idea", {
    privilegeClass: "operator",
    defaultReason: "Promoted operator idea from dashboard",
    bodyOverride: {
      target: (body as { target?: unknown }).target ?? "backlog",
      owner_agent: (body as { owner_agent?: unknown }).owner_agent ?? "coding-agent",
      project_id: (body as { project_id?: unknown }).project_id ?? "",
      reason: (body as { reason?: unknown }).reason ?? "Promoted operator idea from dashboard",
    },
  });
}
