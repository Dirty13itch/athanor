"use client";

import { useEffect, useState } from "react";
import { useLens } from "@/hooks/use-lens";
import { LENS_IDS, LENS_CONFIG } from "@/lib/lens";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";

/** Map lens IDs to service health check URLs */
const LENS_HEALTH: Partial<Record<string, string>> = {
  eoq: "/api/eoq/queens",
  system: "/api/overview",
  media: "/api/media/overview",
};

export function LensSwitcher() {
  const { lens, setLens } = useLens();
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
  }, []);

  // Quick health check for each lens (lightweight, infrequent)
  const healthQuery = useQuery({
    queryKey: ["lens-health"],
    queryFn: async () => {
      const results: Record<string, boolean> = {};
      await Promise.all(
        Object.entries(LENS_HEALTH).map(async ([id, url]) => {
          try {
            const resp = await fetch(url!, { signal: AbortSignal.timeout(5000) });
            results[id] = resp.ok;
          } catch {
            results[id] = false;
          }
        }),
      );
      return results;
    },
    refetchInterval: 60_000,
    staleTime: 30_000,
    enabled: hydrated,
  });

  const health = hydrated ? healthQuery.data ?? {} : {};

  return (
    <div className="flex items-center gap-1.5 px-4 py-2">
      {LENS_IDS.map((id) => {
        const cfg = LENS_CONFIG[id];
        const active = lens === id;
        const hasHealthCheck = id in LENS_HEALTH;
        const isHealthy = health[id];

        return (
          <button
            key={id}
            onClick={() => setLens(id)}
            className={cn(
              "relative flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold transition-all",
              active
                ? "ring-2 ring-offset-1 ring-offset-background scale-110"
                : "opacity-50 hover:opacity-80 border border-border"
            )}
            style={
              active
                ? { backgroundColor: cfg.accent, color: "#111", "--tw-ring-color": cfg.accent } as React.CSSProperties
                : undefined
            }
            title={cfg.label}
          >
            {cfg.icon}
            {/* Health dot */}
            {hasHealthCheck && (
              <span
                className={cn(
                  "absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full border border-background",
                  isHealthy === true ? "bg-emerald-500" :
                  isHealthy === false ? "bg-red-500" :
                  "bg-muted"
                )}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
