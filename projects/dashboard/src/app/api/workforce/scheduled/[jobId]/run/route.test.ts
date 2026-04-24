import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { POST } from "./route";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

describe("scheduled job run api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards scheduled run requests through the operator action proxy", async () => {
    const request = new NextRequest("http://localhost/api/workforce/scheduled/agent-schedule:coding-agent/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ force: true }),
    });

    const response = await POST(request, {
      params: Promise.resolve({ jobId: "agent-schedule:coding-agent" }),
    });

    expect(response.status).toBe(200);
    expect(proxyAgentOperatorJson).toHaveBeenCalledWith(
      request,
      "/v1/tasks/scheduled/agent-schedule%3Acoding-agent/run",
      "Failed to run scheduled job",
      expect.objectContaining({
        privilegeClass: "admin",
        defaultReason: "Triggered scheduled job agent-schedule:coding-agent from dashboard",
      })
    );
  });
});
