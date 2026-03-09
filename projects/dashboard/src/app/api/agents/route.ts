import { NextResponse } from "next/server";
import { getAgentsSnapshot } from "@/lib/dashboard-data";

export async function GET() {
  const snapshot = await getAgentsSnapshot();
  return NextResponse.json(snapshot);
}
