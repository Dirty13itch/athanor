import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  queryPrometheus: vi.fn(async () => []),
}));

vi.mock("@/lib/config", () => ({
  agentServerHeaders: () => ({ Authorization: "Bearer test" }),
  config: {
    agentServer: {
      url: "http://agent",
    },
    gpuWorkloads: {},
  },
  getNodeNameFromInstance: (instance: string) => instance.split(":")[0] || "unknown",
}));

import { GET } from "./route";

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("stream api route", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "setInterval").mockImplementation((() => 1) as unknown as typeof setInterval);
    vi.spyOn(globalThis, "setTimeout").mockImplementation((() => 1) as unknown as typeof setTimeout);
    vi.spyOn(globalThis, "clearInterval").mockImplementation((() => undefined) as unknown as typeof clearInterval);
    vi.spyOn(globalThis, "clearTimeout").mockImplementation((() => undefined) as unknown as typeof clearTimeout);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("streams canonical task residue from operator summary tasks instead of run totals", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url === "http://agent/health") {
        return jsonResponse({ agents: ["coding-agent"] });
      }
      if (url === "http://agent/v1/status/services") {
        return jsonResponse({ services: [{ name: "redis", status: "up" }] });
      }
      if (url === "http://agent/v1/operator/summary") {
        return jsonResponse({
          runs: {
            total: 999,
            by_status: {
              completed: 999,
              failed: 999,
              running: 999,
              queued: 999,
            },
          },
          tasks: {
            total: 332,
            completed: 138,
            failed: 153,
            running: 0,
            pending: 0,
            pending_approval: 13,
            stale_lease: 21,
            failed_actionable: 72,
            failed_historical_repaired: 81,
            failed_missing_detail: 0,
          },
          inbox: {
            total: 0,
            by_status: {
              new: 0,
              acknowledged: 0,
              snoozed: 0,
            },
          },
          approvals: {
            total: 13,
            by_status: {
              pending: 13,
            },
          },
        });
      }
      if (url === "http://agent/v1/status/media") {
        return jsonResponse({ streamCount: 0, downloads: [], sessions: [] });
      }
      throw new Error(`unexpected fetch ${url}`);
    });

    const response = await GET();

    expect(response.status).toBe(200);
    expect(response.headers.get("Content-Type")).toBe("text/event-stream");

    const reader = response.body?.getReader();
    expect(reader).toBeTruthy();
    const firstChunk = await reader!.read();
    const text = new TextDecoder().decode(firstChunk.value);
    const firstEvent = text.split("\n\n")[0]?.replace(/^data:\s*/, "") ?? "";
    const payload = JSON.parse(firstEvent) as Record<string, unknown>;

    expect(payload.tasks).toMatchObject({
      total: 332,
      failed: 153,
      pending_approval: 13,
      stale_lease: 21,
      failed_actionable: 72,
      failed_historical_repaired: 81,
    });
    await reader!.cancel();
  });
});
