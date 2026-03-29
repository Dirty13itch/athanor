import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

interface ChatRouteOptions {
  resolvedTarget?: { url: string } | null;
  resolvedModel?: string;
  litellmBackend?: { url: string } | null;
  headerResult?: { headers: Record<string, string>; error?: string };
  litellmApiKey?: string;
}

async function loadRoute(options: ChatRouteOptions = {}) {
  const {
    resolvedTarget = { url: "https://backend.example" },
    resolvedModel = "reasoning-model",
    litellmBackend = { url: "https://litellm.example" },
    headerResult = {
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer sk-test",
      },
    },
    litellmApiKey = "sk-test",
  } = options;

  vi.resetModules();
  vi.doMock("@/lib/config", () => ({
    joinUrl: (base: string, path: string) => `${base}${path}`,
    resolveChatTarget: () => resolvedTarget,
    resolveChatModel: () => resolvedModel,
    getInferenceBackend: (target: string) => (target === "litellm-proxy" ? litellmBackend : null),
    agentServerHeaders: () => ({ Authorization: "Bearer agent-token" }),
  }));
  vi.doMock("@/lib/chat-proxy", () => ({
    buildChatUpstreamHeaders: () => headerResult,
  }));
  vi.doMock("@/lib/server-config", () => ({
    serverConfig: {
      litellmApiKey,
    },
  }));

  return import("./route");
}

function buildSseResponse(blocks: string[]) {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const block of blocks) {
        controller.enqueue(encoder.encode(block));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

function parseSseEvents(body: string) {
  return body
    .split("\n\n")
    .map((block) =>
      block
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart())
        .join("\n")
    )
    .filter((payload) => payload.length > 0 && payload !== "[DONE]")
    .map((payload) => JSON.parse(payload) as Record<string, unknown>);
}

describe("POST /api/chat", () => {
  afterEach(() => {
    vi.doUnmock("@/lib/config");
    vi.doUnmock("@/lib/chat-proxy");
    vi.doUnmock("@/lib/server-config");
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    vi.resetModules();
  });

  it("returns 400 for an invalid request body", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const { POST } = await loadRoute();
    const response = await POST(
      new NextRequest("http://127.0.0.1:3001/api/chat", {
        method: "POST",
        body: JSON.stringify({ messages: "invalid" }),
      })
    );

    expect(response.status).toBe(400);
    await expect(response.text()).resolves.toBe("Invalid request");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns 400 for an unknown target", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const { POST } = await loadRoute({ resolvedTarget: null });
    const response = await POST(
      new NextRequest("http://127.0.0.1:3001/api/chat", {
        method: "POST",
        body: JSON.stringify({ messages: [], target: "ghost-target" }),
      })
    );

    expect(response.status).toBe(400);
    await expect(response.text()).resolves.toBe("Unknown chat target");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns 503 when upstream auth headers cannot be built", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const { POST } = await loadRoute({
      headerResult: {
        headers: { "Content-Type": "application/json" },
        error: "ATHANOR_LITELLM_API_KEY is required for LiteLLM chat target",
      },
    });
    const response = await POST(
      new NextRequest("http://127.0.0.1:3001/api/chat", {
        method: "POST",
        body: JSON.stringify({ messages: [], target: "litellm-proxy" }),
      })
    );

    expect(response.status).toBe(503);
    await expect(response.text()).resolves.toBe(
      "ATHANOR_LITELLM_API_KEY is required for LiteLLM chat target"
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns 502 when the upstream backend is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connect ECONNREFUSED")));

    const { POST } = await loadRoute();
    const response = await POST(
      new NextRequest("http://127.0.0.1:3001/api/chat", {
        method: "POST",
        body: JSON.stringify({
          messages: [{ role: "system", content: "stay concise" }],
          target: "foundry-coordinator",
        }),
      })
    );

    expect(response.status).toBe(502);
    await expect(response.text()).resolves.toBe("Unable to reach upstream chat backend");
  });

  it("normalizes upstream SSE events and applies sovereign override routing", async () => {
    let upstreamBody = "";
    const fetchMock = vi.fn(async (input: string | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "http://localhost:8740/classify") {
        return new Response(
          JSON.stringify({
            classification: "adult",
            category: "creative",
            confidence: 0.97,
            route: "sovereign",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }

      upstreamBody = String(init?.body ?? "");
      if (url === "https://litellm.example/v1/chat/completions") {
        return buildSseResponse([
          'event: tool_start\ndata: {"type":"tool_start","name":"web_search","args":{"query":"operator memory"}}\n\n',
          'data: {"choices":[{"delta":{"content":"Sovereign reply"}}]}\n\n',
          'event: tool_end\ndata: {"type":"tool_end","name":"web_search","result":"done","duration_ms":12}\n\n',
          "data: [DONE]\n\n",
        ]);
      }

      throw new Error(`Unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { POST } = await loadRoute({
      resolvedTarget: { url: "https://foundry.example" },
      resolvedModel: "qwen-coder",
      litellmBackend: { url: "https://litellm.example" },
    });
    const response = await POST(
      new NextRequest("http://127.0.0.1:3001/api/chat", {
        method: "POST",
        body: JSON.stringify({
          target: "foundry-coordinator",
          model: "qwen-coder",
          threadId: "thread-1",
          messages: [{ role: "user", content: "Need uncensored operator memory help" }],
        }),
      })
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("Content-Type")).toBe("text/event-stream");

    const events = parseSseEvents(await response.text());
    expect(events[0]).toMatchObject({
      type: "classification",
      route: "sovereign",
      sovereignOverride: true,
      resolvedModel: "uncensored",
    });
    expect(events).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          type: "tool_start",
          name: "web_search",
          args: { query: "operator memory" },
        }),
        expect.objectContaining({
          type: "assistant_delta",
          content: "Sovereign reply",
        }),
        expect.objectContaining({
          type: "tool_end",
          name: "web_search",
          output: "done",
          durationMs: 12,
        }),
        expect.objectContaining({
          type: "done",
          finishReason: "stop",
        }),
      ])
    );

    const upstreamPayload = JSON.parse(upstreamBody) as Record<string, unknown>;
    expect(upstreamPayload).toMatchObject({
      model: "uncensored",
      stream: true,
      chat_template_kwargs: { enable_thinking: false },
    });
    expect(upstreamPayload).not.toHaveProperty("thread_id");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("forwards the configured agent-server bearer token for agent chat", async () => {
    let upstreamHeaders: HeadersInit | undefined;
    const fetchMock = vi.fn(async (input: string | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "https://backend.example/v1/chat/completions") {
        upstreamHeaders = init?.headers;
        return buildSseResponse([
          'data: {"choices":[{"delta":{"content":"OK"}}]}\n\n',
          "data: [DONE]\n\n",
        ]);
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { POST } = await loadRoute();
    const response = await POST(
      new NextRequest("http://127.0.0.1:3001/api/chat", {
        method: "POST",
        body: JSON.stringify({
          target: "agent-server",
          threadId: "live-smoke-thread",
          messages: [{ role: "user", content: "Reply with OK only." }],
        }),
      })
    );

    expect(response.status).toBe(200);
    expect(upstreamHeaders).toMatchObject({
      Authorization: "Bearer agent-token",
      "Content-Type": "application/json",
    });
  });
});
