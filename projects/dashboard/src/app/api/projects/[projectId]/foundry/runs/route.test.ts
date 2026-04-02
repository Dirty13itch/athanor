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

describe("foundry runs api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards foundry run GET requests to the upstream path", async () => {
    const response = await GET(
      new NextRequest("http://localhost/api/projects/athanor/foundry/runs?limit=5"),
      { params: Promise.resolve({ projectId: "athanor" }) }
    );

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/projects/athanor/foundry/runs?limit=5",
      undefined,
      "Failed to fetch foundry runs"
    );
  });

  it("forwards foundry run POST requests through the operator action proxy", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/projects/athanor/foundry/runs", {
        method: "POST",
        body: JSON.stringify({ summary: "Recorded run" }),
      }),
      { params: Promise.resolve({ projectId: "athanor" }) }
    );

    expect(response.status).toBe(200);
    const [, path, errorMessage, options] = vi.mocked(proxyAgentOperatorJson).mock.calls[0]!;
    expect(path).toBe("/v1/projects/athanor/foundry/runs");
    expect(errorMessage).toBe("Failed to record foundry run");
    expect(options).toMatchObject({
      privilegeClass: "operator",
      defaultReason: "Recorded foundry run for athanor from dashboard",
    });
  });
});
