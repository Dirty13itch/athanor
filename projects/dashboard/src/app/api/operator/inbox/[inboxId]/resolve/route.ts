import { NextRequest, NextResponse } from "next/server";
import { applyBuilderSyntheticInboxAction, isBuilderSyntheticInboxId } from "@/lib/builder-store";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ inboxId: string }> }
) {
  const { inboxId } = await params;
  const body = await request.json().catch(() => ({}));
  if (isBuilderSyntheticInboxId(inboxId)) {
    const item = await applyBuilderSyntheticInboxAction(inboxId, "resolve");
    return NextResponse.json({ ok: true, item, note: (body as { note?: unknown }).note ?? "" });
  }
  return proxyAgentOperatorJson(
    request,
    `/v1/operator/inbox/${encodeURIComponent(inboxId)}/resolve`,
    "Failed to resolve inbox item",
    {
      privilegeClass: "operator",
      defaultReason: `Resolved inbox item ${inboxId} from dashboard`,
      bodyOverride: {
        note: (body as { note?: unknown }).note ?? "",
        reason: (body as { reason?: unknown }).reason ?? `Resolved inbox item ${inboxId} from dashboard`,
      },
    }
  );
}
