import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

type Context = {
  params: Promise<{ programId: string }>;
};

export async function POST(request: NextRequest, context: Context) {
  const { programId } = await context.params;
  const body = await request.json().catch(() => ({}));
  return proxyAgentOperatorJson(request, `/v1/bootstrap/programs/${encodeURIComponent(programId)}/promote`, "Failed to promote bootstrap program", {
    privilegeClass: "admin",
    defaultReason: "Promoted bootstrap program from dashboard",
    bodyOverride: {
      reason: (body as { reason?: unknown }).reason ?? "Promoted bootstrap program from dashboard",
      force: (body as { force?: unknown }).force ?? false,
    },
  });
}
