import { builderSessionControlRequestSchema } from "@/lib/contracts";
import { applyBuilderSessionControl } from "@/lib/builder-store";
import { requireOperatorMutationAccess } from "@/lib/operator-auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(
  request: Request,
  context: { params: Promise<{ sessionId: string }> },
) {
  const gate = requireOperatorMutationAccess(request);
  if (gate) {
    return gate;
  }

  try {
    const { sessionId } = await context.params;
    const body = await request.json().catch(() => ({}));
    const parsed = builderSessionControlRequestSchema.safeParse(body);
    if (!parsed.success) {
      return Response.json(
        { error: "Invalid builder control payload", issues: parsed.error.flatten() },
        { status: 400 },
      );
    }

    const result = await applyBuilderSessionControl(
      sessionId,
      parsed.data.action,
      parsed.data.approval_id ?? null,
    );
    return Response.json({ ok: true, ...result });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to update builder session";
    const status = message.includes("not found") || message.includes("Unknown builder session") ? 404 : 500;
    return Response.json({ error: message }, { status });
  }
}
