import { NextResponse } from "next/server";
import { loadOperatorMobileSummary } from "@/lib/operator-mobile-summary";

export async function GET() {
  return NextResponse.json(await loadOperatorMobileSummary(), { status: 200 });
}
