import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { requestJson } from "@/features/workforce/helpers";
import { getFixtureOverviewSnapshot } from "@/lib/dashboard-fixtures";
import { CommandCenter } from "./command-center";

const pilotReadinessPayload = {
  generatedAt: "2026-04-16T15:11:19.861884+00:00",
  available: true,
  degraded: false,
  detail: null,
  sourceKind: "workspace_generated_atlas" as const,
  sourcePath: "/mnt/c/Athanor/projects/dashboard/src/generated/master-atlas.json",
  summary: {
    total: 3,
    formalEvalComplete: 0,
    formalEvalFailed: 0,
    manualReviewPending: 0,
    readyForFormalEval: 0,
    operatorSmokeOnly: 0,
    scaffoldOnly: 0,
    blocked: 3,
  },
  records: [
    {
      capabilityId: "letta-memory-plane",
      label: "Letta Memory Plane",
      laneStatus: null,
      capabilityStage: null,
      hostId: "desk",
      readinessState: "blocked",
      proofTier: "operator_smoke_plus_formal_scaffold",
      blockingReasons: ["missing_packet", "missing_env:LETTA_API_KEY"],
      commandChecks: [],
      packetPath: "C:/athanor-devstack/docs/promotion-packets/letta-memory-plane.md",
      latestEvalRunId: null,
      latestEvalStatus: null,
      latestEvalOutcome: null,
      latestEvalAt: null,
      formalEvalStatus: null,
      formalEvalAt: null,
      formalEvalDecisionReason: null,
      formalEvalPrimaryFailureHint: null,
      formalPreflightStatus: null,
      formalPreflightAt: null,
      formalPreflightBlockerClass: "env_wiring",
      formalPreflightBlockingReasons: ["missing_env:LETTA_API_KEY"],
      formalPreflightMissingCommands: [],
      formalPreflightMissingEnvVars: ["LETTA_API_KEY"],
      formalPreflightMissingFixtureFiles: [],
      formalPreflightMissingResultFiles: [],
      manualReviewOutcome: null,
      manualReviewSummary: null,
      nextAction: "Wire LETTA_API_KEY, run the bounded continuity benchmark, and keep replayability and pruning explicit.",
      nextFormalGate: "Wire the required formal-eval env vars: `LETTA_API_KEY`.",
      formalRunnerSupport: null,
    },
    {
      capabilityId: "openhands-bounded-worker-lane",
      label: "OpenHands Bounded Worker Lane",
      laneStatus: null,
      capabilityStage: null,
      hostId: "desk",
      readinessState: "blocked",
      proofTier: "blocked",
      blockingReasons: [
        "missing_command:openhands",
        "missing_packet",
        "missing_env:OPENAI_API_KEY",
        "missing_env:PROMPTFOO_OPENHANDS_CMD",
        "missing_env:PROMPTFOO_OPENHANDS_ARGS_JSON",
      ],
      commandChecks: [],
      packetPath: "C:/athanor-devstack/docs/promotion-packets/openhands-bounded-worker-lane.md",
      latestEvalRunId: null,
      latestEvalStatus: null,
      latestEvalOutcome: null,
      latestEvalAt: null,
      formalEvalStatus: null,
      formalEvalAt: null,
      formalEvalDecisionReason: null,
      formalEvalPrimaryFailureHint: null,
      formalPreflightStatus: null,
      formalPreflightAt: null,
      formalPreflightBlockerClass: "missing_command",
      formalPreflightBlockingReasons: ["missing_command:openhands"],
      formalPreflightMissingCommands: ["openhands"],
      formalPreflightMissingEnvVars: ["OPENAI_API_KEY"],
      formalPreflightMissingFixtureFiles: [],
      formalPreflightMissingResultFiles: [],
      manualReviewOutcome: null,
      manualReviewSummary: null,
      nextAction: "Expose the OpenHands command on DESK, clear the worker env wiring, and run the bounded-worker eval.",
      nextFormalGate: "Install or expose `openhands` on the preferred pilot host.",
      formalRunnerSupport: null,
    },
    {
      capabilityId: "agent-governance-toolkit-policy-plane",
      label: "Agent Governance Toolkit Policy Plane",
      laneStatus: null,
      capabilityStage: null,
      hostId: "desk",
      readinessState: "blocked",
      proofTier: "formal_eval_failed",
      blockingReasons: ["missing_packet"],
      commandChecks: [],
      packetPath: "C:/athanor-devstack/docs/promotion-packets/agent-governance-toolkit-policy-plane.md",
      latestEvalRunId: null,
      latestEvalStatus: null,
      latestEvalOutcome: null,
      latestEvalAt: null,
      formalEvalStatus: "failed",
      formalEvalAt: null,
      formalEvalDecisionReason: null,
      formalEvalPrimaryFailureHint: null,
      formalPreflightStatus: null,
      formalPreflightAt: null,
      formalPreflightBlockerClass: null,
      formalPreflightBlockingReasons: [],
      formalPreflightMissingCommands: [],
      formalPreflightMissingEnvVars: [],
      formalPreflightMissingFixtureFiles: [],
      formalPreflightMissingResultFiles: [],
      manualReviewOutcome: "rejected_as_redundant_for_current_stack",
      manualReviewSummary: "Current narrow approval-held mutation bundle does not prove non-duplicative operational value.",
      nextAction: "Leave this lane below adapter work on the current manual review, and only reopen it if a second protocol-boundary scenario proves unique value over native Athanor policy.",
      nextFormalGate: "Keep this lane below adapter work unless a second protocol-boundary scenario shows non-duplicative value over native Athanor policy.",
      formalRunnerSupport: null,
    },
  ],
};

