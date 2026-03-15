import { NextResponse, type NextRequest } from "next/server";
import { isDockerAvailable, getContainerLogs } from "@/lib/docker";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  const { name } = await params;
  const tail = Number(request.nextUrl.searchParams.get("tail") ?? "100");

  if (!isDockerAvailable()) {
    return NextResponse.json(
      { error: "Docker socket not available" },
      { status: 503 }
    );
  }

  try {
    const logs = await getContainerLogs(name, Math.min(tail, 500));
    return NextResponse.json({ container: name, logs });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Failed to fetch logs" },
      { status: 500 }
    );
  }
}
