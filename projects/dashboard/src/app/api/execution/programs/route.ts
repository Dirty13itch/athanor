import { NextRequest, NextResponse } from "next/server";
import { loadExecutionPrograms } from "@/lib/executive-kernel";

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const programs = await loadExecutionPrograms({
    status: params.get("status"),
    family: params.get("family"),
  });

  return NextResponse.json({
    programs,
    count: programs.length,
  });
}
