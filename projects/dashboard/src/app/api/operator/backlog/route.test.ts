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

describe("operator backlog api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards backlog GET requests to the operator backlog upstream path", async () => {
    const response = await GET(new NextRequest("http://localhost/api/operator/backlog?status=ready"));

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/backlog?status=ready",
      undefined,
      "Failed to fetch operator backlog"
    );
  });

  it("forwards backlog POST requests through the operator action proxy", async () => {
    const request = new NextRequest("http://localhost/api/operator/backlog", {
      method: "POST",
      body: JSON.stringify({ title: "Task", prompt: "Do the thing", owner_agent: "coding-agent" }),
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    const [, path, errorMessage, options] = vi.mocked(proxyAgentOperatorJson).mock.calls[0]!;
    expect(path).toBe("/v1/operator/backlog");
    expect(errorMessage).toBe("Failed to create operator backlog item");
    expect(options).toMatchObject({
      privilegeClass: "operator",
      defaultReason: "Created operator backlog item from dashboard",
    });
  });
});
