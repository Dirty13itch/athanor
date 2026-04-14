import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
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
  });
});
