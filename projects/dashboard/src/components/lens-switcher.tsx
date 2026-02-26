"use client";

import { useLens } from "@/hooks/use-lens";
import { LENS_IDS, LENS_CONFIG } from "@/lib/lens";
import { cn } from "@/lib/utils";

export function LensSwitcher() {
  const { lens, setLens } = useLens();

  return (
    <div className="flex items-center gap-1.5 px-4 py-2">
      {LENS_IDS.map((id) => {
        const cfg = LENS_CONFIG[id];
        const active = lens === id;
        return (
          <button
            key={id}
            onClick={() => setLens(id)}
            className={cn(
              "flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold transition-all",
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
          </button>
        );
      })}
    </div>
  );
}
