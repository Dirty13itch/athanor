import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  directChatSessionSchema,
  agentThreadSchema,
  operatorContextSnapshotSchema,
  type AgentThread,
  type DirectChatSession,
  type OperatorContextSnapshot,
} from "@/lib/contracts";
import { fetchJson } from "@/lib/http";

const OPERATOR_CONTEXT_QUERY_KEY = ["operator-context"] as const;

const EMPTY_OPERATOR_CONTEXT: OperatorContextSnapshot = {
  source: "file",
  updatedAt: "",
  sessionCount: 0,
  threadCount: 0,
  recentContext: [],
  sessions: [],
  threads: [],
};

async function mutateOperatorContext(
  input: RequestInfo | URL,
  init: RequestInit | undefined
): Promise<OperatorContextSnapshot> {
  const response = await fetch(input, init);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }

  return operatorContextSnapshotSchema.parse(await response.json());
}

export async function fetchOperatorContext(): Promise<OperatorContextSnapshot> {
  return fetchJson("/api/operator/context", { cache: "no-store" }, operatorContextSnapshotSchema);
}

export async function upsertDirectChatSession(
  session: DirectChatSession
): Promise<OperatorContextSnapshot> {
  const payload = directChatSessionSchema.parse(session);
  return mutateOperatorContext("/api/operator/context/direct-chats", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
}

export async function removeDirectChatSession(
  sessionId: string
): Promise<OperatorContextSnapshot> {
  return mutateOperatorContext(`/api/operator/context/direct-chats/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
    cache: "no-store",
  });
}

export async function upsertAgentThread(thread: AgentThread): Promise<OperatorContextSnapshot> {
  const payload = agentThreadSchema.parse(thread);
  return mutateOperatorContext("/api/operator/context/agent-threads", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
}

export async function removeAgentThread(threadId: string): Promise<OperatorContextSnapshot> {
  return mutateOperatorContext(`/api/operator/context/agent-threads/${encodeURIComponent(threadId)}`, {
    method: "DELETE",
    cache: "no-store",
  });
}

export function useOperatorContext() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: OPERATOR_CONTEXT_QUERY_KEY,
    queryFn: fetchOperatorContext,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
  const snapshot = query.data ?? EMPTY_OPERATOR_CONTEXT;

  async function saveDirectChatSession(
    session: DirectChatSession
  ): Promise<OperatorContextSnapshot> {
    const next = await upsertDirectChatSession(session);
    queryClient.setQueryData(OPERATOR_CONTEXT_QUERY_KEY, next);
    return next;
  }

  async function deleteDirectChatSession(
    sessionId: string
  ): Promise<OperatorContextSnapshot> {
    const next = await removeDirectChatSession(sessionId);
    queryClient.setQueryData(OPERATOR_CONTEXT_QUERY_KEY, next);
    return next;
  }

  async function saveAgentThread(thread: AgentThread): Promise<OperatorContextSnapshot> {
    const next = await upsertAgentThread(thread);
    queryClient.setQueryData(OPERATOR_CONTEXT_QUERY_KEY, next);
    return next;
  }

  async function deleteAgentThread(threadId: string): Promise<OperatorContextSnapshot> {
    const next = await removeAgentThread(threadId);
    queryClient.setQueryData(OPERATOR_CONTEXT_QUERY_KEY, next);
    return next;
  }

  return {
    ...query,
    source: snapshot.source,
    updatedAt: snapshot.updatedAt,
    recentContext: snapshot.recentContext,
    sessions: snapshot.sessions,
    threads: snapshot.threads,
    saveDirectChatSession,
    deleteDirectChatSession,
    saveAgentThread,
    deleteAgentThread,
  } as const;
}
