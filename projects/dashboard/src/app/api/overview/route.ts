import { NextResponse } from "next/server";
import { getOverviewSnapshot } from "@/lib/dashboard-data";

export async function GET() {
  const snapshot = await getOverviewSnapshot();
  return NextResponse.json(snapshot);
}
