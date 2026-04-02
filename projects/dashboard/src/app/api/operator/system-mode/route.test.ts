import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { GET, POST } from "./route";
import { proxyAgentJson } from "@/lib/server-agent";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

describe("operator system-mode api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards system-mode GET requests to the canonical operator system mode path", async () => {
    const response = await GET();

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/system-mode",
      undefined,
      "Failed to fetch operator system mode"
    );
  });

  it("forwards system-mode POST requests through the operator action proxy", async () => {
    const request = new NextRequest("http://localhost/api/operator/system-mode", {
      method: "POST",
      body: JSON.stringify({ mode: "constrained", reason: "Attention breach" }),
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    const [, path, errorMessage, options] = vi.mocked(proxyAgentOperatorJson).mock.calls[0]!;
    expect(path).toBe("/v1/operator/system-mode");
    expect(errorMessage).toBe("Failed to update operator system mode");
    expect(options).toMatchObject({
      privilegeClass: "admin",
      defaultReason: "Updated operator system mode from dashboard",
    });
  });
});
