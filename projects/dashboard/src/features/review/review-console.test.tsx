import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getFixtureReviewSnapshot } from "@/lib/dashboard-fixtures";
import { ReviewConsole } from "./review-console";

const { getReview, getSearchValue, setSearchValue, postWithoutBody } = vi.hoisted(() => ({
  getReview: vi.fn(),
  getSearchValue: vi.fn(),
  setSearchValue: vi.fn(),
  postWithoutBody: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getReview,
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
  usePathname: () => "/review",
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

describe("ReviewConsole", () => {
  const snapshot = getFixtureReviewSnapshot();

  beforeEach(() => {
    getReview.mockResolvedValue(snapshot);
    postWithoutBody.mockResolvedValue(undefined);
    setSearchValue.mockReset();
    getSearchValue.mockImplementation((key: string, fallback: string) => {
      if (key === "selection") {
        return "builder-result:task-media-1";
      }
      return fallback;
    });
  });

  it("renders explicit kernel-backed review detail from the dedicated review feed", async () => {
    render(<ReviewConsole initialSnapshot={snapshot} />, {
      wrapper: buildWrapper(),
    });

    expect(await screen.findByText("Review Queue")).toBeInTheDocument();
    expect((await screen.findAllByText("Sonarr queue hydration failed and needs operator review.")).length).toBeGreaterThan(0);
    expect(screen.getByText("Outcome")).toBeInTheDocument();
    expect(screen.getAllByText("failed").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /Open source/i })).toHaveAttribute(
      "href",
      "/builder?session=task-media-1",
    );
  });
});
