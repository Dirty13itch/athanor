import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function POST(request: NextRequest, context: { params: Promise<{ sliceId: string }> }) {
  const { sliceId } = await context.params;
  const body = await request.json().catch(() => ({}));
  return proxyAgentOperatorJson(request, `/v1/bootstrap/integrations/${encodeURIComponent(sliceId)}/replay`, "Failed to replay bootstrap integration", {
    privilegeClass: "admin",
    defaultReason: "Queued bootstrap integration replay from dashboard",
    bodyOverride: {
      method: (body as { method?: unknown }).method ?? "squash_commit",
      source_ref: (body as { source_ref?: unknown }).source_ref ?? "",
      target_ref: (body as { target_ref?: unknown }).target_ref ?? "main",
      patch_path: (body as { patch_path?: unknown }).patch_path ?? "",
      priority: (body as { priority?: unknown }).priority ?? 3,
      reason: (body as { reason?: unknown }).reason ?? "Queued bootstrap integration replay from dashboard",
    },
  });
}
