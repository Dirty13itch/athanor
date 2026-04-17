import { readBuilderSessionEvents } from "@/lib/builder-store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ sessionId: string }> },
) {
  const { sessionId } = await context.params;
  const payload = await readBuilderSessionEvents(sessionId);
  if (!payload) {
    return Response.json({ error: "Builder session not found" }, { status: 404 });
  }

  return Response.json(payload);
}
