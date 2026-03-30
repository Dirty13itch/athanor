import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useOperatorUiPreferences } from "./operator-ui-preferences";

describe("useOperatorUiPreferences", () => {
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
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads and saves shared operator UI preferences", async () => {
    fetchMock.mockImplementation(async (input, init) => {
      const url = typeof input === "string" ? input : input.toString();
      if (
        url.endsWith("/api/operator/ui-preferences") &&
        (!init || init.method === undefined || init.method === "GET")
      ) {
        return Response.json({
          source: "file",
          updatedAt: "2026-03-25T12:00:00.000Z",
          preferences: {
            density: "comfortable",
            lastSelectedAgentId: null,
            lastSelectedModelKey: null,
            dismissedHints: [],
          },
        });
      }

      if (url.endsWith("/api/operator/ui-preferences") && init?.method === "POST") {
        return Response.json({
          source: "file",
          updatedAt: "2026-03-25T12:05:00.000Z",
          preferences: {
            density: "compact",
            lastSelectedAgentId: "coding-agent",
            lastSelectedModelKey: "litellm::/models/qwen",
            dismissedHints: ["welcome"],
          },
        });
      }

      throw new Error(`Unexpected fetch: ${url}`);
    });

    const { result } = renderHook(() => useOperatorUiPreferences(), {
      wrapper: buildWrapper(),
    });

    await waitFor(() => {
      expect(result.current.preferences.density).toBe("comfortable");
    });

    await act(async () => {
      await result.current.setPreferences((current) => ({
        ...current,
        density: "compact",
        lastSelectedAgentId: "coding-agent",
        lastSelectedModelKey: "litellm::/models/qwen",
        dismissedHints: ["welcome"],
      }));
    });

    await waitFor(() => {
      expect(result.current.preferences.density).toBe("compact");
      expect(result.current.preferences.lastSelectedAgentId).toBe("coding-agent");
      expect(result.current.preferences.dismissedHints).toEqual(["welcome"]);
    });
  });
});
