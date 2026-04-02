import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function POST(request: NextRequest, context: { params: Promise<{ sliceId: string }> }) {
  const { sliceId } = await context.params;
  const body = await request.json().catch(() => ({}));
  return proxyAgentOperatorJson(request, `/v1/bootstrap/slices/${encodeURIComponent(sliceId)}/complete`, "Failed to complete bootstrap slice", {
    privilegeClass: "admin",
    defaultReason: "Completed bootstrap slice from dashboard",
    bodyOverride: {
      host_id: (body as { host_id?: unknown }).host_id ?? "",
      current_ref: (body as { current_ref?: unknown }).current_ref ?? "",
      worktree_path: (body as { worktree_path?: unknown }).worktree_path ?? "",
      files_touched: (body as { files_touched?: unknown }).files_touched ?? [],
      validation_status: (body as { validation_status?: unknown }).validation_status ?? "passed",
      open_risks: (body as { open_risks?: unknown }).open_risks ?? [],
      next_step: (body as { next_step?: unknown }).next_step ?? "",
      summary: (body as { summary?: unknown }).summary ?? "",
      integration_method: (body as { integration_method?: unknown }).integration_method ?? "squash_commit",
      target_ref: (body as { target_ref?: unknown }).target_ref ?? "main",
      queue_priority: (body as { queue_priority?: unknown }).queue_priority ?? 3,
      reason: (body as { reason?: unknown }).reason ?? "Completed bootstrap slice from dashboard",
    },
  });
}
