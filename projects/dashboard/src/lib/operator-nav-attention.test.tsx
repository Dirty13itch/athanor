import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useOperatorNavAttention } from "./operator-nav-attention";

describe("useOperatorNavAttention", () => {
  const fetchMock = vi.fn();

  function buildWrapper() {
    const client = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });

    return function Wrapper({ children }: { children: ReactNode }) {
      return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
    };
  }

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads and saves shared nav attention state", async () => {
    fetchMock.mockImplementation(async (input, init) => {
      const url = typeof input === "string" ? input : input.toString();
      if (
        url.endsWith("/api/operator/nav-attention") &&
        (!init || init.method === undefined || init.method === "GET")
      ) {
        return Response.json({
          source: "file",
          updatedAt: "2026-03-25T12:00:00.000Z",
          routeCount: 1,
          state: {
            "/runs": {
              signature: "/runs|pending_approvals|urgent|1|task-1",
              firstSeenAt: "2026-03-25T12:00:00.000Z",
              acknowledgedAt: null,
            },
          },
        });
      }

      if (url.endsWith("/api/operator/nav-attention") && init?.method === "POST") {
        return Response.json({
          source: "file",
          updatedAt: "2026-03-25T12:05:00.000Z",
          routeCount: 2,
          state: {
            "/runs": {
              signature: "/runs|pending_approvals|urgent|1|task-1",
              firstSeenAt: "2026-03-25T12:00:00.000Z",
              acknowledgedAt: "2026-03-25T12:05:00.000Z",
            },
            "/services": {
              signature: "/services|degraded_core_services|urgent|1|dashboard",
              firstSeenAt: "2026-03-25T12:05:00.000Z",
              acknowledgedAt: null,
            },
          },
        });
      }

      throw new Error(`Unexpected fetch: ${url}`);
    });

    const { result } = renderHook(() => useOperatorNavAttention(), {
      wrapper: buildWrapper(),
    });

    await waitFor(() => {
      expect(result.current.state["/runs"]?.signature).toContain("pending_approvals");
    });

    await act(async () => {
      await result.current.saveState({
        "/runs": {
          signature: "/runs|pending_approvals|urgent|1|task-1",
          firstSeenAt: "2026-03-25T12:00:00.000Z",
          acknowledgedAt: "2026-03-25T12:05:00.000Z",
        },
        "/services": {
          signature: "/services|degraded_core_services|urgent|1|dashboard",
          firstSeenAt: "2026-03-25T12:05:00.000Z",
          acknowledgedAt: null,
        },
      });
    });

    await waitFor(() => {
      expect(Object.keys(result.current.state)).toEqual(["/runs", "/services"]);
      expect(result.current.routeCount).toBe(2);
    });
  });
});
