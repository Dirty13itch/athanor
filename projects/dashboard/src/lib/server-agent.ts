import { NextResponse } from "next/server";
import { config, joinUrl } from "@/lib/config";
import { isDashboardFixtureMode } from "@/lib/dashboard-fixtures";

function parseFixtureBody(body: BodyInit | null | undefined) {
  if (typeof body !== "string") {
    return null;
  }

  try {
    return JSON.parse(body) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function buildFixtureAgentResponse(path: string, init: RequestInit | undefined) {
  const method = (init?.method ?? "GET").toUpperCase();
  const payload = parseFixtureBody(init?.body);
  const timestamp = new Date().toISOString();

  if (method === "POST" && path === "/v1/patterns/run") {
    return { ok: true, fixture: true, queued: true, runId: "fixture-pattern-run", timestamp };
  }

  if (method === "POST" && path === "/v1/improvement/benchmarks/run") {
    return { ok: true, fixture: true, queued: true, runId: "fixture-benchmark-run", timestamp };
  }

  if (method === "POST" && path === "/v1/preferences") {
    return {
      ok: true,
      fixture: true,
      saved: true,
      timestamp,
      preference: {
        agentId: typeof payload?.agent === "string" ? payload.agent : "global",
        signalType: typeof payload?.signal_type === "string" ? payload.signal_type : "remember_this",
        content: typeof payload?.content === "string" ? payload.content : "",
        category: typeof payload?.category === "string" ? payload.category : null,
      },
    };
  }

  if (method === "POST" && /\/v1\/tasks\/[^/]+\/approve$/.test(path)) {
    return { ok: true, fixture: true, approved: true, taskId: path.split("/").at(-2), timestamp };
  }

  if (method === "POST" && /\/v1\/tasks\/[^/]+\/cancel$/.test(path)) {
    return { ok: true, fixture: true, canceled: true, taskId: path.split("/").at(-2), timestamp };
  }

  if (method === "POST" && /\/v1\/workspace\/[^/]+\/endorse$/.test(path)) {
    return { ok: true, fixture: true, endorsed: true, itemId: path.split("/").at(-2), timestamp };
  }

  if (method === "POST" && /\/v1\/notifications\/[^/]+\/resolve$/.test(path)) {
    return { ok: true, fixture: true, resolved: true, notificationId: path.split("/").at(-2), timestamp };
  }

  if (method === "POST" && /\/v1\/conventions\/[^/]+\/(confirm|reject)$/.test(path)) {
    return {
      ok: true,
      fixture: true,
      action: path.endsWith("/confirm") ? "confirm" : "reject",
      conventionId: path.split("/").at(-2),
      timestamp,
    };
  }

  if (["POST", "PATCH", "PUT", "DELETE"].includes(method)) {
    return { ok: true, fixture: true, path, method, timestamp };
  }

  return null;
}

export async function proxyAgentJson(
  path: string,
  init: RequestInit | undefined,
  errorMessage: string,
  timeoutMs = 10_000
) {
  if (isDashboardFixtureMode()) {
    const fixtureResponse = buildFixtureAgentResponse(path, init);
    if (fixtureResponse) {
      return NextResponse.json(fixtureResponse);
    }
  }

  try {
    const response = await fetch(joinUrl(config.agentServer.url, path), {
      ...init,
      signal: init?.signal ?? AbortSignal.timeout(timeoutMs),
    });

    if (!response.ok) {
      return NextResponse.json({ error: `Upstream returned ${response.status}` }, { status: response.status });
    }

    const text = await response.text();
    return NextResponse.json(text ? JSON.parse(text) : { ok: true });
  } catch {
    return NextResponse.json({ error: errorMessage }, { status: 502 });
  }
}
