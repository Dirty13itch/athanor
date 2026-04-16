import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  navAttentionPersistenceStateSchema,
  navAttentionSnapshotSchema,
  type NavAttentionPersistenceState,
  type NavAttentionSnapshot,
} from "@/lib/contracts";
import { fetchJson } from "@/lib/http";
import { useOperatorSessionStatus } from "@/lib/operator-session";

const OPERATOR_NAV_ATTENTION_QUERY_KEY = ["operator-nav-attention"] as const;

const EMPTY_NAV_ATTENTION_SNAPSHOT: NavAttentionSnapshot = {
  source: "file",
  updatedAt: "",
  routeCount: 0,
  state: {},
};

async function mutateNavAttention(
  state: NavAttentionPersistenceState
): Promise<NavAttentionSnapshot> {
  const payload = navAttentionPersistenceStateSchema.parse(state);
  const response = await fetch("/api/operator/nav-attention", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }

  return navAttentionSnapshotSchema.parse(await response.json());
}

export async function fetchOperatorNavAttention(): Promise<NavAttentionSnapshot> {
  return fetchJson(
    "/api/operator/nav-attention",
    { cache: "no-store" },
    navAttentionSnapshotSchema
  );
}

export function useOperatorNavAttention() {
  const session = useOperatorSessionStatus();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: OPERATOR_NAV_ATTENTION_QUERY_KEY,
    queryFn: fetchOperatorNavAttention,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    enabled: !session.requiresSession || session.unlocked,
  });

  const snapshot = query.data ?? EMPTY_NAV_ATTENTION_SNAPSHOT;

  async function saveState(
    state: NavAttentionPersistenceState
  ): Promise<NavAttentionSnapshot> {
    if (session.requiresSession && !session.unlocked) {
      throw new Error("Operator session required");
    }
    const parsed = navAttentionPersistenceStateSchema.parse(state);
    const optimistic: NavAttentionSnapshot = {
      source: snapshot.source || "file",
      updatedAt: new Date().toISOString(),
      routeCount: Object.keys(parsed).length,
      state: parsed,
    };
    queryClient.setQueryData(OPERATOR_NAV_ATTENTION_QUERY_KEY, optimistic);
    try {
      const next = await mutateNavAttention(parsed);
      queryClient.setQueryData(OPERATOR_NAV_ATTENTION_QUERY_KEY, next);
      return next;
    } catch (error) {
      queryClient.invalidateQueries({ queryKey: OPERATOR_NAV_ATTENTION_QUERY_KEY }).catch(() => undefined);
      throw error;
    }
  }

  return {
    ...query,
    source: snapshot.source,
    updatedAt: snapshot.updatedAt,
    routeCount: snapshot.routeCount,
    state: snapshot.state,
    saveState,
  } as const;
}
