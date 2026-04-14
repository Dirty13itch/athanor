import { NextRequest, NextResponse } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi
    .fn()
    .mockResolvedValue(NextResponse.json({ status: "ok" })),
}));

import { POST } from "./route";
import { GET, HEAD } from "./route";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

describe("governor heartbeat api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards heartbeat posts through the shared operator envelope", async () => {
    const request = new NextRequest("http://localhost/api/governor/heartbeat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        actor: "dashboard-heartbeat",
        state: "at_desk",
        source: "dashboard_heartbeat",
        reason: "Visible dashboard heartbeat",
      }),
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    expect(proxyAgentOperatorJson).toHaveBeenCalledWith(
      request,
      "/v1/governor/heartbeat",
      "Failed to update operator heartbeat",
      {
        privilegeClass: "operator",
        defaultActor: "dashboard-heartbeat",
        defaultReason: "Dashboard heartbeat acknowledgement",
      },
    );
  });

  it("fails soft when the upstream heartbeat path is temporarily unavailable", async () => {
    vi.mocked(proxyAgentOperatorJson).mockResolvedValueOnce(
      NextResponse.json({ error: "upstream down" }, { status: 502 }),
    );

    const request = new NextRequest("http://localhost/api/governor/heartbeat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        actor: "dashboard-heartbeat",
        state: "away",
        source: "dashboard_heartbeat",
        reason: "Dashboard hidden",
      }),
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      status: "degraded",
      source: "dashboard_heartbeat",
    });
  });

  it("fails soft when the proxy layer throws while posting heartbeat", async () => {
    vi.mocked(proxyAgentOperatorJson).mockRejectedValueOnce(new Error("proxy unavailable"));

    const request = new NextRequest("http://localhost/api/governor/heartbeat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        actor: "dashboard-heartbeat",
        state: "at_desk",
        source: "dashboard_heartbeat",
        reason: "Dashboard visible",
      }),
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      status: "degraded",
      source: "dashboard_heartbeat",
    });
  });

  it("returns a degraded transparency response for GET probes", async () => {
    const response = await GET();

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      status: "degraded",
      source: "dashboard_heartbeat",
    });
  });

  it("returns a lightweight 200 for HEAD probes", async () => {
    const response = await HEAD();

    expect(response.status).toBe(200);
    expect(response.body).toBeNull();
  });
});
