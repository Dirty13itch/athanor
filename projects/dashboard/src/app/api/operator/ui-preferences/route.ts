import { uiPreferencesSchema } from "@/lib/contracts";
import { requireOperatorMutationAccess } from "@/lib/operator-auth";
import { readUiPreferences, saveUiPreferences } from "./store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  return Response.json(await readUiPreferences());
}

export async function POST(request: Request) {
  const gate = requireOperatorMutationAccess(request);
  if (gate) {
    return gate;
  }

  try {
    const body = await request.json().catch(() => ({}));
    const parsed = uiPreferencesSchema.safeParse(body);
    if (!parsed.success) {
      return Response.json(
        { error: "Invalid UI preferences payload", issues: parsed.error.flatten() },
        { status: 400 }
      );
    }

    const snapshot = await saveUiPreferences(parsed.data);
    return Response.json({
      ok: true,
      ...snapshot,
    });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "Failed to save UI preferences" },
      { status: 500 }
    );
  }
}
