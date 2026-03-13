import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function GET() {
  return proxyAgentJson(
    "/v1/governor/operator-tests",
    undefined,
    "Failed to fetch operator-test snapshot"
  );
}

export async function POST(request: NextRequest) {
  const body = await request.text();
  return proxyAgentJson(
    "/v1/governor/operator-tests/run",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    },
    "Failed to run synthetic operator tests"
  );
}
