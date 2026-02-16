import { config } from "@/lib/config";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const res = await fetch(`${config.vllm.url}${config.vllm.modelsEndpoint}`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return NextResponse.json({ models: [] });
    const data = await res.json();
    const models = data.data?.map((m: { id: string }) => m.id) ?? [];
    return NextResponse.json({ models });
  } catch {
    return NextResponse.json({ models: [] });
  }
}
