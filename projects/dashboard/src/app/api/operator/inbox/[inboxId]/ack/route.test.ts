import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

vi.mock("@/lib/builder-store", () => ({
  isBuilderSyntheticInboxId: vi.fn((id: string) => id.startsWith("builder-inbox-")),
  applyBuilderSyntheticInboxAction: vi.fn(async (id: string, action: string) => ({
    id,
    status: action === "ack" ? "acknowledged" : "new",
  })),
}));

import { POST } from "./route";
import { applyBuilderSyntheticInboxAction } from "@/lib/builder-store";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

describe("operator inbox ack route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("acknowledges local builder inbox items without proxying upstream", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/operator/inbox/builder-inbox-1/ack", {
        method: "POST",
      }),
      { params: Promise.resolve({ inboxId: "builder-inbox-1" }) },
    );

    await expect(response.json()).resolves.toMatchObject({
      ok: true,
      item: {
        id: "builder-inbox-1",
        status: "acknowledged",
      },
    });
    expect(applyBuilderSyntheticInboxAction).toHaveBeenCalledWith("builder-inbox-1", "ack");
    expect(proxyAgentOperatorJson).not.toHaveBeenCalled();
  });

  it("proxies non-builder inbox acknowledgements upstream", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/operator/inbox/agent-inbox-1/ack", {
        method: "POST",
      }),
      { params: Promise.resolve({ inboxId: "agent-inbox-1" }) },
    );

    expect(response.status).toBe(200);
    expect(proxyAgentOperatorJson).toHaveBeenCalledOnce();
  });
});
