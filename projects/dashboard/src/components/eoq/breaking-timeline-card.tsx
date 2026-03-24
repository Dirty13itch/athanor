"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { cn } from "@/lib/utils";

interface QueenBreakingPoint {
  queenName: string;
  queenId: string;
  archetype: string;
  resistance: number;
  corruption: number;
}

interface QueensResponse {
  queens: QueenBreakingPoint[];
}

const STAGE_COLORS: Record<string, string> = {
  defiant: "bg-red-500",
  struggling: "bg-orange-500",
  conflicted: "bg-yellow-500",
  yielding: "bg-emerald-500",
  surrendered: "bg-purple-500",
  broken: "bg-slate-500",
};

function getStage(resistance: number): string {
  if (resistance >= 80) return "defiant";
  if (resistance >= 60) return "struggling";
  if (resistance >= 40) return "conflicted";
  if (resistance >= 20) return "yielding";
  if (resistance >= 1) return "surrendered";
  return "broken";
}

export function BreakingTimelineCard() {
  const { data, isLoading } = useQuery<QueensResponse>({
    queryKey: ["eoq", "queens-breaking"],
    queryFn: async () => {
      const resp = await fetch("/api/eoq/queens");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return resp.json();
    },
    refetchInterval: 30_000,
  });

  const queens = data?.queens ?? [];

  // Sort by resistance (most broken first) for visual impact
  const sorted = [...queens].sort((a, b) => a.resistance - b.resistance);

  return (
    <Card className="border-border/70 bg-card/70">
      <CardHeader>
        <CardTitle className="text-lg">Breaking Progress</CardTitle>
        <CardDescription>Resistance levels across the empire</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-8 animate-pulse rounded bg-muted" />
            ))}
          </div>
        )}

        {!isLoading && sorted.length === 0 && (
          <EmptyState
            title="No queens tracked"
            description="Play EoBQ to see breaking progress here."
            className="py-6"
          />
        )}

        {sorted.length > 0 && (
          <div className="space-y-2">
            {sorted.map((queen) => {
              const stage = getStage(queen.resistance);
              const stageColor = STAGE_COLORS[stage] ?? "bg-muted";
              return (
                <div key={queen.queenId ?? queen.queenName} className="group">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium truncate max-w-[120px]">
                      {queen.queenName}
                    </span>
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <span>{queen.resistance}%</span>
                      <span className={cn(
                        "rounded-full px-1.5 py-0.5 text-[10px] font-medium",
                        stage === "broken" ? "bg-slate-500/20 text-slate-400" :
                        stage === "surrendered" ? "bg-purple-500/20 text-purple-400" :
                        stage === "defiant" ? "bg-red-500/20 text-red-400" :
                        "bg-muted text-muted-foreground"
                      )}>
                        {stage}
                      </span>
                    </div>
                  </div>
                  {/* Resistance bar */}
                  <div className="mt-1 h-2 w-full rounded-full bg-muted/50 overflow-hidden">
                    <div
                      className={cn("h-full rounded-full transition-all duration-500", stageColor)}
                      style={{ width: `${queen.resistance}%` }}
                    />
                  </div>
                  {/* Corruption overlay */}
                  {queen.corruption > 0 && (
                    <div className="mt-0.5 h-1 w-full rounded-full bg-muted/30 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-purple-500/60 transition-all duration-500"
                        style={{ width: `${queen.corruption}%` }}
                      />
                    </div>
                  )}
                </div>
              );
            })}

            {/* Summary stats */}
            <div className="mt-3 flex justify-between text-[11px] text-muted-foreground border-t border-border/50 pt-2">
              <span>
                Broken: {sorted.filter(q => q.resistance === 0).length}/{sorted.length}
              </span>
              <span>
                Avg resistance: {Math.round(sorted.reduce((sum, q) => sum + q.resistance, 0) / sorted.length)}%
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
