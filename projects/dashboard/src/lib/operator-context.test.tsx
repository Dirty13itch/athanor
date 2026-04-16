import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useOperatorContext } from "./operator-context";

describe("useOperatorContext", () => {
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

  it("loads and saves shared operator context", async () => {
    fetchMock.mockImplementation(async (input, init) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.endsWith("/api/operator/context") && (!init || init.method === undefined || init.method === "GET")) {
        return Response.json({
          source: "file",
          updatedAt: "2026-03-25T12:00:00.000Z",
          sessionCount: 1,
          threadCount: 0,
          recentContext: [
            {
              id: "chat-1",
              title: "Loaded session",
              route: "/chat?session=chat-1",
              updatedAt: "2026-03-25T12:00:00.000Z",
              type: "direct_chat_session",
            },
          ],
          sessions: [
            {
              id: "chat-1",
              title: "Loaded session",
              modelId: "/models/qwen",
              target: "litellm",
              createdAt: "2026-03-25T11:59:00.000Z",
              updatedAt: "2026-03-25T12:00:00.000Z",
              messages: [],
            },
          ],
          threads: [],
        });
      }

      if (url.endsWith("/api/operator/context/direct-chats") && init?.method === "POST") {
        return Response.json({
          source: "file",
          updatedAt: "2026-03-25T12:05:00.000Z",
          sessionCount: 2,
          threadCount: 0,
          recentContext: [
            {
              id: "chat-2",
              title: "Saved session",
              route: "/chat?session=chat-2",
              updatedAt: "2026-03-25T12:05:00.000Z",
              type: "direct_chat_session",
            },
            {
              id: "chat-1",
              title: "Loaded session",
              route: "/chat?session=chat-1",
              updatedAt: "2026-03-25T12:00:00.000Z",
              type: "direct_chat_session",
            },
          ],
          sessions: [
            {
              id: "chat-2",
              title: "Saved session",
              modelId: "/models/gpt-5.4",
              target: "litellm",
              createdAt: "2026-03-25T12:05:00.000Z",
              updatedAt: "2026-03-25T12:05:00.000Z",
              messages: [],
            },
            {
              id: "chat-1",
              title: "Loaded session",
              modelId: "/models/qwen",
              target: "litellm",
              createdAt: "2026-03-25T11:59:00.000Z",
              updatedAt: "2026-03-25T12:00:00.000Z",
              messages: [],
            },
          ],
          threads: [],
        });
      }

      throw new Error(`Unexpected fetch: ${url}`);
    });

    const { result } = renderHook(() => useOperatorContext(), { wrapper: buildWrapper() });

    await waitFor(() => {
      expect(result.current.sessions[0]?.id).toBe("chat-1");
    });

    await act(async () => {
      await result.current.saveDirectChatSession({
        id: "chat-2",
        title: "Saved session",
        modelId: "/models/gpt-5.4",
        target: "litellm",
        createdAt: "2026-03-25T12:05:00.000Z",
        updatedAt: "2026-03-25T12:05:00.000Z",
        messages: [],
      });
    });

    await waitFor(() => {
      expect(result.current.sessions.map((session) => session.id)).toEqual(["chat-2", "chat-1"]);
    });
  });
});
