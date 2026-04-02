import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

type Context = { params: Promise<{ programId: string }> };

export async function POST(request: NextRequest, context: Context) {
  const { programId } = await context.params;
  const body = await request.json().catch(() => ({}));
  return proxyAgentOperatorJson(
    request,
    `/v1/bootstrap/programs/${encodeURIComponent(programId)}/nudge`,
    "Failed to nudge bootstrap program",
    {
      privilegeClass: "admin",
      defaultReason: "Nudged bootstrap supervisor from dashboard",
      bodyOverride: {
        execute: (body as { execute?: unknown }).execute ?? false,
        retry_blockers: (body as { retry_blockers?: unknown }).retry_blockers ?? true,
        process_integrations: (body as { process_integrations?: unknown }).process_integrations ?? true,
        reason: (body as { reason?: unknown }).reason ?? "Nudged bootstrap supervisor from dashboard",
      },
    }
  );
}
