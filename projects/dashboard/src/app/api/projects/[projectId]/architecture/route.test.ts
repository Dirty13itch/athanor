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

describe("project architecture api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards architecture GET requests to the foundry architecture upstream path", async () => {
    const response = await GET(new NextRequest("http://localhost/api/projects/athanor/architecture"), {
      params: Promise.resolve({ projectId: "athanor" }),
    });

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/projects/athanor/architecture",
      undefined,
      "Failed to fetch project architecture"
    );
  });

  it("forwards architecture POST requests through the operator action proxy", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/projects/athanor/architecture", {
        method: "POST",
        body: JSON.stringify({ service_shape: { kind: "nextjs" } }),
      }),
      { params: Promise.resolve({ projectId: "athanor" }) }
    );

    expect(response.status).toBe(200);
    const [, path, errorMessage, options] = vi.mocked(proxyAgentOperatorJson).mock.calls[0]!;
    expect(path).toBe("/v1/projects/athanor/architecture");
    expect(errorMessage).toBe("Failed to update project architecture");
    expect(options).toMatchObject({
      privilegeClass: "admin",
      defaultReason: "Updated project architecture for athanor from dashboard",
    });
  });
});
