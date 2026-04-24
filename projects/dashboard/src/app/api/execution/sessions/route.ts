import { NextRequest, NextResponse } from "next/server";
import { loadExecutionSessions } from "@/lib/executive-kernel";

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const sessions = await loadExecutionSessions({
    status: params.get("status"),
    family: params.get("family"),
  });

  return NextResponse.json({
    sessions,
    count: sessions.length,
  });
}
