import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/master-atlas", () => ({
  buildFallbackMasterAtlasRelationshipMap: vi.fn(),
  readGeneratedMasterAtlas: vi.fn(),
  pickMasterAtlasRelationshipMap: vi.fn(),
}));

import { GET } from "./route";
import {
  buildFallbackMasterAtlasRelationshipMap,
  pickMasterAtlasRelationshipMap,
  readGeneratedMasterAtlas,
} from "@/lib/master-atlas";

describe("master atlas api route", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("returns the compiled relationship map when the generated feed is available", async () => {
    vi.mocked(readGeneratedMasterAtlas).mockResolvedValue({ dashboard_summary: {} });
    vi.mocked(pickMasterAtlasRelationshipMap).mockReturnValue({
      generated_at: "2026-04-10T00:00:00Z",
      summary: null,
      turnover_readiness: null,
      authority_surfaces: [],
      promotion_flow: {
        source_label: "Devstack proof lanes",
        packet_ready_count: 0,
        next_promotion_candidate: null,
        target_label: "Athanor adopted truth",
        governance_posture: "blocked",
      },
      blocked_packets: [],
      node_capacity: [],
      dispatch_lanes: [],
      quota_posture: null,
      router_shadow_summary: null,
      next_required_approval: null,
      safe_surface_summary: null,
      autonomous_queue_summary: null,
      governed_dispatch_state: null,
      lane_recommendations: [],
    });

    const response = await GET();

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      generated_at: "2026-04-10T00:00:00Z",
      promotion_flow: {
        source_label: "Devstack proof lanes",
      },
    });
  });

  it("returns 503 when the generated feed cannot produce a relationship map", async () => {
    vi.mocked(readGeneratedMasterAtlas).mockResolvedValue(null);
    vi.mocked(pickMasterAtlasRelationshipMap).mockReturnValue(null);
    vi.mocked(buildFallbackMasterAtlasRelationshipMap).mockReturnValue({
      generated_at: "2026-04-13T00:00:00Z",
      available: false,
      degraded: true,
      detail: "Master atlas feed is temporarily unavailable from this dashboard runtime.",
      source: "master-atlas-fallback",
      error: "Master atlas feed is unavailable",
      summary: null,
      turnover_readiness: null,
      authority_surfaces: [],
      promotion_flow: {
        source_label: "Devstack proof lanes",
        packet_ready_count: 0,
        next_promotion_candidate: null,
        target_label: "Athanor adopted truth",
        governance_posture: null,
      },
      blocked_packets: [],
      node_capacity: [],
      dispatch_lanes: [],
      quota_posture: null,
      router_shadow_summary: null,
      next_required_approval: null,
      safe_surface_summary: null,
      autonomous_queue_summary: null,
      governed_dispatch_state: null,
      lane_recommendations: [],
    });

    const response = await GET();

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({
      available: false,
      degraded: true,
      error: "Master atlas feed is unavailable",
    });
  });
});
