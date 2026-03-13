"use client";

import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { NavAttentionSignal, OverviewSnapshot } from "@/lib/contracts";
import {
  createNavAttentionMap,
  resolveNavAttentionPresentation,
  type NavAttentionPersistenceState,
  type NavAttentionPresentation,
} from "@/lib/nav-attention";
import { STORAGE_KEYS, usePersistentState } from "@/lib/state";

interface NavAttentionContextValue {
  getAttention: (routeHref: string, activeSurface?: boolean) => NavAttentionPresentation;
  getSignal: (routeHref: string) => NavAttentionSignal | null;
}

const NavAttentionContext = createContext<NavAttentionContextValue | null>(null);

function usePrefersReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }

    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const handleChange = () => setPrefersReducedMotion(mediaQuery.matches);
    handleChange();

    if (typeof mediaQuery.addEventListener === "function") {
      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    }

    mediaQuery.addListener(handleChange);
    return () => mediaQuery.removeListener(handleChange);
  }, []);

  return prefersReducedMotion;
}

function useDocumentVisible() {
  const [visible, setVisible] = useState(() =>
    typeof document === "undefined" ? true : document.visibilityState === "visible"
  );

  useEffect(() => {
    if (typeof document === "undefined") {
      return;
    }

    const handleVisibilityChange = () => setVisible(document.visibilityState === "visible");
    handleVisibilityChange();
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, []);

  return visible;
}

export function NavAttentionProvider({
  overview,
  pathname,
  children,
}: {
  overview: OverviewSnapshot | undefined;
  pathname: string;
  children: ReactNode;
}) {
  const prefersReducedMotion = usePrefersReducedMotion();
  const tabVisible = useDocumentVisible();
  const [state, setState] = usePersistentState<NavAttentionPersistenceState>(
    STORAGE_KEYS.navAttention,
    {}
  );

  const signals = overview?.navAttention ?? [];
  const signalMap = useMemo(() => createNavAttentionMap(signals), [signals]);

  useEffect(() => {
    if (!overview) {
      return;
    }

    const now = new Date().toISOString();
    setState((current) => {
      const next: NavAttentionPersistenceState = { ...current };
      let changed = false;
      const activeRoutes = new Set<string>();

      for (const signal of signals) {
        activeRoutes.add(signal.routeHref);

        if (signal.tier === "none") {
          if (signal.routeHref in next) {
            delete next[signal.routeHref];
            changed = true;
          }
          continue;
        }

        const existing = next[signal.routeHref];
        if (!existing || existing.signature !== signal.signature) {
          next[signal.routeHref] = {
            signature: signal.signature,
            firstSeenAt: now,
            acknowledgedAt: null,
          };
          changed = true;
        }
      }

      for (const routeHref of Object.keys(next)) {
        if (!activeRoutes.has(routeHref)) {
          delete next[routeHref];
          changed = true;
        }
      }

      const activeSignal = signalMap.get(pathname);
      if (activeSignal && activeSignal.tier !== "none") {
        const existing = next[pathname];
        if (existing && existing.signature === activeSignal.signature && !existing.acknowledgedAt) {
          next[pathname] = {
            ...existing,
            acknowledgedAt: now,
          };
          changed = true;
        }
      }

      return changed ? next : current;
    });
  }, [overview, pathname, setState, signalMap, signals]);

  const value = useMemo<NavAttentionContextValue>(() => {
    const getSignal = (routeHref: string) => signalMap.get(routeHref) ?? null;

    const getAttention = (routeHref: string, activeSurface = pathname === routeHref) =>
      resolveNavAttentionPresentation(signalMap.get(routeHref), state[routeHref], {
        activeSurface,
        tabVisible,
        reducedMotion: prefersReducedMotion,
      });

    return { getAttention, getSignal };
  }, [pathname, prefersReducedMotion, signalMap, state, tabVisible]);

  return <NavAttentionContext.Provider value={value}>{children}</NavAttentionContext.Provider>;
}

export function useNavAttention(routeHref: string, activeSurface = false) {
  const context = useContext(NavAttentionContext);
  if (!context) {
    return resolveNavAttentionPresentation(null, undefined, {
      activeSurface,
      tabVisible: true,
      reducedMotion: false,
    });
  }

  return context.getAttention(routeHref, activeSurface);
}
