import { NextRequest, NextResponse } from "next/server";
import { getGpuHistory } from "@/lib/dashboard-data";
import { isTimeWindow } from "@/lib/ranges";

export async function GET(request: NextRequest) {
  const window = request.nextUrl.searchParams.get("window");
  const snapshot = await getGpuHistory(isTimeWindow(window) ? window : "3h");
  return NextResponse.json(snapshot);
}
