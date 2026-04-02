import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { GET, POST } from "./route";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { proxyAgentJson } from "@/lib/server-agent";

describe("operator inbox api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards inbox GET requests to the operator inbox upstream path", async () => {
    const response = await GET(new NextRequest("http://localhost/api/operator/inbox?status=new"));

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/inbox?status=new",
      undefined,
      "Failed to fetch operator inbox"
    );
  });

  it("forwards inbox POST requests through the operator action proxy", async () => {
    const request = new NextRequest("http://localhost/api/operator/inbox", {
      method: "POST",
      body: JSON.stringify({
        kind: "approval_request",
        title: "Review change",
      }),
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    expect(proxyAgentOperatorJson).toHaveBeenCalledOnce();
    const [, path, errorMessage, options] = vi.mocked(proxyAgentOperatorJson).mock.calls[0]!;
    expect(path).toBe("/v1/operator/inbox");
    expect(errorMessage).toBe("Failed to create operator inbox item");
    expect(options).toMatchObject({
      privilegeClass: "operator",
      defaultReason: "Created operator inbox item from dashboard",
    });
  });
});
