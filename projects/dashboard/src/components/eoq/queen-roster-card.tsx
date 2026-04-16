"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/empty-state";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { getProjectById } from "@/lib/config";
import { cn } from "@/lib/utils";

interface QueenTrait {
  name: string;
  value: number;
}

interface QueenRelationship {
  target: string;
  type: string;
}

interface Queen {
  id: string;
  name: string;
  title: string;
  archetype: string;
  resistance: number;
  corruption: number;
  speechStylePreview: string;
  topTraits: QueenTrait[];
  relationships: QueenRelationship[];
}

interface QueensResponse {
  queens: Queen[];
  archetypeColors: Record<string, string>;
}

const FALLBACK_ARCHETYPE_COLORS: Record<string, string> = {
  warrior: "oklch(0.55 0.08 230)",
  defiant: "oklch(0.55 0.08 230)",
  sorceress: "oklch(0.55 0.12 290)",
  priestess: "oklch(0.55 0.12 290)",
  seductress: "oklch(0.55 0.15 15)",
  ice: "oklch(0.7 0.08 230)",
  fire: "oklch(0.65 0.15 50)",
  shadow: "oklch(0.4 0.12 300)",
  sun: "oklch(0.75 0.12 80)",
  innocent: "oklch(0.7 0.1 350)",
};

function getBreakingStage(resistance: number): string {
  if (resistance >= 80) return "Defiant";
  if (resistance >= 60) return "Struggling";
  if (resistance >= 40) return "Conflicted";
  if (resistance >= 20) return "Yielding";
  if (resistance >= 1) return "Surrendered";
  return "Broken";
}

function archetypeColor(archetype: string, colors: Record<string, string>): string {
  return colors[archetype] ?? FALLBACK_ARCHETYPE_COLORS[archetype] ?? "oklch(0.5 0.05 250)";
}

function archetypeForeground(archetype: string): string {
  const dark = new Set(["shadow", "warrior", "defiant", "sorceress", "priestess", "seductress"]);
  return dark.has(archetype) ? "oklch(0.95 0.01 60)" : "oklch(0.15 0.01 60)";
}

export function QueenRosterCard() {
  const [selectedQueen, setSelectedQueen] = useState<Queen | null>(null);

  const { data, isLoading } = useQuery<QueensResponse>({
    queryKey: ["eoq", "queens"],
    queryFn: async () => {
      const res = await fetch("/api/eoq/queens");
      if (!res.ok) throw new Error("Failed to fetch queens");
      return res.json();
    },
    staleTime: 60_000,
  });

  const queens = data?.queens ?? [];
  const colors = data?.archetypeColors ?? FALLBACK_ARCHETYPE_COLORS;

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-hide">
        <span className="shrink-0 text-xs font-medium text-muted-foreground">Council</span>
        <div className="flex items-center gap-1.5">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-9 w-9 animate-pulse rounded-full bg-muted" />
          ))}
        </div>
      </div>
    );
  }

  if (queens.length === 0) {
    return null;
  }

  return (
    <>
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-hide">
        <span className="shrink-0 text-xs font-medium text-muted-foreground" style={{ fontFamily: "'Cormorant Garamond', serif" }}>
          Council
        </span>
        <div className="flex items-center gap-1.5">
          {queens.map((queen) => {
            const bg = archetypeColor(queen.archetype, colors);
            const fg = archetypeForeground(queen.archetype);
            return (
              <button
                key={queen.id}
                onClick={() => setSelectedQueen(queen)}
                className={cn(
                  "group relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-bold transition-all",
                  "hover:scale-110 hover:ring-2 hover:ring-primary/50"
                )}
                style={{ backgroundColor: bg, color: fg }}
                title={`${queen.name} — ${queen.title}`}
              >
                {queen.name[0]}
                <span className="pointer-events-none absolute -bottom-6 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-popover px-1.5 py-0.5 text-[10px] text-popover-foreground opacity-0 shadow transition-opacity group-hover:opacity-100">
                  {queen.name.split(" ")[0]}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <Sheet open={!!selectedQueen} onOpenChange={(open) => !open && setSelectedQueen(null)}>
        <SheetContent side="right" className="overflow-y-auto">
          {selectedQueen && (
            <QueenDetail queen={selectedQueen} colors={colors} />
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}

function QueenDetail({ queen, colors }: { queen: Queen; colors: Record<string, string> }) {
  const bg = archetypeColor(queen.archetype, colors);
  const eoqUrl = getProjectById("eoq")?.externalUrl ?? "http://interface.athanor.local:3002/";

  return (
    <>
      <SheetHeader>
        <div className="flex items-center gap-3">
          <div
            className="flex h-12 w-12 items-center justify-center rounded-full text-lg font-bold"
            style={{ backgroundColor: bg, color: archetypeForeground(queen.archetype) }}
          >
            {queen.name[0]}
          </div>
          <div>
            <SheetTitle style={{ fontFamily: "'Cormorant Garamond', serif" }}>
              {queen.name}
            </SheetTitle>
            <SheetDescription>{queen.title}</SheetDescription>
          </div>
        </div>
      </SheetHeader>

      <div className="space-y-5 px-4 pb-4">
        <div className="flex flex-wrap gap-2">
          <Badge style={{ backgroundColor: bg, color: archetypeForeground(queen.archetype) }}>
            {queen.archetype}
          </Badge>
          <Badge variant="outline">{getBreakingStage(queen.resistance)}</Badge>
        </div>

        <div className="space-y-2">
          <div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Resistance</span>
              <span className="font-mono">{queen.resistance}/100</span>
            </div>
            <div className="mt-1 h-2 rounded-full bg-muted">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${queen.resistance}%`,
                  backgroundColor: queen.resistance > 60 ? "oklch(0.6 0.15 25)" : queen.resistance > 30 ? "oklch(0.7 0.15 80)" : "oklch(0.5 0.15 300)",
                }}
              />
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Corruption</span>
              <span className="font-mono">{queen.corruption}/100</span>
            </div>
            <div className="mt-1 h-2 rounded-full bg-muted">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${queen.corruption}%`,
                  backgroundColor: "oklch(0.5 0.2 300)",
                  opacity: 0.4 + (queen.corruption / 100) * 0.6,
                }}
              />
            </div>
          </div>
        </div>

        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Voice</p>
          <p className="mt-1 text-sm italic text-muted-foreground">{queen.speechStylePreview}</p>
        </div>

        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Top traits</p>
          <div className="mt-2 space-y-2">
            {queen.topTraits.map((trait) => (
              <div key={trait.name} className="flex items-center gap-3">
                <span className="w-20 text-sm capitalize">{trait.name}</span>
                <div className="h-2 flex-1 rounded-full bg-muted">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${trait.value * 100}%`,
                      backgroundColor: bg,
                      opacity: 0.5 + trait.value * 0.5,
                    }}
                  />
                </div>
                <span className="w-8 text-right font-mono text-xs text-muted-foreground">
                  {(trait.value * 100).toFixed(0)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {queen.relationships.length > 0 && (
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Relationships</p>
            <div className="mt-2 space-y-1">
              {queen.relationships.map((rel, i) => (
                <div key={i} className="surface-tile flex items-center justify-between rounded-xl border px-3 py-2 text-sm">
                  <span>{rel.target}</span>
                  <Badge variant="secondary">{rel.type}</Badge>
                </div>
              ))}
            </div>
          </div>
        )}

        <a
          href={eoqUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 inline-flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/10 px-4 py-2 text-sm font-medium text-primary transition hover:bg-primary/20"
        >
          Play EoBQ
        </a>
      </div>
    </>
  );
}
