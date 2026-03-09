import { getServicesSnapshot } from "@/lib/dashboard-data";
import { NextResponse } from "next/server";

export async function GET() {
  const snapshot = await getServicesSnapshot();
  return NextResponse.json(snapshot);
}
