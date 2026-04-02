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

describe("operator ideas api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards ideas GET requests to the operator ideas upstream path", async () => {
    const response = await GET(new NextRequest("http://localhost/api/operator/ideas?status=candidate"));

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/ideas?status=candidate",
      undefined,
      "Failed to fetch operator ideas"
    );
  });

  it("forwards idea POST requests through the operator action proxy", async () => {
    const request = new NextRequest("http://localhost/api/operator/ideas", {
      method: "POST",
      body: JSON.stringify({ title: "New idea", note: "Capture it" }),
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    const [, path, errorMessage, options] = vi.mocked(proxyAgentOperatorJson).mock.calls[0]!;
    expect(path).toBe("/v1/operator/ideas");
    expect(errorMessage).toBe("Failed to create operator idea");
    expect(options).toMatchObject({
      privilegeClass: "operator",
      defaultReason: "Created operator idea from dashboard",
    });
  });
});
