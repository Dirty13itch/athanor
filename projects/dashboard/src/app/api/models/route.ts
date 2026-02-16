import { config } from "@/lib/config";
import { NextResponse } from "next/server";

interface ModelEntry {
  id: string;
  backend: string;
  backendUrl: string;
}

export async function GET() {
  const results: ModelEntry[] = [];

  await Promise.all(
    config.inferenceBackends.map(async (backend) => {
      try {
        const res = await fetch(`${backend.url}/v1/models`, {
          signal: AbortSignal.timeout(5000),
        });
        if (!res.ok) return;
        const data = await res.json();
        const models = data.data ?? [];
        for (const m of models) {
          results.push({
            id: m.id,
            backend: backend.name,
            backendUrl: backend.url,
          });
        }
      } catch {
        // Backend unreachable — skip
      }
    })
  );

  return NextResponse.json({ models: results });
}
