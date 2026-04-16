import { NextResponse } from "next/server";
import { getWorkforceSnapshot } from "@/lib/dashboard-data";

export async function GET() {
  const snapshot = await getWorkforceSnapshot();
  return NextResponse.json(snapshot);
}
