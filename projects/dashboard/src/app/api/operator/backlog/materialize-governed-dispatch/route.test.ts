import { NextRequest, NextResponse } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/master-atlas", () => ({
  readGeneratedMasterAtlas: vi.fn(),
}));

vi.mock("@/lib/operator-actions", () => ({
  proxyAgentOperatorJson: vi.fn(),
}));

vi.mock("@/lib/operator-auth", () => ({
  requireSameOriginOperatorSessionAccess: vi.fn(),
}));

import { POST } from "./route";
import { readGeneratedMasterAtlas } from "@/lib/master-atlas";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { requireSameOriginOperatorSessionAccess } from "@/lib/operator-auth";

describe("materialize governed dispatch backlog api route", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    vi.mocked(requireSameOriginOperatorSessionAccess).mockReturnValue(null);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("returns 409 when no governed dispatch claim is available", async () => {
    vi.mocked(readGeneratedMasterAtlas).mockResolvedValue({
      governed_dispatch_state: null,
    });

    const response = await POST(
      new NextRequest("http://localhost/api/operator/backlog/materialize-governed-dispatch", {
        method: "POST",
      })
    );

    expect(response.status).toBe(409);
    await expect(response.json()).resolves.toMatchObject({
      gate: "governed-dispatch-unavailable",
    });
    expect(proxyAgentOperatorJson).not.toHaveBeenCalled();
  });

  it("returns the existing backlog item when the claim was already materialized", async () => {
    vi.mocked(readGeneratedMasterAtlas).mockResolvedValue({
      governed_dispatch_state: {
        claim_id: "ralph-claim-123",
        current_task_id: "workstream:dispatch-and-work-economy-closure",
        current_task_title: "Dispatch and Work-Economy Closure",
      },
    });
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({
        backlog: [
          {
            id: "backlog-1",
            title: "Dispatch and Work-Economy Closure",
            metadata: {
              materialization_source: "governed_dispatch_state",
              claim_id: "ralph-claim-123",
              current_task_id: "workstream:dispatch-and-work-economy-closure",
            },
          },
        ],
      }),
    } as Response);

    const response = await POST(
      new NextRequest("http://localhost/api/operator/backlog/materialize-governed-dispatch", {
        method: "POST",
      })
    );

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      ok: true,
      already_materialized: true,
      backlog_id: "backlog-1",
    });
    expect(proxyAgentOperatorJson).not.toHaveBeenCalled();
  });

  it("creates a backlog item from the current governed dispatch claim", async () => {
    vi.mocked(readGeneratedMasterAtlas).mockResolvedValue({
      governed_dispatch_state: {
        claim_id: "ralph-claim-123",
        current_task_id: "workstream:dispatch-and-work-economy-closure",
        current_task_title: "Dispatch and Work-Economy Closure",
        preferred_lane_family: "dispatch_truth_repair",
        approved_mutation_class: "auto_harvest",
        approved_mutation_label: "Auto harvest",
        proof_command_or_eval_surface:
          "\"C:\\Program Files\\Python313\\python.exe\" scripts/run_ralph_loop_pass.py --skip-refresh",
        provider_gate_state: "completed",
        work_economy_status: "ready",
        report_path: "reports/truth-inventory/governed-dispatch-state.json",
      },
    });
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({
        backlog: [],
      }),
    } as Response);
    vi.mocked(proxyAgentOperatorJson).mockResolvedValue(
      NextResponse.json({
        ok: true,
        backlog_id: "backlog-2",
      })
    );

    const response = await POST(
      new NextRequest("http://localhost/api/operator/backlog/materialize-governed-dispatch", {
        method: "POST",
        body: JSON.stringify({ owner_agent: "coding-agent" }),
        headers: { "content-type": "application/json" },
      })
    );

    expect(proxyAgentOperatorJson).toHaveBeenCalledWith(
      expect.any(NextRequest),
      "/v1/operator/backlog",
      "Failed to materialize governed dispatch backlog item",
      expect.objectContaining({
        privilegeClass: "operator",
        bodyOverride: expect.objectContaining({
          title: "Dispatch and Work-Economy Closure",
          owner_agent: "coding-agent",
          work_class: "system_improvement",
          dispatch_policy: "planner_eligible",
          metadata: expect.objectContaining({
            materialization_source: "governed_dispatch_state",
            claim_id: "ralph-claim-123",
            current_task_id: "workstream:dispatch-and-work-economy-closure",
          }),
        }),
      })
    );
    expect(response.status).toBe(200);
  });
});
