import { NextRequest } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

export async function POST(request: NextRequest) {
  const body = await request.text();
  return proxyAgentJson(
    "/v1/feedback",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    },
    "Failed to send feedback"
  );
}
