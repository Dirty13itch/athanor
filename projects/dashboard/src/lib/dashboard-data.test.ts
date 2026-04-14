import { afterEach, describe, expect, it, vi } from "vitest";

import { __testing } from "./dashboard-data";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("dashboard service health normalization", () => {
  it("treats model catalog responses as healthy service probes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ data: [{ id: "dolphin3-r1-24b" }] }), {
          status: 200,
          headers: { "content-type": "application/json" },
        })
      )
    );

    const snapshot = await __testing.checkService({
      id: "foundry-coder",
      name: "Foundry Coder",
      nodeId: "node1",
      node: "Foundry",
      category: "inference",
      description: "Autonomous dolphin coding runtime on the 4090 lane.",
      url: "http://192.168.1.244:8100/v1/models",
    });

    expect(snapshot.healthy).toBe(true);
    expect(snapshot.state).toBe("healthy");
    expect(snapshot.lastError).toBeNull();
  });

  it("treats configured pass-through probe endpoints as healthy on 200 responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("Prometheus is Healthy.", {
          status: 200,
          headers: { "content-type": "text/plain" },
        })
      )
    );

    const snapshot = await __testing.checkService({
      id: "prometheus",
      name: "Prometheus",
      nodeId: "vault",
      node: "VAULT",
      category: "observability",
      description: "Metrics and scrape surface.",
      url: "http://192.168.1.203:9090/-/healthy",
    });

    expect(snapshot.healthy).toBe(true);
    expect(snapshot.state).toBe("healthy");
    expect(snapshot.lastError).toBeNull();
  });

  it("treats ComfyUI as healthy when Workshop answers on its own runtime contract", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ system: { comfyui_version: "0.18.1" } }), {
          status: 200,
          headers: { "content-type": "application/json" },
        })
      )
    );

    const snapshot = await __testing.checkService({
      id: "comfyui",
      name: "ComfyUI",
      nodeId: "node2",
      node: "Workshop",
      category: "experience",
      description: "Creative workflow runtime.",
      url: "http://192.168.1.225:8188/system_stats",
    });

    expect(snapshot.healthy).toBe(true);
    expect(snapshot.state).toBe("healthy");
    expect(snapshot.lastError).toBeNull();
  });

  it("treats Workshop Open WebUI as healthy when the UI responds without the shared contract", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("<html><body>Open WebUI</body></html>", {
          status: 200,
          headers: { "content-type": "text/html" },
        })
      )
    );

    const snapshot = await __testing.checkService({
      id: "workshop-open-webui",
      name: "Workshop Open WebUI",
      nodeId: "node2",
      node: "Workshop",
      category: "experience",
      description: "Direct local chat surface for raw model access.",
      url: "http://192.168.1.225:3000",
    });

    expect(snapshot.healthy).toBe(true);
    expect(snapshot.state).toBe("healthy");
    expect(snapshot.lastError).toBeNull();
  });

  it("passes configured auth headers to service probes", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("ok", {
        status: 200,
        headers: { "content-type": "text/plain" },
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    await __testing.checkService({
      id: "home-assistant",
      name: "Home Assistant",
      nodeId: "vault",
      node: "VAULT",
      category: "home",
      description: "Smart-home control plane and automation state.",
      url: "http://192.168.1.203:8123/api/",
      headers: { Authorization: "Bearer test-token" },
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://192.168.1.203:8123/api/",
      expect.objectContaining({
        headers: { Authorization: "Bearer test-token" },
      })
    );
  });

  it("treats auth-guarded pass-through services as warning instead of contract drift", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("401: Unauthorized", {
          status: 401,
          headers: { "content-type": "text/plain" },
        })
      )
    );

    const snapshot = await __testing.checkService({
      id: "home-assistant",
      name: "Home Assistant",
      nodeId: "vault",
      node: "VAULT",
      category: "home",
      description: "Smart-home control plane and automation state.",
      url: "http://192.168.1.203:8123/api/",
    });

    expect(snapshot.healthy).toBe(true);
    expect(snapshot.state).toBe("warning");
    expect(snapshot.lastError).toBe("Service is reachable but requires auth for the health probe.");
  });

  it("preserves fetch failures as degraded probe detail", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connect ECONNREFUSED 192.168.1.189:8001")));

    const snapshot = await __testing.checkService({
      id: "dev-embedding",
      name: "DEV Embedding",
      nodeId: "dev",
      node: "DEV",
      category: "knowledge",
      description: "Embedding runtime for retrieval, indexing, and semantic search.",
      url: "http://192.168.1.189:8001/v1/models",
    });

    expect(snapshot.healthy).toBe(false);
    expect(snapshot.state).toBe("degraded");
    expect(snapshot.lastError).toContain("ECONNREFUSED");
  });

  it("normalizes aborts into explicit timeout detail", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new DOMException("This operation was aborted", "AbortError")));

    const snapshot = await __testing.checkService({
      id: "comfyui",
      name: "ComfyUI",
      nodeId: "node2",
      node: "Workshop",
      category: "experience",
      description: "Creative workflow runtime.",
      url: "http://192.168.1.225:8188/system_stats",
      probeTimeoutMs: 7000,
    });

    expect(snapshot.healthy).toBe(false);
    expect(snapshot.state).toBe("degraded");
    expect(snapshot.lastError).toBe("Probe timed out after 7000ms");
  });

  it("uses service-specific probe timeouts when provided", async () => {
    const setTimeoutSpy = vi.spyOn(globalThis, "setTimeout");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ data: [{ id: "general-assistant" }] }), {
          status: 200,
          headers: { "content-type": "application/json" },
        })
      )
    );

    const snapshot = await __testing.checkService({
      id: "agent-server",
      name: "Agent Server",
      nodeId: "node1",
      node: "Foundry",
      category: "platform",
      description: "FastAPI runtime for the Athanor workforce and task APIs.",
      url: "http://192.168.1.244:9000/health",
      probeTimeoutMs: 10000,
    });

    expect(snapshot.healthy).toBe(true);
    expect(setTimeoutSpy.mock.calls[0]?.[1]).toBe(10000);
  });
});
