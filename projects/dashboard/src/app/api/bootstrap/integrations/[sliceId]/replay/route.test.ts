import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { POST } from "./route";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

describe("bootstrap integration replay route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards POST requests through the canonical operator-action proxy", async () => {
    const request = new Request("http://localhost/api/bootstrap/integrations/slice-1/replay", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ method: "squash_commit", reason: "Replay from test" }),
    });

    const response = await POST(request as never, { params: Promise.resolve({ sliceId: "slice-1" }) });

    expect(response.status).toBe(200);
    expect(proxyAgentOperatorJson).toHaveBeenCalledWith(
      request,
      "/v1/bootstrap/integrations/slice-1/replay",
      "Failed to replay bootstrap integration",
      expect.objectContaining({
        privilegeClass: "admin",
        defaultReason: "Queued bootstrap integration replay from dashboard",
      })
    );
  });
});
