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

describe("operator todos api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards todos GET requests to the operator todos upstream path", async () => {
    const response = await GET(new NextRequest("http://localhost/api/operator/todos?status=ready"));

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/todos?status=ready",
      undefined,
      "Failed to fetch operator todos"
    );
  });

  it("forwards todo POST requests through the operator action proxy", async () => {
    const request = new NextRequest("http://localhost/api/operator/todos", {
      method: "POST",
      body: JSON.stringify({
        title: "Follow up",
        description: "Capture detail",
      }),
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    expect(proxyAgentOperatorJson).toHaveBeenCalledOnce();
    const [, path, errorMessage, options] = vi.mocked(proxyAgentOperatorJson).mock.calls[0]!;
    expect(path).toBe("/v1/operator/todos");
    expect(errorMessage).toBe("Failed to create operator todo");
    expect(options).toMatchObject({
      privilegeClass: "operator",
      defaultReason: "Created operator todo from dashboard",
    });
  });
});
