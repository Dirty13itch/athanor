import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  operatorUiPreferencesSnapshotSchema,
  uiPreferencesSchema,
  type OperatorUiPreferencesSnapshot,
  type UiPreferences,
} from "@/lib/contracts";
import { fetchJson } from "@/lib/http";
import {
  DEFAULT_UI_PREFERENCES,
  LEGACY_STORAGE_KEYS,
  readJsonStorage,
  removeStorageKey,
} from "@/lib/state";
import { useOperatorSessionStatus } from "@/lib/operator-session";

const OPERATOR_UI_PREFERENCES_QUERY_KEY = ["operator-ui-preferences"] as const;

const EMPTY_UI_PREFERENCES_SNAPSHOT: OperatorUiPreferencesSnapshot = {
  source: "file",
  updatedAt: "",
  preferences: { ...DEFAULT_UI_PREFERENCES },
};

function uiPreferencesEqual(left: UiPreferences, right: UiPreferences): boolean {
  return (
    left.density === right.density &&
    left.lastSelectedAgentId === right.lastSelectedAgentId &&
    left.lastSelectedModelKey === right.lastSelectedModelKey &&
    left.dismissedHints.length === right.dismissedHints.length &&
    left.dismissedHints.every((hint, index) => hint === right.dismissedHints[index])
  );
}

async function mutateUiPreferences(
  preferences: UiPreferences
): Promise<OperatorUiPreferencesSnapshot> {
  const payload = uiPreferencesSchema.parse(preferences);
  const response = await fetch("/api/operator/ui-preferences", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }

  return operatorUiPreferencesSnapshotSchema.parse(await response.json());
}

export async function fetchOperatorUiPreferences(): Promise<OperatorUiPreferencesSnapshot> {
  return fetchJson(
    "/api/operator/ui-preferences",
    { cache: "no-store" },
    operatorUiPreferencesSnapshotSchema
  );
}

export function useOperatorUiPreferences() {
  const session = useOperatorSessionStatus();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: OPERATOR_UI_PREFERENCES_QUERY_KEY,
    queryFn: fetchOperatorUiPreferences,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    enabled: !session.requiresSession || session.unlocked,
  });

  const snapshot = query.data ?? EMPTY_UI_PREFERENCES_SNAPSHOT;

  async function setPreferences(
    next: UiPreferences | ((current: UiPreferences) => UiPreferences)
  ): Promise<OperatorUiPreferencesSnapshot> {
    if (session.requiresSession && !session.unlocked) {
      throw new Error("Operator session required");
    }
    const resolved = uiPreferencesSchema.parse(
      typeof next === "function" ? next(snapshot.preferences) : next
    );
    const optimistic: OperatorUiPreferencesSnapshot = {
      source: snapshot.source || "file",
      updatedAt: new Date().toISOString(),
      preferences: resolved,
    };
    queryClient.setQueryData(OPERATOR_UI_PREFERENCES_QUERY_KEY, optimistic);
    try {
      const committed = await mutateUiPreferences(resolved);
      queryClient.setQueryData(OPERATOR_UI_PREFERENCES_QUERY_KEY, committed);
      return committed;
    } catch (error) {
      queryClient.invalidateQueries({ queryKey: OPERATOR_UI_PREFERENCES_QUERY_KEY }).catch(
        () => undefined
      );
      throw error;
    }
  }

  useEffect(() => {
    if (session.requiresSession && !session.unlocked) {
      return;
    }
    if (!query.isFetched) {
      return;
    }

    const legacy = readJsonStorage<UiPreferences>(
      LEGACY_STORAGE_KEYS.uiPreferences,
      DEFAULT_UI_PREFERENCES
    );

    if (snapshot.updatedAt) {
      removeStorageKey(LEGACY_STORAGE_KEYS.uiPreferences);
      return;
    }

    if (!uiPreferencesEqual(legacy, DEFAULT_UI_PREFERENCES)) {
      void setPreferences(legacy)
        .then(() => removeStorageKey(LEGACY_STORAGE_KEYS.uiPreferences))
        .catch(() => undefined);
    }
  }, [query.isFetched, session.requiresSession, session.unlocked, snapshot.updatedAt]);

  return {
    ...query,
    source: snapshot.source,
    updatedAt: snapshot.updatedAt,
    preferences: snapshot.preferences,
    setPreferences,
  } as const;
}
