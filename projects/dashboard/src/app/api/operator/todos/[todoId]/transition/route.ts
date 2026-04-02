import { NextRequest } from "next/server";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ todoId: string }> }
) {
  const { todoId } = await params;
  const body = await request.json().catch(() => ({}));
  return proxyAgentOperatorJson(
    request,
    `/v1/operator/todos/${encodeURIComponent(todoId)}/transition`,
    "Failed to update operator todo",
    {
      privilegeClass: "operator",
      defaultReason: `Updated operator todo ${todoId} from dashboard`,
      bodyOverride: {
        status: (body as { status?: unknown }).status ?? "",
        note: (body as { note?: unknown }).note ?? "",
        reason: (body as { reason?: unknown }).reason ?? `Updated operator todo ${todoId} from dashboard`,
      },
    }
  );
}
