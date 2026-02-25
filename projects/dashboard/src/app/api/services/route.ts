import { config } from "@/lib/config";
import { NextResponse } from "next/server";

interface ServiceResult {
  name: string;
  node: string;
  url: string;
  healthy: boolean;
  latencyMs: number | null;
}

async function checkService(service: {
  name: string;
  url: string;
  node: string;
  headers?: Record<string, string>;
}): Promise<ServiceResult> {
  const start = Date.now();
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    const res = await fetch(service.url, {
      signal: controller.signal,
      ...(service.headers && { headers: service.headers }),
    });
    clearTimeout(timeout);
    return {
      ...service,
      healthy: res.ok,
      latencyMs: Date.now() - start,
    };
  } catch {
    return {
      ...service,
      healthy: false,
      latencyMs: null,
    };
  }
}

export async function GET() {
  const results = await Promise.all(config.services.map(checkService));
  return NextResponse.json(results);
}
