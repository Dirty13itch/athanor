import { readBuilderSession } from "@/lib/builder-store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ sessionId: string }> },
) {
  const { sessionId } = await context.params;
  const session = await readBuilderSession(sessionId);
  if (!session) {
    return Response.json({ error: "Builder session not found" }, { status: 404 });
  }

  return Response.json(session);
}
