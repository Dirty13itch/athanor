import { NextResponse } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";

type OperatorReadFallback = Record<string, unknown> & {
  available?: boolean;
  degraded?: boolean;
  source?: string;
  detail?: string;
};

export async function proxyOperatorReadJson(
  path: string,
  errorMessage: string,
  fallback: OperatorReadFallback,
  timeoutMs?: number,
) {
  const response =
    timeoutMs === undefined
      ? await proxyAgentJson(path, undefined, errorMessage)
      : await proxyAgentJson(path, undefined, errorMessage, timeoutMs);

  if (response.status >= 500) {
    return NextResponse.json(
      {
        available: false,
        degraded: true,
        source: "agent-server",
        detail: errorMessage,
        ...fallback,
      },
      { status: 200 },
    );
  }

  return response;
}
