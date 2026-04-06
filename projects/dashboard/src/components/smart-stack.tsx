"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/empty-state";
import { isOperatorSessionLocked, useOperatorSessionStatus } from "@/lib/operator-session";

type TimeContext = "morning" | "afternoon" | "evening" | "night";

interface TaskStats {
  completed: number;
  failed: number;
  running: number;
  pending: number;
  total: number;
  pendingApproval: number;
  staleLease: number;
  failedActionable: number;
  failedHistoricalRepaired: number;
}

interface PatternReport {
  patterns: { type: string; severity: string; agent?: string; count?: number; success_rate?: number }[];
  recommendations: string[];
}

interface OperatorSummaryPayload {
  tasks?: {
    total?: number;
    by_status?: Record<string, number>;
    completed?: number;
    failed?: number;
    running?: number;
    pending?: number;
    pending_approval?: number;
    stale_lease?: number;
    failed_actionable?: number;
    failed_historical_repaired?: number;
  };
  patterns?: PatternReport;
}

interface StackData {
  taskStats: TaskStats | null;
  patterns: PatternReport | null;
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
    case "morning":
      return "Good morning";
    case "afternoon":
      return "Afternoon";
    case "evening":
      return "Evening";
    case "night":
      return "Overnight";
  }
}

function contextEmoji(ctx: TimeContext): string {
  switch (ctx) {
    case "morning":
      return "\u2600\uFE0F";
    case "afternoon":
      return "\u26A1";
    case "evening":
      return "\uD83C\uDF19";
    case "night":
      return "\uD83D\uDD53";
  }
}

export function SmartStack() {
  const session = useOperatorSessionStatus();
  const locked = isOperatorSessionLocked(session);
  const [ctx] = useState<TimeContext>(getTimeContext);
  const [data, setData] = useState<StackData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (locked) {
      setData(null);
      setLoading(false);
      return;
    }

    let mounted = true;

    async function fetchData() {
      try {
        const operatorRes = await fetch("/api/operator/summary", {
          signal: AbortSignal.timeout(5000),
        }).catch(() => null);

        let taskStats: TaskStats | null = null;
        let patterns: PatternReport | null = null;
        if (operatorRes?.ok) {
          const operator = (await operatorRes.json()) as OperatorSummaryPayload;
          const taskSummary = operator?.tasks;
          const byStatus = taskSummary?.by_status ?? {};
          taskStats = taskSummary
            ? {
                completed: taskSummary.completed ?? byStatus.completed ?? 0,
                failed: taskSummary.failed ?? byStatus.failed ?? 0,
                running: taskSummary.running ?? byStatus.running ?? 0,
                pending: taskSummary.pending ?? byStatus.pending ?? 0,
                total: taskSummary.total ?? 0,
                pendingApproval: taskSummary.pending_approval ?? byStatus.pending_approval ?? 0,
                staleLease: taskSummary.stale_lease ?? byStatus.stale_lease ?? 0,
                failedActionable: taskSummary.failed_actionable ?? 0,
                failedHistoricalRepaired: taskSummary.failed_historical_repaired ?? 0,
              }
            : null;
          patterns = operator?.patterns ?? null;
        }

        if (mounted) {
          setData({ taskStats, patterns });
          setLoading(false);
        }
      } catch {
        if (mounted) setLoading(false);
      }
    }

    void fetchData();
    const interval = setInterval(() => {
      void fetchData();
    }, 30000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [locked]);

  if (locked) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <span>{contextEmoji(ctx)}</span>
            <span>{contextLabel(ctx)}</span>
            <span className="ml-auto text-xs font-normal text-muted-foreground">Smart Stack</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="Unlock required"
            description="The smart stack stays quiet until the operator session is unlocked."
            className="py-6"
          />
        </CardContent>
      </Card>
    );
  }

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
  const approvalHeld = stats?.pendingApproval ?? 0;
  const actionableFailures = stats?.failedActionable ?? 0;
  const staleLeases = stats?.staleLease ?? 0;
  const repairedHistory = stats?.failedHistoricalRepaired ?? 0;

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
          <span className="ml-auto text-xs font-normal text-muted-foreground">Smart Stack</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {approvalHeld > 0 && (
          <a
            href="/operator"
            className="flex items-center gap-2 rounded-md border border-primary/25 bg-primary/10 px-3 py-2 text-xs transition-colors hover:bg-primary/15"
          >
            <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
            <span className="font-medium text-primary">
              {approvalHeld} approval-held task{approvalHeld > 1 ? "s" : ""}
            </span>
          </a>
        )}

        {stats && (
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <span className="text-muted-foreground">Task plane:</span>
            {stats.completed > 0 && (
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
                {stats.completed} done
              </span>
            )}
            {stats.running > 0 && (
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
                {stats.running} running
              </span>
            )}
            {actionableFailures > 0 && (
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
                {actionableFailures} actionable failure{actionableFailures > 1 ? "s" : ""}
              </span>
            )}
            {staleLeases > 0 && (
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                {staleLeases} stale lease{staleLeases > 1 ? "s" : ""}
              </span>
            )}
            {repairedHistory > 0 && (
              <span className="flex items-center gap-1 text-muted-foreground">
                <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60" />
                {repairedHistory} repaired historical
              </span>
            )}
            {stats.total === 0 && <span className="text-muted-foreground">No tasks yet</span>}
          </div>
        )}

        {warnings.length > 0 && (
          <div className="space-y-1">
            {warnings.slice(0, 3).map((w, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-muted-foreground">
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

        {recommendations.length > 0 && ctx === "morning" && (
          <div className="space-y-1 border-t border-border pt-2">
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Recommendations
            </span>
            {recommendations.slice(0, 2).map((r, i) => (
              <p key={i} className="text-xs leading-relaxed text-muted-foreground">
                {r}
              </p>
            ))}
          </div>
        )}

        {ctx === "morning" && !stats?.total && !approvalHeld && !warnings.length && (
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
