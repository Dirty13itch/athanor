"use client";

import { useLens } from "@/hooks/use-lens";
import { LENS_CONFIG, LENS_IDS, type LensId } from "@/lib/lens";
import { cn } from "@/lib/utils";

export function LensTabs() {
  const { config: activeConfig, setLens } = useLens();

  return (
    <div className="flex items-center gap-0.5 overflow-x-auto rounded-xl bg-muted/50 p-0.5 scrollbar-hide sm:gap-1 sm:p-1">
      {LENS_IDS.map((id) => {
        const isActive = activeConfig.id === id;
        return (
          <button
            key={id}
            type="button"
            onClick={() => setLens(id as LensId)}
            className={cn(
              "flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-medium transition min-h-[36px] sm:min-h-[auto] sm:gap-1.5 sm:px-3 sm:text-sm",
              "whitespace-nowrap",
              isActive
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-background/50"
            )}
            style={isActive ? { boxShadow: `inset 0 -2px 0 ${LENS_CONFIG[id as LensId].accent}` } : undefined}
          >
            <span
              className="flex h-4 w-4 items-center justify-center rounded text-[10px] font-bold sm:h-5 sm:w-5 sm:text-xs"
              style={{
                backgroundColor: isActive ? activeConfig.accent : undefined,
                color: isActive ? "oklch(0.12 0.01 60)" : undefined,
              }}
            >
              {LENS_CONFIG[id as LensId].icon}
            </span>
            <span className="hidden sm:inline">{LENS_CONFIG[id as LensId].label}</span>
          </button>
        );
      })}
    </div>
  );
}
