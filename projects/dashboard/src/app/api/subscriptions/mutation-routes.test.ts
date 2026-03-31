import { NextRequest, NextResponse } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

type RouteDeps = {
  gate: ReturnType<typeof vi.fn>;
  proxyAgentJson: ReturnType<typeof vi.fn>;
  proxyAgentOperatorJson: ReturnType<typeof vi.fn>;
};

function mockRouteDeps(gateResponse: Response | null = null): RouteDeps {
  const gate = vi.fn().mockReturnValue(gateResponse);
  const proxyAgentJson = vi.fn();
  const proxyAgentOperatorJson = vi
    .fn()
    .mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));

  vi.doMock("@/lib/operator-auth", () => ({
    requireOperatorMutationAccess: gate,
  }));
  vi.doMock("@/lib/operator-actions", () => ({
    proxyAgentOperatorJson,
  }));
  vi.doMock("@/lib/server-agent", () => ({
    proxyAgentJson,
  }));

  return { gate, proxyAgentJson, proxyAgentOperatorJson };
}

async function loadExecutionRoute(gateResponse: Response | null = null) {
  vi.resetModules();
  const deps = mockRouteDeps(gateResponse);
  const route = await import("./execution/route");
  return { ...route, ...deps };
}

async function loadHandoffsRoute(gateResponse: Response | null = null) {
  vi.resetModules();
  const deps = mockRouteDeps(gateResponse);
  const route = await import("./handoffs/route");
  return { ...route, ...deps };
}

async function loadOutcomeRoute(gateResponse: Response | null = null) {
  vi.resetModules();
  const deps = mockRouteDeps(gateResponse);
  const route = await import("./handoffs/[handoffId]/outcome/route");
  return { ...route, ...deps };
}

async function loadLeasesRoute(gateResponse: Response | null = null) {
  vi.resetModules();
  const deps = mockRouteDeps(gateResponse);
  const route = await import("./leases/route");
  return { ...route, ...deps };
}

afterEach(() => {
  vi.doUnmock("@/lib/operator-auth");
  vi.doUnmock("@/lib/operator-actions");
  vi.doUnmock("@/lib/server-agent");
  vi.restoreAllMocks();
  vi.resetModules();
});

