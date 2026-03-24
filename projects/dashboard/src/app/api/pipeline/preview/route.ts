import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson("/v1/pipeline/preview", undefined, "Failed to fetch pipeline preview", 30_000);
}

export async function POST(request: NextRequest) {
  const body = await request.text();
  return proxyAgentJson(
    "/v1/pipeline/preview/approve",
    { method: "POST", headers: { "Content-Type": "application/json" }, body },
    "Failed to approve preview",
    30_000
  );
}
