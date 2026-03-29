"use client";

import { useQuery } from "@tanstack/react-query";

export interface OperatorSessionStatus {
  configured: boolean;
  fixtureMode: boolean;
  requiresSession: boolean;
  unlocked: boolean;
  sessionIdPresent: boolean;
}

const DEFAULT_OPERATOR_SESSION_STATUS: OperatorSessionStatus = {
  configured: false,
  fixtureMode: false,
  requiresSession: false,
  unlocked: true,
  sessionIdPresent: false,
};

const OPERATOR_SESSION_QUERY_KEY = ["operator-session-status"] as const;

async function fetchOperatorSessionStatus(): Promise<OperatorSessionStatus> {
  const response = await fetch("/api/operator/session", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  const payload = (await response.json()) as Partial<OperatorSessionStatus>;
  return {
    configured: Boolean(payload.configured),
    fixtureMode: Boolean(payload.fixtureMode),
    requiresSession: Boolean(payload.requiresSession),
    unlocked: Boolean(payload.unlocked ?? !payload.configured),
    sessionIdPresent: Boolean(payload.sessionIdPresent),
  };
}

export function useOperatorSessionStatus() {
  const query = useQuery({
    queryKey: OPERATOR_SESSION_QUERY_KEY,
    queryFn: fetchOperatorSessionStatus,
    staleTime: 15_000,
    gcTime: 5 * 60_000,
    retry: 1,
  });

  const snapshot = query.data ?? DEFAULT_OPERATOR_SESSION_STATUS;
  return {
    ...query,
    ...snapshot,
  } as const;
}

export function isOperatorSessionLocked(
  session: Pick<OperatorSessionStatus, "requiresSession" | "unlocked">
) {
  return session.requiresSession && !session.unlocked;
}
