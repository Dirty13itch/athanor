import { NextResponse } from "next/server";
import { isDockerAvailable, restartContainer } from "@/lib/docker";

const PROTECTED_CONTAINERS = new Set([
  "athanor-dashboard", // don't restart yourself
]);

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ name: string }> }
) {
  const { name } = await params;

  if (!isDockerAvailable()) {
    return NextResponse.json(
      { error: "Docker socket not available" },
      { status: 503 }
    );
  }

  if (PROTECTED_CONTAINERS.has(name)) {
    return NextResponse.json(
      { error: `Container "${name}" is protected and cannot be restarted from the dashboard` },
      { status: 403 }
    );
  }

  try {
    await restartContainer(name);
    return NextResponse.json({ ok: true, container: name, action: "restart" });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Restart failed" },
      { status: 500 }
    );
  }
}
