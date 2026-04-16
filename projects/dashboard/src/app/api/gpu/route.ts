import { NextResponse } from "next/server";
import { getGpuSnapshot } from "@/lib/dashboard-data";

export async function GET() {
  const snapshot = await getGpuSnapshot();
  return NextResponse.json(snapshot);
}
