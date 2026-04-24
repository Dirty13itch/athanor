import { NextRequest, NextResponse } from "next/server";
import { applyBuilderSyntheticInboxAction, isBuilderSyntheticInboxId } from "@/lib/builder-store";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ inboxId: string }> }
) {
  const { inboxId } = await params;
  if (isBuilderSyntheticInboxId(inboxId)) {
    const item = await applyBuilderSyntheticInboxAction(inboxId, "ack");
    return NextResponse.json({ ok: true, item });
  }
  return proxyAgentOperatorJson(
    request,
    `/v1/operator/inbox/${encodeURIComponent(inboxId)}/ack`,
    "Failed to acknowledge inbox item",
    {
      privilegeClass: "operator",
      defaultReason: `Acknowledged inbox item ${inboxId} from dashboard`,
      bodyOverride: {
        reason: `Acknowledged inbox item ${inboxId} from dashboard`,
      },
    }
  );
}
