import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { requestJson } from "@/features/workforce/helpers";
import { ProjectsConsole } from "./projects-console";

vi.mock("@/features/workforce/helpers", () => ({
  requestJson: vi.fn(),
}));

function buildWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe("ProjectsConsole", () => {
  it("renders the governed project-factory view from truth artifacts", async () => {
    vi.mocked(requestJson).mockResolvedValue({
      generatedAt: "2026-04-20T22:15:00+00:00",
      available: true,
      degraded: false,
      detail: null,
      summary: {
        operatingMode: "core_runtime_hold",
        topPriorityProjectId: "eoq",
        topPriorityProjectLabel: "Empire of Broken Queens",
        acceptedProjectOutputCount: 0,
        pendingCandidateCount: 1,
        pendingHybridAcceptanceCount: 1,
        latestPendingProjectId: "eoq",
        broadProjectFactoryReady: false,
        projectOutputStageMet: false,
        distinctProjectCount: 0,
        eligibleNowCount: 0,
      },
      coreRuntimeGate: {
        proofGateOpen: false,
        continuityHealthStatus: "healthy",
        runtimeParityClass: "generated_surface_drift",
        singleLiveBlocker: "stable_operating_day",
        stableOperatingDayMet: false,
        stableOperatingDayHours: 1.38,
        stableOperatingDayRequiredHours: 24,
        blockingCheckIds: ["stable_operating_day"],
      },
      latestPendingCandidate: {
        title: "EOQ scene pack: The Courtyard of Ashenmoor",
        projectId: "eoq",
        deliverableKind: "content_artifact",
        acceptanceState: "pending_acceptance",
        acceptanceBacklogId: "backlog-dbee5ca9",
        acceptanceMode: "hybrid",
        verificationStatus: "passed",
        nextAction: "materialize_hybrid_acceptance",
        deliverableRefs: ["projects/eoq/NEW/courtyard-scene-pack-alpha/manifest.json"],
        workflowRefs: ["projects/eoq/comfyui/flux-scene.json"],
      },
      firstClassProjects: [
        {
          projectId: "eoq",
          label: "Empire of Broken Queens",
          canonicalRoot: "C:\\Athanor\\projects\\eoq",
          projectClass: "sovereign_creative_runtime_product",
          platformClass: "creative_runtime",
          authorityClass: "athanor_in_repo_project",
          authorityCleanliness: "dirty",
          autonomyEligibility: "held_by_core_runtime_gate",
          readinessTier: "core_gate_hold",
          buildHealth: "passed",
          safeSurfaceStatus: "athanor_in_repo",
          safeSurfaceExpectation: "not_applicable",
          routingClass: "sovereign_only",
          factoryPriority: 10,
          firstOutputTarget: "Reproducible scene pack or character bundle.",
          nextTranche: "Produce the first accepted EOQ scene pack.",
          blockers: ["dirty_authority_root", "core_runtime_gate:stable_operating_day"],
          verificationBundle: ["npm run build"],
          acceptanceBundle: ["Accepted creative artifact refs"],
          isFirstClass: true,
          isTopPriority: true,
          candidateCount: 1,
          pendingCandidateCount: 1,
          acceptedCandidateCount: 0,
          latestCandidate: {
            title: "EOQ scene pack: The Courtyard of Ashenmoor",
            projectId: "eoq",
            deliverableKind: "content_artifact",
            acceptanceState: "pending_acceptance",
            acceptanceBacklogId: "backlog-dbee5ca9",
            acceptanceMode: "hybrid",
            verificationStatus: "passed",
            deliverableRefs: ["projects/eoq/NEW/courtyard-scene-pack-alpha/manifest.json"],
            workflowRefs: ["projects/eoq/comfyui/flux-scene.json"],
          },
          latestAcceptedEntry: null,
        },
      ],
      baselineProjects: [
        {
          projectId: "lawnsignal",
          label: "LawnSignal",
          readinessTier: "admission_pending",
          projectClass: "web_plus_mobile_consumer_product",
          platformClass: "web_plus_mobile",
          autonomyEligibility: "explicit_admission_required",
          nextTranche: "Promote LawnSignal into the governed project-output loop.",
        },
      ],
      finalFormStatus: {
        done: false,
        summary: {
          openGapCount: 1,
          highestSeverity: "medium",
          consecutiveCleanUiAuditPassCount: 1,
        },
        openGaps: [
          {
            id: "ui-audit-clean-pass-streak",
            route: "/",
            severity: "medium",
            tranche: "verification",
            verificationState: "needs_second_clean_pass",
            detail: "The final-form bar requires two consecutive UI audit passes.",
          },
        ],
      },
    });

    render(<ProjectsConsole />, { wrapper: buildWrapper() });

    expect(await screen.findByRole("heading", { name: "Governed Projects" })).toBeInTheDocument();
    expect(screen.getAllByText("Empire of Broken Queens").length).toBeGreaterThan(0);
    expect(screen.getAllByText("EOQ scene pack: The Courtyard of Ashenmoor").length).toBeGreaterThan(0);
    expect(screen.getAllByText("backlog-dbee5ca9").length).toBeGreaterThan(0);
    expect(screen.getByText("LawnSignal")).toBeInTheDocument();
    expect(screen.getByText(/two consecutive UI audit passes/i)).toBeInTheDocument();
  });
});
