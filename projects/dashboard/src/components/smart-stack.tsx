"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type TimeContext = "morning" | "afternoon" | "evening" | "night";

interface TaskStats {
  completed: number;
  failed: number;
  running: number;
  pending: number;
  total: number;
}

interface PatternReport {
  patterns: { type: string; severity: string; agent?: string; count?: number; success_rate?: number }[];
  recommendations: string[];
}

interface StackData {
  taskStats: TaskStats | null;
  patterns: PatternReport | null;
  pendingApprovals: number;
}

function getTimeContext(): TimeContext {
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 11) return "morning";
  if (hour >= 11 && hour < 17) return "afternoon";
  if (hour >= 17 && hour < 23) return "evening";
  return "night";
}

function contextLabel(ctx: TimeContext): string {
  switch (ctx) {
    case "morning": return "Good morning";
    case "afternoon": return "Afternoon";
    case "evening": return "Evening";
    case "night": return "Overnight";
  }
}

function contextEmoji(ctx: TimeContext): string {
  switch (ctx) {
    case "morning": return "\u2600\uFE0F";
    case "afternoon": return "\u26A1";
    case "evening": return "\uD83C\uDF19";
    case "night": return "\uD83D\uDD53";
  }
}

export function SmartStack() {
  const [ctx] = useState<TimeContext>(getTimeContext);
  const [data, setData] = useState<StackData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    async function fetchData() {
      try {
        const [workforceRes, patternsRes] = await Promise.all([
          fetch("/api/workforce", { signal: AbortSignal.timeout(5000) }).catch(() => null),
          fetch("/api/insights", { signal: AbortSignal.timeout(5000) }).catch(() => null),
        ]);

        let taskStats: TaskStats | null = null;
        let pendingApprovals = 0;
        if (workforceRes?.ok) {
          const workforce = await workforceRes.json();
          taskStats = workforce?.summary
            ? {
                completed: workforce.summary.completedTasks ?? 0,
                failed: workforce.summary.failedTasks ?? 0,
                running: workforce.summary.runningTasks ?? 0,
                pending: workforce.summary.pendingTasks ?? 0,
                total: workforce.summary.totalTasks ?? 0,
              }
            : null;
          pendingApprovals = workforce?.summary?.pendingApprovals ?? 0;
        }
        const patterns = patternsRes?.ok ? await patternsRes.json() : null;

        if (mounted) {
          setData({ taskStats, patterns, pendingApprovals });
          setLoading(false);
        }
      } catch {
        if (mounted) setLoading(false);
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  if (loading) {
    return (
      <Card>
        <CardContent className="py-4">
          <div className="h-4 w-32 animate-pulse rounded bg-muted" />
        </CardContent>
      </Card>
    );
  }

  const stats = data?.taskStats;
  const patterns = data?.patterns;
  const approvals = data?.pendingApprovals ?? 0;

  // Filter actionable patterns
  const warnings = (patterns?.patterns ?? []).filter(
    (p) => p.severity === "high" || p.severity === "medium"
  );
  const recommendations = patterns?.recommendations ?? [];

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <span>{contextEmoji(ctx)}</span>
          <span>{contextLabel(ctx)}</span>
          <span className="text-xs font-normal text-muted-foreground ml-auto">
            Smart Stack
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Pending approvals — always show if any */}
        {approvals > 0 && (
          <a
            href="/tasks?status=approval"
            className="flex items-center gap-2 rounded-md bg-amber-500/10 border border-amber-500/20 px-3 py-2 text-xs hover:bg-amber-500/15 transition-colors"
          >
            <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
            <span className="font-medium text-amber-200">
              {approvals} pending approval{approvals > 1 ? "s" : ""}
            </span>
          </a>
        )}

        {/* Task summary */}
        {stats && (
          <div className="flex items-center gap-3 text-xs">
            <span className="text-muted-foreground">Tasks (24h):</span>
            {stats.completed > 0 && (
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
                {stats.completed} done
              </span>
            )}
            {stats.running > 0 && (
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
                {stats.running} running
              </span>
            )}
            {stats.failed > 0 && (
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
                {stats.failed} failed
              </span>
            )}
            {stats.total === 0 && (
              <span className="text-muted-foreground">No tasks yet</span>
            )}
          </div>
        )}

        {/* Pattern warnings */}
        {warnings.length > 0 && (
          <div className="space-y-1">
            {warnings.slice(0, 3).map((w, i) => (
              <div
                key={i}
                className="flex items-center gap-2 text-xs text-muted-foreground"
              >
                <Badge
                  variant={w.severity === "high" ? "destructive" : "outline"}
                  className="text-[10px] px-1.5 py-0"
                >
                  {w.type.replace(/_/g, " ")}
                </Badge>
                {w.agent && <span className="font-mono">{w.agent}</span>}
                {w.count && <span>({w.count}x)</span>}
              </div>
            ))}
          </div>
        )}

        {/* Recommendations */}
        {recommendations.length > 0 && ctx === "morning" && (
          <div className="space-y-1 border-t border-border pt-2">
            <span className="text-[10px] uppercase text-muted-foreground tracking-wider">
              Recommendations
            </span>
            {recommendations.slice(0, 2).map((r, i) => (
              <p key={i} className="text-xs text-muted-foreground leading-relaxed">
                {r}
              </p>
            ))}
          </div>
        )}

        {/* Context-specific content */}
        {ctx === "morning" && !stats?.total && !approvals && !warnings.length && (
          <p className="text-xs text-muted-foreground">
            All clear. No overnight issues detected.
          </p>
        )}

        {ctx === "night" && (
          <p className="text-xs text-muted-foreground">
            Scheduled tasks running autonomously. Pattern detection at 5:00 AM.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
