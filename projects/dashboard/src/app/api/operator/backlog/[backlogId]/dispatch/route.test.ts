import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { POST } from "./route";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

describe("operator backlog dispatch api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards backlog dispatches through the operator action proxy", async () => {
    const request = new NextRequest("http://localhost/api/operator/backlog/backlog-1/dispatch", {
      method: "POST",
      body: JSON.stringify({}),
    });

    const response = await POST(request, { params: Promise.resolve({ backlogId: "backlog-1" }) });

    expect(response.status).toBe(200);
    const [, path, errorMessage] = vi.mocked(proxyAgentOperatorJson).mock.calls[0]!;
    expect(path).toBe("/v1/operator/backlog/backlog-1/dispatch");
    expect(errorMessage).toBe("Failed to dispatch operator backlog item");
  });
});
