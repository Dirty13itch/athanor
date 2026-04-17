import { builderTaskEnvelopeSchema } from "@/lib/contracts";
import { createBuilderSession } from "@/lib/builder-store";
import { requireOperatorMutationAccess } from "@/lib/operator-auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const gate = requireOperatorMutationAccess(request);
  if (gate) {
    return gate;
  }

  try {
    const body = await request.json().catch(() => ({}));
    const parsed = builderTaskEnvelopeSchema.safeParse(body);
    if (!parsed.success) {
      return Response.json(
        { error: "Invalid builder task envelope", issues: parsed.error.flatten() },
        { status: 400 },
      );
    }

    const session = await createBuilderSession(parsed.data);
    return Response.json({ ok: true, session }, { status: 201 });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "Failed to create builder session" },
      { status: 500 },
    );
  }
}
