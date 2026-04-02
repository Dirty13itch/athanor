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

describe("project maintenance api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards maintenance GET requests to the upstream path", async () => {
    const response = await GET(
      new NextRequest("http://localhost/api/projects/athanor/maintenance?limit=10"),
      { params: Promise.resolve({ projectId: "athanor" }) }
    );

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/projects/athanor/maintenance?limit=10",
      undefined,
      "Failed to fetch maintenance runs"
    );
  });

  it("forwards maintenance POST requests through the operator action proxy", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/projects/athanor/maintenance", {
        method: "POST",
        body: JSON.stringify({ kind: "smoke" }),
      }),
      { params: Promise.resolve({ projectId: "athanor" }) }
    );

    expect(response.status).toBe(200);
    const [, path, errorMessage, options] = vi.mocked(proxyAgentOperatorJson).mock.calls[0]!;
    expect(path).toBe("/v1/projects/athanor/maintenance");
    expect(errorMessage).toBe("Failed to record maintenance run");
    expect(options).toMatchObject({
      privilegeClass: "operator",
      defaultReason: "Recorded maintenance run for athanor from dashboard",
    });
  });
});
