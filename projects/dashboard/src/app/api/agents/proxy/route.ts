import { NextRequest, NextResponse } from "next/server";
import { proxyAgentJson } from "@/lib/server-agent";
import { requireOperatorMutationAccess, requireOperatorSessionAccess } from "@/lib/operator-auth";

function getValidatedAgentProxyPath(request: NextRequest): string | NextResponse {
  const path = request.nextUrl.searchParams.get("path")?.trim();
  if (!path) {
    return NextResponse.json({ error: "Missing path parameter" }, { status: 400 });
  }

  if (!path.startsWith("/")) {
    return NextResponse.json({ error: "Proxy path must be absolute" }, { status: 400 });
  }

  if (!(path === "/health" || path.startsWith("/v1/"))) {
    return NextResponse.json({ error: "Unsupported agent proxy path" }, { status: 400 });
  }

  return path;
}

export async function GET(request: NextRequest) {
  const gate = requireOperatorSessionAccess(request);
  if (gate) {
    return gate;
  }

  const path = getValidatedAgentProxyPath(request);
  if (path instanceof NextResponse) {
    return path;
  }

  return proxyAgentJson(path, undefined, "Agent server request failed");
}

export async function POST(request: NextRequest) {
  const gate = requireOperatorMutationAccess(request);
  if (gate) {
    return gate;
  }

  const path = getValidatedAgentProxyPath(request);
  if (path instanceof NextResponse) {
    return path;
  }

  const contentType = request.headers.get("content-type") ?? "";
  const hasBody = contentType.includes("application/json");
  return proxyAgentJson(
    path,
    {
      method: "POST",
      headers: hasBody ? { "Content-Type": "application/json" } : undefined,
      body: hasBody ? await request.text() : undefined,
    },
    "Agent server request failed"
  );
}