const { getOverview } = vi.hoisted(() => ({
  getOverview: vi.fn(),
}));

vi.mock("@/features/workforce/helpers", () => ({
  requestJson: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getOverview,
  };
});

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

describe("CommandCenter", () => {
  it("renders the mission-control triage surface from live-shaped overview data", async () => {
    const snapshot = getFixtureOverviewSnapshot();
    getOverview.mockResolvedValue(snapshot);
    vi.mocked(requestJson).mockImplementation(async (url: string) => {
      if (url === "/api/master-atlas") {
        return {
          generated_at: "2026-04-13T21:57:17.698187+00:00",
          turnover_readiness: {
            work_economy_status: "ready",
            dispatchable_autonomous_queue_count: 3,
            top_dispatchable_autonomous_task_title: "Dispatch and Work-Economy Closure",
          },
          governed_dispatch_execution: {
            status: "already_dispatched",
            dispatch_outcome: "claimed",
            current_task_title: "Dispatch and Work-Economy Closure",
            backlog_status: "scheduled",
            task_status: "running",
            task_source: "auto-retry",
            recovery_reason: "server_restart",
            resilience_state: "restart_interfering",
            advisory_blockers: ["agent_runtime_restart_interfering"],
            governor_level: "A",
          },
        };
      }

      if (url === "/api/operator/pilot-readiness") {
        return pilotReadinessPayload;
      }

      return {};
    });

    render(<CommandCenter initialSnapshot={snapshot} />, { wrapper: buildWrapper() });

    expect(screen.getByRole("heading", { name: /Current work, next move, and live pressure\./i })).toBeInTheDocument();
    expect(screen.getByText("Current plan")).toBeInTheDocument();
    expect(screen.getByText("wp-1741531200")).toBeInTheDocument();
    expect(screen.getAllByText(/Push EoBQ content and keep Athanor drift in check\./i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Implement the next EoBQ scene renderer state machine and branching transitions\./i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open workforce planner/i })).toHaveAttribute("href", "/workforce");
    expect(screen.getByText("Priority Queue")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open backlog/i })).toHaveAttribute("href", "/backlog");
    expect(screen.getByText("Critical Signals")).toBeInTheDocument();
    expect(screen.getByText("Cluster Posture")).toBeInTheDocument();
    expect(screen.getByText("Operator attention")).toBeInTheDocument();
    expect(screen.getAllByText(/No action needed/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/workspace report/i)).toBeInTheDocument();
    expect(screen.getByText(/Core closure is complete and no approval-held runtime work is waiting\./i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Open operator desk/i })).toHaveAttribute('href', '/operator');
    expect(screen.getByText("Builder front door")).toBeInTheDocument();
    expect(screen.getAllByText(/Codex direct implementation/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("link", { name: /Open builder desk/i })).toHaveAttribute(
      "href",
      "/builder?session=builder-fixture-1",
    );
    expect(await screen.findByText(/Pilot readiness/i)).toBeInTheDocument();
    expect((await screen.findAllByText(/Letta Memory Plane/i)).length).toBeGreaterThan(0);
    expect((await screen.findAllByText(/OpenHands Bounded Worker Lane/i)).length).toBeGreaterThan(0);
    expect((await screen.findAllByText(/Agent Governance Toolkit Policy Plane/i)).length).toBeGreaterThan(0);
    expect(screen.getByText("Specialist routes")).toBeInTheDocument();
    expect(screen.getByText(/Depth lives on the specialist routes/i)).toBeInTheDocument();
    expect(screen.getByText("First Read")).toBeInTheDocument();
    expect(screen.getByText(/Live posture first, then proof surfaces for deeper drilling\./i)).toBeInTheDocument();
    expect(screen.getByText("Proof drill-down")).toBeInTheDocument();
    expect(await screen.findByText(/Autonomous handoff/i)).toBeInTheDocument();
    expect(await screen.findByText(/Dispatch and Work-Economy Closure/i)).toBeInTheDocument();
    expect(screen.getByText(/auto-retry lineage after a server restart/i)).toBeInTheDocument();
    expect(
      screen.getAllByText(/Recent agent-runtime restarts are interrupting governed execution\./i).length,
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/recovered from server restart/i)).toBeInTheDocument();
    expect(screen.getByText(/Cheap Bulk Cloud/i)).toBeInTheDocument();
    expect(screen.getAllByText(/restart interfering/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("link", { name: /Open this surface/i })).toHaveAttribute(
      "href",
      "/routing",
    );
    const routeOwnershipPanel = screen.getByText(/Depth lives on the specialist routes/i).closest(".surface-panel") as HTMLElement | null;
    expect(routeOwnershipPanel).toBeTruthy();
    if (!routeOwnershipPanel) return;
    expect(
      within(routeOwnershipPanel)
        .getAllByRole("link", { name: /Operator/ })
        .some((link) => link.getAttribute("href") === "/operator"),
    ).toBe(true);
    expect(
      within(routeOwnershipPanel)
        .getAllByRole("link", { name: /Routing/ })
        .some((link) => link.getAttribute("href") === "/routing"),
    ).toBe(true);
    expect(
      within(routeOwnershipPanel)
        .getAllByRole("link", { name: /Subscriptions/ })
        .some((link) => link.getAttribute("href") === "/subscriptions"),
    ).toBe(true);
    const proofDrilldownPanel = screen.getByText("Proof drill-down").closest("div")?.parentElement?.parentElement as HTMLElement | null;
    expect(proofDrilldownPanel).toBeTruthy();
    if (!proofDrilldownPanel) return;
    expect(within(proofDrilldownPanel).getByRole("link", { name: /Route index/i })).toHaveAttribute("href", "/more");
  });

  it("surfaces a degraded steady-state front door explicitly", async () => {
    const snapshot = {
      ...getFixtureOverviewSnapshot(),
      steadyState: null,
      steadyStateReadStatus: {
        available: false,
        degraded: true,
        detail: "Invalid steady-state front door at /tmp/steady-state-status.json",
        sourceKind: "workspace_report" as const,
        sourcePath: "/tmp/steady-state-status.json",
      },
    };
    getOverview.mockResolvedValue(snapshot);
    vi.mocked(requestJson).mockImplementation(async (url: string) => {
      if (url === "/api/operator/pilot-readiness") {
        return {
          ...pilotReadinessPayload,
          available: false,
          degraded: true,
          detail: "Capability pilot readiness feed is unavailable.",
        };
      }
      return {};
    });

    render(<CommandCenter initialSnapshot={snapshot} />, { wrapper: buildWrapper() });

    expect(await screen.findByText(/Steady-state front door degraded/i)).toBeInTheDocument();
    expect(screen.getByText(/Invalid steady-state front door at \/tmp\/steady-state-status.json/i)).toBeInTheDocument();
    expect(screen.getByText(/Source: workspace_report/i)).toBeInTheDocument();
  });
});
