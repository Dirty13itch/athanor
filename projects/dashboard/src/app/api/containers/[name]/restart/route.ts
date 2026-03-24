import { NextResponse, type NextRequest } from "next/server";
import { restartContainer } from "@/lib/docker";

const PROTECTED_CONTAINERS = new Set([
  "athanor-dashboard", // don't restart yourself
]);

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  const { name } = await params;
  const node = request.nextUrl.searchParams.get("node") ?? "workshop";

  if (node === "foundry") {
    return NextResponse.json(
      { error: "FOUNDRY is production — restart not allowed from dashboard" },
      { status: 403 }
    );
  }

  if (node === "workshop" && PROTECTED_CONTAINERS.has(name)) {
    return NextResponse.json(
      { error: `Container "${name}" is protected and cannot be restarted from the dashboard` },
      { status: 403 }
    );
  }

  try {
    await restartContainer(node, name);
    return NextResponse.json({ ok: true, container: name, node, action: "restart" });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Restart failed";
    const status = message.includes("not allowed") ? 403 : 500;
    return NextResponse.json({ error: message }, { status });
  }
}
