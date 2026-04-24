import { NextResponse } from "next/server";
import { loadOperatorSummaryPayload } from "@/lib/operator-summary";

export async function GET() {
  return NextResponse.json(await loadOperatorSummaryPayload(), { status: 200 });
}
