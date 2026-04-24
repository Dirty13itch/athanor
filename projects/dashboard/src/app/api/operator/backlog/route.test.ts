import { NextRequest, NextResponse } from "next/server";
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

  it("forwards backlog GET requests to the canonical operator backlog path", async () => {
    const response = await GET(new NextRequest("http://localhost/api/operator/backlog?status=ready"));

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/backlog?status=ready",
      undefined,
      "Failed to fetch operator backlog"
    );
  });

  it("normalizes status=all so the upstream backlog path stays unfiltered", async () => {
    const response = await GET(
      new NextRequest("http://localhost/api/operator/backlog?status=all&limit=120"),
    );

    expect(response.status).toBe(200);
    expect(proxyAgentJson).toHaveBeenCalledWith(
      "/v1/operator/backlog?limit=120",
      undefined,
      "Failed to fetch operator backlog"
    );
  });

  it("fails soft when the operator backlog upstream is unavailable", async () => {
    vi.mocked(proxyAgentJson).mockResolvedValueOnce(
      NextResponse.json({ error: "upstream down" }, { status: 502 }),
    );

    const response = await GET(new NextRequest("http://localhost/api/operator/backlog?status=ready"));

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      available: false,
      degraded: true,
      backlog: [],
      count: 0,
    });
  });

  it("forwards canonical work-item fields when creating backlog items", async () => {
    const response = await POST(
      new NextRequest("http://localhost/api/operator/backlog", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          title: "Packet maintenance",
          prompt: "Refresh maintenance evidence.",
          owner_agent: "coding-agent",
          family: "maintenance",
          project_id: "kindred",
          source_type: "program_signal",
          source_ref: "project-packet:kindred:weekly",
          routing_class: "private_but_cloud_allowed",
          verification_contract: "maintenance_proof",
          closure_rule: "proof_or_review_required",
          materialization_source: "project_packet_cadence",
          materialization_reason: "Recurring maintenance signal emitted governed queue work.",
          recurrence_program_id: "weekly-kindred-maintenance",
          result_id: "",
          review_id: "",
        }),
      }),
    );

    expect(response.status).toBe(200);
    expect(proxyAgentOperatorJson).toHaveBeenCalledWith(
      expect.any(NextRequest),
      "/v1/operator/backlog",
      "Failed to create operator backlog item",
      expect.objectContaining({
        bodyOverride: expect.objectContaining({
          family: "maintenance",
          project_id: "kindred",
          source_type: "program_signal",
          source_ref: "project-packet:kindred:weekly",
          routing_class: "private_but_cloud_allowed",
          verification_contract: "maintenance_proof",
          closure_rule: "proof_or_review_required",
          materialization_source: "project_packet_cadence",
          materialization_reason: "Recurring maintenance signal emitted governed queue work.",
          recurrence_program_id: "weekly-kindred-maintenance",
        }),
      }),
    );
  });
});
