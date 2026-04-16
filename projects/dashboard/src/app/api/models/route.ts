import { NextResponse } from "next/server";
import { getModelsSnapshot } from "@/lib/dashboard-data";

export async function GET() {
  const snapshot = await getModelsSnapshot();
  return NextResponse.json(snapshot);
}
