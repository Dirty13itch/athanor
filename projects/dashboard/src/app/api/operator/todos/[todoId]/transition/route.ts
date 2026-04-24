import { NextRequest, NextResponse } from "next/server";
import { applyBuilderSyntheticTodoTransition, isBuilderSyntheticTodoId } from "@/lib/builder-store";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ todoId: string }> }
) {
  const { todoId } = await params;
  const body = await request.json().catch(() => ({}));
  if (isBuilderSyntheticTodoId(todoId)) {
    const todo = await applyBuilderSyntheticTodoTransition(
      todoId,
      String((body as { status?: unknown }).status ?? "open") as
        | "open"
        | "ready"
        | "blocked"
        | "waiting"
        | "done"
        | "cancelled"
        | "someday",
      typeof (body as { note?: unknown }).note === "string" ? (body as { note?: string }).note : undefined,
    );
    return NextResponse.json({ ok: true, todo });
  }
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