describe("subscription mutation routes", () => {
  it("denies execution writes without operator access", async () => {
    const denied = NextResponse.json({ error: "forbidden" }, { status: 403 });
    const { POST, gate, proxyAgentOperatorJson } = await loadExecutionRoute(denied);
    const request = new NextRequest("http://localhost/api/subscriptions/execution", {
      method: "POST",
      body: JSON.stringify({ provider_id: "deepseek_api" }),
    });

    const response = await POST(request);

    expect(response.status).toBe(403);
    expect(gate).toHaveBeenCalledWith(request);
    expect(proxyAgentOperatorJson).not.toHaveBeenCalled();
  });

  it("forwards execution writes through the shared operator envelope", async () => {
    const { POST, gate, proxyAgentOperatorJson } = await loadExecutionRoute();
    const request = new NextRequest("http://localhost/api/subscriptions/execution", {
      method: "POST",
      body: JSON.stringify({ provider_id: "deepseek_api" }),
    });

    await POST(request);

    expect(gate).toHaveBeenCalledWith(request);
    expect(proxyAgentOperatorJson).toHaveBeenCalledWith(
      request,
      "/v1/subscriptions/execution",
      "Failed to execute provider request",
      {
        privilegeClass: "admin",
        defaultActor: "dashboard-operator",
        defaultReason: "Executed provider request",
        timeoutMs: 120_000,
      }
    );
  });

  it("denies handoff creation without operator access", async () => {
    const denied = NextResponse.json({ error: "forbidden" }, { status: 403 });
    const { POST, gate, proxyAgentOperatorJson } = await loadHandoffsRoute(denied);
    const request = new NextRequest("http://localhost/api/subscriptions/handoffs", {
      method: "POST",
      body: JSON.stringify({ provider_id: "moonshot_api" }),
    });

    const response = await POST(request);

    expect(response.status).toBe(403);
    expect(gate).toHaveBeenCalledWith(request);
    expect(proxyAgentOperatorJson).not.toHaveBeenCalled();
  });

  it("forwards handoff creation through the shared operator envelope", async () => {
    const { POST, gate, proxyAgentOperatorJson } = await loadHandoffsRoute();
    const request = new NextRequest("http://localhost/api/subscriptions/handoffs", {
      method: "POST",
      body: JSON.stringify({ provider_id: "moonshot_api" }),
    });

    await POST(request);

    expect(gate).toHaveBeenCalledWith(request);
    expect(proxyAgentOperatorJson).toHaveBeenCalledWith(
      request,
      "/v1/subscriptions/handoffs",
      "Failed to create subscription handoff",
      {
        privilegeClass: "operator",
        defaultActor: "dashboard-operator",
        defaultReason: "Created provider handoff bundle",
        timeoutMs: 30_000,
      }
    );
  });

  it("denies handoff outcomes without operator access", async () => {
    const denied = NextResponse.json({ error: "forbidden" }, { status: 403 });
    const { POST, gate, proxyAgentOperatorJson } = await loadOutcomeRoute(denied);
    const request = new NextRequest("http://localhost/api/subscriptions/handoffs/h1/outcome", {
      method: "POST",
      body: JSON.stringify({ outcome: "accepted" }),
    });

    const response = await POST(request, { params: Promise.resolve({ handoffId: "handoff-1" }) });

    expect(response.status).toBe(403);
    expect(gate).toHaveBeenCalledWith(request);
    expect(proxyAgentOperatorJson).not.toHaveBeenCalled();
  });

  it("forwards handoff outcomes through the shared operator envelope", async () => {
    const { POST, gate, proxyAgentOperatorJson } = await loadOutcomeRoute();
    const request = new NextRequest("http://localhost/api/subscriptions/handoffs/h1/outcome", {
      method: "POST",
      body: JSON.stringify({ outcome: "accepted" }),
    });

    await POST(request, { params: Promise.resolve({ handoffId: "handoff 1" }) });

    expect(gate).toHaveBeenCalledWith(request);
    expect(proxyAgentOperatorJson).toHaveBeenCalledWith(
      request,
      "/v1/subscriptions/handoffs/handoff%201/outcome",
      "Failed to record handoff outcome",
      {
        privilegeClass: "admin",
        defaultActor: "dashboard-operator",
        defaultReason: "Recorded provider handoff outcome",
        timeoutMs: 30_000,
      }
    );
  });

  it("denies lease requests without operator access", async () => {
    const denied = NextResponse.json({ error: "forbidden" }, { status: 403 });
    const { POST, gate, proxyAgentOperatorJson } = await loadLeasesRoute(denied);
    const request = new NextRequest("http://localhost/api/subscriptions/leases", {
      method: "POST",
      body: JSON.stringify({ provider_id: "openai_codex" }),
    });

    const response = await POST(request);

    expect(response.status).toBe(403);
    expect(gate).toHaveBeenCalledWith(request);
    expect(proxyAgentOperatorJson).not.toHaveBeenCalled();
  });

  it("forwards lease requests through the shared operator envelope", async () => {
    const { POST, gate, proxyAgentOperatorJson } = await loadLeasesRoute();
    const request = new NextRequest("http://localhost/api/subscriptions/leases", {
      method: "POST",
      body: JSON.stringify({ provider_id: "openai_codex" }),
    });

    await POST(request);

    expect(gate).toHaveBeenCalledWith(request);
    expect(proxyAgentOperatorJson).toHaveBeenCalledWith(
      request,
      "/v1/subscriptions/leases",
      "Failed to request subscription lease",
      {
        privilegeClass: "operator",
        defaultActor: "dashboard-operator",
        defaultReason: "Issued provider execution lease",
      }
    );
  });
});
