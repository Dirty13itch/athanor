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

    expect(screen.getByRole("heading", { name: /Triage the system, pick the next move, then jump\./i })).toBeInTheDocument();
    expect(screen.getByText("Priority Queue")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open backlog/i })).toHaveAttribute("href", "/backlog");
    expect(screen.getByText("Critical Signals")).toBeInTheDocument();
    expect(screen.getByText("Cluster Posture")).toBeInTheDocument();
    expect(screen.getByText("Route ownership")).toBeInTheDocument();
    expect(screen.getByText(/Depth lives on the specialist routes/i)).toBeInTheDocument();
    expect(await screen.findByText(/Autonomous handoff/i)).toBeInTheDocument();
    expect(await screen.findByText(/Dispatch and Work-Economy Closure/i)).toBeInTheDocument();
    expect(screen.getByText(/auto-retry lineage after a server restart/i)).toBeInTheDocument();
    expect(
      screen.getAllByText(/Recent agent-runtime restarts are interrupting governed execution\./i).length,
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/recovered from server restart/i)).toBeInTheDocument();
    expect(screen.getAllByText(/restart interfering/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("link", { name: /Open this surface/i })).toHaveAttribute(
      "href",
      "/routing",
    );
    const routeOwnershipPanel = screen.getByText(/Depth lives on the specialist routes/i).closest("div")?.parentElement;
    expect(routeOwnershipPanel).toBeTruthy();
    if (!routeOwnershipPanel) return;
    expect(within(routeOwnershipPanel).getByRole("link", { name: /Operator/ })).toHaveAttribute("href", "/operator");
    expect(within(routeOwnershipPanel).getByRole("link", { name: /Routing/ })).toHaveAttribute("href", "/routing");
    expect(within(routeOwnershipPanel).getByRole("link", { name: /Subscriptions/ })).toHaveAttribute("href", "/subscriptions");
  });
});
