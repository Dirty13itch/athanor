import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { requestJson } from "@/features/workforce/helpers";
import { getFixtureOverviewSnapshot } from "@/lib/dashboard-fixtures";
import { CommandCenter } from "./command-center";

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
    vi.mocked(requestJson).mockResolvedValue({
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
    expect(screen.getByText(/Core closure is complete and no approval-held runtime work is waiting\./i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Open operator desk/i })).toHaveAttribute('href', '/operator');
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
});
