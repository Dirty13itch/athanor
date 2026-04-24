import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getFixtureIntelligenceSnapshot } from "@/lib/dashboard-fixtures";
import { IntelligenceConsole } from "./intelligence-console";

const { getIntelligence, getSearchValue, setSearchValue, postWithoutBody } = vi.hoisted(() => ({
  getIntelligence: vi.fn(),
  getSearchValue: vi.fn(),
  setSearchValue: vi.fn(),
  postWithoutBody: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getIntelligence,
  };
});

vi.mock("@/lib/url-state", () => ({
  useUrlState: () => ({
    getSearchValue,
    setSearchValue,
  }),
}));

vi.mock("@/features/workforce/helpers", () => ({
  postWithoutBody,
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/insights",
  useSearchParams: () => new URLSearchParams(),
}));

function buildWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe("IntelligenceConsole", () => {
  const snapshot = getFixtureIntelligenceSnapshot();

  beforeEach(() => {
    getIntelligence.mockResolvedValue(snapshot);
    postWithoutBody.mockResolvedValue(undefined);
    setSearchValue.mockReset();
    getSearchValue.mockImplementation((key: string, fallback: string) => {
      if (key === "selection") {
        return "builder-result:task-media-1";
      }
      return fallback;
    });
  });

  it("renders insights without depending on the review feed", async () => {
    render(<IntelligenceConsole initialSnapshot={snapshot} variant="insights" />, {
      wrapper: buildWrapper(),
    });

    expect(await screen.findByRole("heading", { name: "Insights" })).toBeInTheDocument();
    expect(screen.getByText("Detected patterns")).toBeInTheDocument();
    expect(screen.queryByText("Review Queue")).not.toBeInTheDocument();
    expect(screen.queryByText("Sonarr queue hydration failed and needs operator review.")).not.toBeInTheDocument();
  });
});
