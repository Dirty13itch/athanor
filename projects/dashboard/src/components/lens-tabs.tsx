"use client";

import { useLens } from "@/hooks/use-lens";
import { LENS_CONFIG, LENS_IDS, type LensId } from "@/lib/lens";
import { cn } from "@/lib/utils";

export function LensTabs() {
  const { config: activeConfig, setLens } = useLens();

  return (
    <div className="flex items-center gap-1 overflow-x-auto rounded-xl bg-muted/50 p-1">
      {LENS_IDS.map((id) => {
        const isActive = activeConfig.id === id;
        return (
          <button
            key={id}
            type="button"
            onClick={() => setLens(id as LensId)}
            className={cn(
              "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition",
              "whitespace-nowrap",
              isActive
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-background/50"
            )}
            style={isActive ? { boxShadow: `inset 0 -2px 0 ${LENS_CONFIG[id as LensId].accent}` } : undefined}
          >
            <span
              className="flex h-5 w-5 items-center justify-center rounded text-xs font-bold"
              style={{
                backgroundColor: isActive ? activeConfig.accent : undefined,
                color: isActive ? "oklch(0.12 0.01 60)" : undefined,
              }}
            >
              {LENS_CONFIG[id as LensId].icon}
            </span>
            {LENS_CONFIG[id as LensId].label}
          </button>
        );
      })}
    </div>
  );
}
