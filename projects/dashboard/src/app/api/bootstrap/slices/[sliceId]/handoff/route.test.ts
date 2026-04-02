import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { POST } from "./route";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

describe("bootstrap handoff mutation route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards POST requests through the canonical operator-action proxy", async () => {
    const request = new Request("http://localhost/api/bootstrap/slices/slice-1/handoff", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        from_host: "codex_external",
        to_host: "claude_external",
        stop_reason: "context_exhausted",
        reason: "Relay from test",
      }),
    });

    const response = await POST(request as never, { params: Promise.resolve({ sliceId: "slice-1" }) });

    expect(response.status).toBe(200);
    expect(proxyAgentOperatorJson).toHaveBeenCalledWith(
      request,
      "/v1/bootstrap/slices/slice-1/handoff",
      "Failed to hand off bootstrap slice",
      expect.objectContaining({
        privilegeClass: "admin",
        defaultReason: "Handed off bootstrap slice from dashboard",
      })
    );
  });
});
