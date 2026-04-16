"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Brain } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { formatRelativeTime } from "@/lib/format";
import queensData from "@/data/eoq-queens.json";

interface MemorySummary {
  characterId: string;
  memoryCount: number;
  lastInteraction: string | null;
  avgImportance: number;
  topMemoryText: string;
}

const archetypeColors = queensData.archetypeColors as Record<string, string>;

function queenById(id: string) {
  return queensData.queens.find((q) => q.id === id);
}

export function CharacterMemoryCard() {
  const [selectedMemory, setSelectedMemory] = useState<MemorySummary | null>(null);

  const { data, isLoading } = useQuery<{ memories: MemorySummary[] }>({
    queryKey: ["eoq", "memories"],
    queryFn: async () => {
      const res = await fetch("/api/eoq/memories");
      if (!res.ok) throw new Error("Failed to fetch memories");
      return res.json();
    },
    staleTime: 60_000,
  });

  const memories = data?.memories ?? [];
  const maxCount = Math.max(1, ...memories.map((m) => m.memoryCount));

  return (
    <>
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Brain className="h-5 w-5 text-primary" />
            <span style={{ fontFamily: "'Cormorant Garamond', serif" }}>Character memory</span>
          </CardTitle>
          <CardDescription>Persistent memory strength per queen.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-10 animate-pulse rounded-xl bg-muted" />
              ))}
            </div>
          ) : memories.length === 0 ? (
            <EmptyState
              title="No memories yet"
              description="Character memories build as you play. Each conversation and choice is remembered."
              icon={<Brain className="h-5 w-5" />}
            />
          ) : (
            memories.map((mem) => {
              const queen = queenById(mem.characterId);
              const color = queen ? archetypeColors[queen.archetype] ?? "oklch(0.5 0.05 250)" : "oklch(0.5 0.05 250)";
              const barWidth = (mem.memoryCount / maxCount) * 100;
              const intensity = 0.4 + Math.min(mem.avgImportance, 1) * 0.6;

              return (
                <button
                  key={mem.characterId}
                  onClick={() => setSelectedMemory(mem)}
                  className="surface-tile flex w-full items-center gap-3 rounded-xl border px-3 py-2 text-left transition hover:bg-accent/60"
                >
                  <div className="w-24 shrink-0">
                    <span className="text-sm font-medium">{queen?.name.split(" ")[0] ?? mem.characterId}</span>
                    {queen && (
                      <Badge
                        variant="secondary"
                        className="ml-1 text-[10px]"
                        style={{ backgroundColor: color, color: "oklch(0.95 0.01 60)", opacity: 0.8 }}
                      >
                        {queen.archetype}
                      </Badge>
                    )}
                  </div>
                  <div className="h-3 flex-1 rounded-full bg-muted">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${barWidth}%`,
                        backgroundColor: color,
                        opacity: intensity,
                      }}
                    />
                  </div>
                  <span className="w-8 shrink-0 text-right font-mono text-xs text-muted-foreground">
                    {mem.memoryCount}
                  </span>
                  {mem.lastInteraction && (
                    <span className="hidden w-16 shrink-0 text-right text-xs text-muted-foreground sm:block" data-volatile="true">
                      {formatRelativeTime(mem.lastInteraction)}
                    </span>
                  )}
                </button>
              );
            })
          )}
        </CardContent>
      </Card>

      <Sheet open={!!selectedMemory} onOpenChange={(open) => !open && setSelectedMemory(null)}>
        <SheetContent side="right" className="overflow-y-auto">
          {selectedMemory && (
            <MemoryDetail memory={selectedMemory} />
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}

function MemoryDetail({ memory }: { memory: MemorySummary }) {
  const queen = queenById(memory.characterId);
  const color = queen ? archetypeColors[queen.archetype] ?? "oklch(0.5 0.05 250)" : "oklch(0.5 0.05 250)";

  return (
    <>
      <SheetHeader>
        <SheetTitle style={{ fontFamily: "'Cormorant Garamond', serif" }}>
          {queen?.name ?? memory.characterId}
        </SheetTitle>
        <SheetDescription>
          {memory.memoryCount} memories stored
        </SheetDescription>
      </SheetHeader>
      <div className="space-y-4 px-4 pb-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="surface-instrument rounded-xl border p-3">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Count</p>
            <p className="mt-1 text-lg font-semibold">{memory.memoryCount}</p>
          </div>
          <div className="surface-instrument rounded-xl border p-3">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Avg importance</p>
            <p className="mt-1 text-lg font-semibold">{(memory.avgImportance * 100).toFixed(0)}%</p>
          </div>
        </div>
        {memory.lastInteraction && (
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Last interaction</p>
            <p className="mt-1 text-sm" data-volatile="true">{formatRelativeTime(memory.lastInteraction)}</p>
          </div>
        )}
        {memory.topMemoryText && (
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Top memory</p>
            <p className="mt-1 text-sm italic text-muted-foreground">{memory.topMemoryText}</p>
          </div>
        )}
        {queen && (
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Archetype</p>
            <Badge className="mt-1" style={{ backgroundColor: color, color: "oklch(0.95 0.01 60)" }}>
              {queen.archetype}
            </Badge>
          </div>
        )}
      </div>
    </>
  );
}
