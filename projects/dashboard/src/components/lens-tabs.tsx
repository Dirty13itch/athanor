"use client";

import { useLens } from "@/hooks/use-lens";
import { LENS_CONFIG, LENS_IDS, type LensId } from "@/lib/lens";
import { cn } from "@/lib/utils";

export function LensTabs() {
  const { config: activeConfig, setLens } = useLens();

  return (
    <div className="flex items-center gap-0 rounded-lg bg-muted/30 p-0.5">
      {LENS_IDS.map((id) => {
        const isActive = activeConfig.id === id;
        const cfg = LENS_CONFIG[id as LensId];
        return (
          <button
            key={id}
            type="button"
            onClick={() => setLens(id as LensId)}
            className={cn(
              "flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-all",
              "whitespace-nowrap",
              isActive
                ? "text-foreground shadow-sm"
                : "text-muted-foreground/60 hover:text-foreground"
            )}
            style={isActive ? {
              backgroundColor: `color-mix(in srgb, ${cfg.accent} 15%, transparent)`,
            } : undefined}
          >
            <span
              className="flex h-4 w-4 items-center justify-center rounded text-[10px] font-bold"
              style={{
                backgroundColor: isActive ? cfg.accent : undefined,
                color: isActive ? "oklch(0.12 0.01 60)" : undefined,
                opacity: isActive ? 1 : 0.5,
              }}
            >
              {cfg.icon}
            </span>
            <span className="hidden sm:inline">{cfg.label}</span>
          </button>
        );
      })}
    </div>
  );
}
