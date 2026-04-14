import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/config", () => ({
  agentServerHeaders: vi.fn(() => ({ Authorization: "Bearer test-token" })),
  config: {
    agentServer: {
      url: "http://agent-server.test",
    },
  },
  joinUrl: vi.fn((base: string, path: string) => `${base}${path}`),
}));

import { GET } from "./route";

describe("operator stream api route", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("maps canonical events query payloads into operator-stream events", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          events: [
            {
              event_type: "task_failed",
              agent: "coding-agent",
              description: "Task abc failed",
              timestamp: "2026-04-12T21:00:00Z",
              data: {
                task_id: "task-abc",
                run_id: "run-123",
              },
            },
          ],
        }),
        { status: 200 }
      ) as unknown as Response
    );

    const request = new Request("http://localhost/api/activity/operator-stream?limit=8");
    const response = await GET(request as never);

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({
      events: [
        {
          id: "task-abc",
          timestamp: "2026-04-12T21:00:00Z",
          severity: "error",
          subsystem: "tasks",
          event_type: "task_failed",
          subject: "coding-agent",
          summary: "Task abc failed",
          deep_link: "/operator",
          related_run_id: "run-123",
        },
      ],
    });
  });

  it("degrades to an empty stream when the upstream request fails", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("boom"));

    const request = new Request("http://localhost/api/activity/operator-stream");
    const response = await GET(request as never);

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ events: [] });
  });
});
