"use client";

import { useEffect, useState } from "react";
import type { UiPreferences } from "@/lib/contracts";

export const STORAGE_KEYS = {
  uiPreferences: "athanor-ui-preferences",
  directChatSessions: "athanor-direct-chat-sessions",
  agentThreads: "athanor-agent-threads",
  promptHistory: "athanor-prompt-history",
  navAttention: "athanor-nav-attention-state",
} as const;

export const LEGACY_STORAGE_KEYS = {
  uiPreferences: "athanor-ui-preferences",
  directChatSessions: "athanor-direct-chat-sessions",
  agentThreads: "athanor-agent-threads",
  navAttention: "athanor-nav-attention-state",
} as const;

export function readJsonStorage<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") {
    return fallback;
  }

  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function writeJsonStorage<T>(key: string, value: T) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(key, JSON.stringify(value));
}

export function removeStorageKey(key: string) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(key);
}

export function usePersistentState<T>(key: string, fallback: T) {
  const [value, setValue] = useState<T>(() => readJsonStorage(key, fallback));
  const isHydrated = typeof window !== "undefined";

  useEffect(() => {
    if (!isHydrated) {
      return;
    }

    writeJsonStorage(key, value);
  }, [isHydrated, key, value]);

  return [value, setValue, isHydrated] as const;
}

export const DEFAULT_UI_PREFERENCES: UiPreferences = {
  density: "comfortable",
  lastSelectedAgentId: null,
  lastSelectedModelKey: null,
  dismissedHints: [],
};
