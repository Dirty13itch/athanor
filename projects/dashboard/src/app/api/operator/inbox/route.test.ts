import { NextRequest, NextResponse } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/server-agent", () => ({
  proxyAgentJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

vi.mock("@/lib/builder-store", () => ({
  listBuilderSyntheticInboxItems: vi.fn(async () => [
    {
      id: "builder-inbox-1",
      kind: "approval_request",
      severity: 3,
      status: "new",
      source: "builder",
      title: "Approve builder route",
      description: "Builder session is waiting for operator approval.",
      requires_decision: true,
      decision_type: "approve",
      related_run_id: "builder-run-1",
      related_task_id: "builder-1",
      snooze_until: 0,
      created_at: 100,
      updated_at: 100,
      resolved_at: 0,
      metadata: { builder_session_id: "builder-1" },
    },
  ]),
}));

import { GET, POST } from "./route";
import { listBuilderSyntheticInboxItems } from "@/lib/builder-store";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { proxyAgentJson } from "@/lib/server-agent";

describe("operator inbox api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards inbox GET requests to the operator inbox upstream path", async () => {
    vi.mocked(proxyAgentJson).mockResolvedValueOnce(
      NextResponse.json({ items: [{ id: "agent-inbox-1", status: "new", created_at: 90, updated_at: 90 }], count: 1 }, {
        status: 200,
      }),
    );
    const response = await GET(new NextRequest("http://localhost/api/operator/inbox?status=new"));
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/inbox?status=new",
      undefined,
      "Failed to fetch operator inbox"
    );
    expect(listBuilderSyntheticInboxItems).toHaveBeenCalledWith("new");
    expect(payload.count).toBe(2);
    expect(payload.items[0]?.id).toBe("builder-inbox-1");
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
