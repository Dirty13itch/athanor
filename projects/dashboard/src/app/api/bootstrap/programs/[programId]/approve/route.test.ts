import { afterEach, describe, expect, it, vi } from "vitest";
import { NextResponse } from "next/server";

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
}));

import { POST } from "./route";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";

describe("bootstrap approve api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it("forwards POST requests to the canonical bootstrap approve path", async () => {
    const request = new Request("http://localhost/api/bootstrap/programs/launch-readiness-bootstrap/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ packet_id: "db_schema_change" }),
    });

    const response = await POST(request as never, {
      params: Promise.resolve({ programId: "launch-readiness-bootstrap" }),
    });

    expect(response.status).toBe(200);
    expect(proxyAgentOperatorJson).toHaveBeenCalledWith(
      request,
      "/v1/bootstrap/programs/launch-readiness-bootstrap/approve",
      "Failed to approve bootstrap packet",
      expect.objectContaining({
        privilegeClass: "admin",
        defaultReason: "Approved bootstrap packet from dashboard",
        timeoutMs: 60_000,
        bodyOverride: expect.objectContaining({
          packet_id: "db_schema_change",
          reason: "Approved bootstrap packet db_schema_change from dashboard",
        }),
      })
    );
  });

  it("treats already-approved packets as success when the live program is no longer waiting on approval", async () => {
    vi.mocked(proxyAgentOperatorJson).mockResolvedValueOnce(
      NextResponse.json({ error: "Upstream returned 400" }, { status: 400 })
    );
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            programs: [
              {
                id: "launch-readiness-bootstrap",
                next_action: {
                  kind: "dispatch",
                  family: "durable_persistence_activation",
                  slice_id: "persist-04-activation-cutover",
                },
                waiting_on_approval_family: "",
                waiting_on_approval_slice_id: "",
              },
            ],
            status: { approval_context: {} },
            takeover: { ready: false, blocker_ids: ["durable_persistence_live"] },
          }),
          { status: 200 }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            slices: [
              {
                id: "persist-04-activation-cutover",
                metadata: { approved_packets: ["db_schema_change"] },
              },
            ],
          }),
          { status: 200 }
        )
      );
    vi.stubGlobal("fetch", fetchMock);

    const request = new Request("http://localhost/api/bootstrap/programs/launch-readiness-bootstrap/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ packet_id: "db_schema_change" }),
    });

    const response = await POST(request as never, {
      params: Promise.resolve({ programId: "launch-readiness-bootstrap" }),
    });
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload.already_approved).toBe(true);
    expect(payload.approved_packet_id).toBe("db_schema_change");
    expect(payload.approved_slice_ids).toEqual(["persist-04-activation-cutover"]);
  });
});
