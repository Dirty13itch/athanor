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

describe("project deployments api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards deployment GET requests to the upstream path", async () => {
    const response = await GET(
      new NextRequest("http://localhost/api/projects/athanor/deployments?limit=10"),
      { params: Promise.resolve({ projectId: "athanor" }) }
    );

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/projects/athanor/deployments?limit=10",
      undefined,
      "Failed to fetch deploy candidates"
    );
  });

  it("forwards deployment POST requests through the operator action proxy", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/projects/athanor/deployments", {
        method: "POST",
        body: JSON.stringify({ channel: "public_staging" }),
      }),
      { params: Promise.resolve({ projectId: "athanor" }) }
    );

    expect(response.status).toBe(200);
    const [, path, errorMessage, options] = vi.mocked(proxyAgentOperatorJson).mock.calls[0]!;
    expect(path).toBe("/v1/projects/athanor/deployments");
    expect(errorMessage).toBe("Failed to record deploy candidate");
    expect(options).toMatchObject({
      privilegeClass: "admin",
      defaultReason: "Recorded deploy candidate for athanor from dashboard",
    });
  });
});
