import { NextResponse, type NextRequest } from "next/server";
import { getContainerLogs } from "@/lib/docker";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  const { name } = await params;
  const node = request.nextUrl.searchParams.get("node") ?? "workshop";
  const tail = Number(request.nextUrl.searchParams.get("tail") ?? "100");

  try {
    const logs = await getContainerLogs(node, name, Math.min(tail, 500));
    return NextResponse.json({ container: name, node, logs });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Failed to fetch logs" },
      { status: 500 }
    );
  }
}
