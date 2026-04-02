import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function POST(request: NextRequest, context: { params: Promise<{ sliceId: string }> }) {
  const { sliceId } = await context.params;
  const body = await request.json().catch(() => ({}));
  return proxyAgentOperatorJson(request, `/v1/bootstrap/slices/${encodeURIComponent(sliceId)}/claim`, "Failed to claim bootstrap slice", {
    privilegeClass: "admin",
    defaultReason: "Claimed bootstrap slice from dashboard",
    bodyOverride: {
      host_id: (body as { host_id?: unknown }).host_id ?? "",
      current_ref: (body as { current_ref?: unknown }).current_ref ?? "",
      worktree_path: (body as { worktree_path?: unknown }).worktree_path ?? "",
      files_touched: (body as { files_touched?: unknown }).files_touched ?? [],
      next_step: (body as { next_step?: unknown }).next_step ?? "",
      reason: (body as { reason?: unknown }).reason ?? "Claimed bootstrap slice from dashboard",
    },
  });
}
