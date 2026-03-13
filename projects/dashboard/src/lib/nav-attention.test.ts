import { describe, expect, it } from "vitest";
import type { JudgePlaneSnapshot } from "@/lib/contracts";
import {
  getFixtureAgentsSnapshot,
  getFixtureServicesSnapshot,
  getFixtureWorkforceSnapshot,
} from "@/lib/dashboard-fixtures";
import {
  buildNavAttentionSignals,
  resolveNavAttentionPresentation,
  type NavAttentionPersistenceRecord,
} from "@/lib/nav-attention";

const fixtureJudge: Pick<JudgePlaneSnapshot, "generated_at" | "summary"> = {
  generated_at: "2026-03-09T15:00:00.000Z",
  summary: {
    recent_verdicts: 5,
    accept_count: 3,
    reject_count: 2,
    review_required: 2,
    acceptance_rate: 0.6,
    pending_review_queue: 2,
  },
};

describe("buildNavAttentionSignals", () => {
  it("classifies pending approvals on /tasks as urgent", () => {
    const signals = buildNavAttentionSignals({
      workforce: getFixtureWorkforceSnapshot(),
      services: getFixtureServicesSnapshot().services,
      agents: getFixtureAgentsSnapshot().agents,
      judge: fixtureJudge,
      updatedAt: "2026-03-09T15:00:00.000Z",
    });

    const signal = signals.find((entry) => entry.routeHref === "/tasks");
    expect(signal?.tier).toBe("urgent");
    expect(signal?.source).toBe("pending_approvals");
    expect(signal?.count).toBe(2);
  });

  it("classifies review backlog on /review as urgent", () => {
    const signals = buildNavAttentionSignals({
      workforce: getFixtureWorkforceSnapshot(),
      services: getFixtureServicesSnapshot().services,
      agents: getFixtureAgentsSnapshot().agents,
      judge: fixtureJudge,
      updatedAt: "2026-03-09T15:00:00.000Z",
    });

    const signal = signals.find((entry) => entry.routeHref === "/review");
    expect(signal?.tier).toBe("urgent");
    expect(signal?.source).toBe("pending_review_queue");
    expect(signal?.count).toBe(2);
  });

  it("marks /services urgent when a core service is degraded", () => {
    const services = getFixtureServicesSnapshot().services.map((service) =>
      service.id === "litellm-proxy"
        ? { ...service, healthy: false, state: "degraded" as const, latencyMs: null }
        : service
    );

    const signals = buildNavAttentionSignals({
      workforce: getFixtureWorkforceSnapshot(),
      services,
      agents: getFixtureAgentsSnapshot().agents,
      judge: fixtureJudge,
      updatedAt: "2026-03-09T15:00:00.000Z",
    });

    const signal = signals.find((entry) => entry.routeHref === "/services");
    expect(signal?.tier).toBe("urgent");
    expect(signal?.source).toBe("degraded_core_services");
    expect(signal?.count).toBeGreaterThanOrEqual(1);
  });
});

describe("resolveNavAttentionPresentation", () => {
  const signal = {
    routeHref: "/tasks",
    tier: "urgent" as const,
    count: 2,
    reason: "2 tasks need approval.",
    source: "pending_approvals" as const,
    updatedAt: "2026-03-09T15:00:00.000Z",
    signature: "/tasks|pending_approvals|urgent|2|task-1|task-2",
  };

  it("keeps urgent signals hot before they settle", () => {
    const persisted: NavAttentionPersistenceRecord = {
      signature: signal.signature,
      firstSeenAt: "2026-03-09T15:00:00.000Z",
      acknowledgedAt: null,
    };

    const presentation = resolveNavAttentionPresentation(signal, persisted, {
      activeSurface: false,
      tabVisible: true,
      reducedMotion: false,
      nowMs: Date.parse("2026-03-09T15:00:30.000Z"),
    });

    expect(presentation.displayTier).toBe("urgent");
    expect(presentation.animateSweep).toBe(true);
    expect(presentation.settled).toBe(false);
  });

  it("settles but does not silence unresolved urgent signals over time", () => {
    const persisted: NavAttentionPersistenceRecord = {
      signature: signal.signature,
      firstSeenAt: "2026-03-09T15:00:00.000Z",
      acknowledgedAt: null,
    };

    const presentation = resolveNavAttentionPresentation(signal, persisted, {
      activeSurface: false,
      tabVisible: true,
      reducedMotion: false,
      nowMs: Date.parse("2026-03-09T15:04:00.000Z"),
    });

    expect(presentation.displayTier).toBe("urgent");
    expect(presentation.animateSweep).toBe(true);
    expect(presentation.settled).toBe(true);
  });

  it("downgrades acknowledged urgent signals to action", () => {
    const persisted: NavAttentionPersistenceRecord = {
      signature: signal.signature,
      firstSeenAt: "2026-03-09T15:00:00.000Z",
      acknowledgedAt: "2026-03-09T15:01:00.000Z",
    };

    const presentation = resolveNavAttentionPresentation(signal, persisted, {
      activeSurface: false,
      tabVisible: true,
      reducedMotion: false,
      nowMs: Date.parse("2026-03-09T15:02:00.000Z"),
    });

    expect(presentation.displayTier).toBe("action");
    expect(presentation.animateSweep).toBe(false);
    expect(presentation.acknowledged).toBe(true);
  });

  it("suppresses rail animation for the active route", () => {
    const persisted: NavAttentionPersistenceRecord = {
      signature: signal.signature,
      firstSeenAt: "2026-03-09T15:00:00.000Z",
      acknowledgedAt: null,
    };

    const presentation = resolveNavAttentionPresentation(signal, persisted, {
      activeSurface: true,
      tabVisible: true,
      reducedMotion: false,
      nowMs: Date.parse("2026-03-09T15:00:30.000Z"),
    });

    expect(presentation.displayTier).toBe("urgent");
    expect(presentation.animateSweep).toBe(false);
    expect(presentation.activeSurface).toBe(true);
  });
});
