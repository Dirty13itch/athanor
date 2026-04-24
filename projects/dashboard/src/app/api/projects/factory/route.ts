import { NextResponse } from "next/server";
import { loadProjectFactorySnapshot } from "@/lib/project-factory";

export async function GET() {
  return NextResponse.json(await loadProjectFactorySnapshot(), { status: 200 });
}
