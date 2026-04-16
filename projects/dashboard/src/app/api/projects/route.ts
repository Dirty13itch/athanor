import { NextResponse } from "next/server";
import { getProjectsSnapshot } from "@/lib/dashboard-data";

export async function GET() {
  const snapshot = await getProjectsSnapshot();
  return NextResponse.json(snapshot);
}
