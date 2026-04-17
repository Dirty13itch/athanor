import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getFixtureOverviewSnapshot } from "@/lib/dashboard-fixtures";
import { AppShell } from "./app-shell";

const { getOverview, usePathname } = vi.hoisted(() => ({
  getOverview: vi.fn(),
  usePathname: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname,
}));

vi.mock("next/dynamic", () => ({
  default: () => () => null,
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getOverview,
  };
});

vi.mock("@/lib/navigation", () => ({
  getRouteFamiliesWithRoutes: () => [
    {
      id: "command_center",
      label: "Command Center",
      routes: [{ href: "/", label: "Command", shortLabel: "Command", icon: "command" }],
    },
    {
      id: "operate",
      label: "Operate",
      routes: [
        { href: "/services", label: "Services", shortLabel: "Services", icon: "services" },
        { href: "/operator", label: "Operator", shortLabel: "Operator", icon: "operator" },
        { href: "/topology", label: "Topology", shortLabel: "Topology", icon: "topology" },
      ],
    },
    {
      id: "build",
      label: "Build",
      routes: [
        { href: "/subscriptions", label: "Subs", shortLabel: "Subs", icon: "subscriptions" },
        { href: "/routing", label: "Routing", shortLabel: "Routing", icon: "routing" },
        { href: "/projects", label: "Projects", shortLabel: "Projects", icon: "projects" },
      ],
    },
    {
      id: "catalog",
      label: "Catalog",
      routes: [{ href: "/catalog", label: "Catalog", shortLabel: "Catalog", icon: "catalog" }],
    },
  ],
  getRouteLabel: () => "Command Center",
}));

vi.mock("@/lib/operator-ui-preferences", () => ({
  useOperatorUiPreferences: () => ({
    preferences: { density: "comfortable" },
  }),
}));

vi.mock("@/components/lens-switcher", () => ({
  LensSwitcher: () => null,
}));

vi.mock("@/components/command-palette", () => ({
  CommandPalette: ({ open }: { open: boolean }) => <div data-testid="command-palette">{String(open)}</div>,
}));

vi.mock("@/components/nav-attention-provider", () => ({
  NavAttentionProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  useNavAttention: () => ({ displayTier: "none", reason: null }),
}));

vi.mock("@/components/nav-attention-label", () => ({
  NavAttentionLabel: ({ label }: { label: string }) => <>{label}</>,
}));

vi.mock("@/components/nav-attention-indicator", () => ({
  NavAttentionIndicator: () => null,
}));

vi.mock("@/components/operator-presence-heartbeat", () => ({
  OperatorPresenceHeartbeat: () => null,
}));

vi.mock("@/components/route-icon", () => ({
  RouteIcon: ({ icon }: { icon: string }) => <span data-testid={`route-icon-${icon}`} />,
}));

vi.mock("@/components/status-dot", () => ({
  StatusDot: ({ tone }: { tone: string }) => <span data-testid={`status-${tone}`} />,
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

describe("AppShell", () => {
  beforeEach(() => {
    getOverview.mockReset();
    usePathname.mockReset();
    window.localStorage.clear();
  });

  it("renders the thinner mission-control shell with primary routes and live posture", async () => {
    const snapshot = getFixtureOverviewSnapshot();
    getOverview.mockResolvedValue(snapshot);
    usePathname.mockReturnValue("/");

    render(
      <AppShell>
        <div>workspace body</div>
      </AppShell>,
      { wrapper: buildWrapper() },
    );

    expect(screen.getAllByText("Athanor").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Command palette/i })).toBeInTheDocument();
    expect(screen.getByText("Operate the cluster. Jump only when needed.")).toBeInTheDocument();
    expect(screen.getByText("workspace body")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Services/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Operator/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Topology/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Routing/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Catalog/i })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Overview refreshed/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/Needs Shaun:/i)).toBeInTheDocument();
    expect(screen.getByText(/Current:/i)).toBeInTheDocument();
  });

  it("shows a persistent what-changed digest after the front door shifts", async () => {
    const previousSnapshot = getFixtureOverviewSnapshot();
    previousSnapshot.steadyState = {
      generatedAt: "2026-04-16T00:00:00.000Z",
      closureState: "repo_safe_complete",
      operatorMode: "steady_state_monitoring",
      interventionLabel: "No action needed",
      interventionLevel: "no_action_needed",
      interventionSummary: "Queue is moving without operator intervention.",
      needsYou: false,
      nextOperatorAction: "Keep monitoring.",
      queueDispatchable: 1,
      queueTotal: 1,
      suppressedTaskCount: 0,
      runtimePacketCount: 0,
      currentWork: {
        taskTitle: "Cheap Bulk Cloud",
        providerLabel: "deepseek_api",
        laneFamily: "capacity_truth_repair",
      },
      nextUp: {
        taskTitle: "Reference and Archive Prune",
        providerLabel: "Athanor Local",
        laneFamily: "cleanup",
      },
      sourceKind: "workspace_report",
      sourcePath: "/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json",
    };
    previousSnapshot.steadyStateReadStatus = {
      available: true,
      degraded: false,
      detail: null,
      sourceKind: "workspace_report",
      sourcePath: "/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json",
    };
    window.localStorage.setItem(
      "athanor-steady-state-digest",
      JSON.stringify({
        comparisonKey: "healthy|No action needed|Cheap Bulk Cloud|Reference and Archive Prune|1 dispatchable / 0 suppressed / 0 runtime packets",
        degraded: false,
        needsYou: false,
        attentionLabel: "No action needed",
        attentionTone: "warning",
        changeHeadline: "Queue is moving without operator intervention.",
        currentWorkTitle: "Cheap Bulk Cloud",
        nextUpTitle: "Reference and Archive Prune",
        queuePosture: "1 dispatchable / 0 suppressed / 0 runtime packets",
        sourceLabel: "workspace report",
      }),
    );

    const currentSnapshot = getFixtureOverviewSnapshot();
    currentSnapshot.steadyState = {
      ...previousSnapshot.steadyState,
      interventionLabel: "Review recommended",
      interventionLevel: "review_recommended",
      interventionSummary: "Promotion work is ready for review.",
      needsYou: true,
      nextOperatorAction: "Review the next activation lane.",
      queueDispatchable: 2,
      currentWork: {
        taskTitle: "Letta Memory Plane",
        providerLabel: "Athanor Local",
        laneFamily: "memory_plane",
      },
      nextUp: {
        taskTitle: "Agent Governance Toolkit Policy Plane",
        providerLabel: "Athanor Local",
        laneFamily: "policy_plane",
      },
    };
    getOverview.mockResolvedValue(currentSnapshot);
    usePathname.mockReturnValue("/operator");

    render(
      <AppShell>
        <div>workspace body</div>
      </AppShell>,
      { wrapper: buildWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByText("Shaun attention is now required.")).toBeInTheDocument();
    });
    expect(screen.getByText(/Needs Shaun: Yes/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Current:/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Letta Memory Plane").length).toBeGreaterThan(0);
  });
});
