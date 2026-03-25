"use client";

import { useSystemStream } from "@/hooks/use-system-stream";

interface SubTier {
  name: string;
  cost: number;
  limit: string;
  usage: string;
  burnPercent: number;
}

/**
 * Subscription burn rate card — shows how well we're utilizing
 * paid AI subscriptions. The goal is to burn every token before it resets.
 *
 * TODO: Wire to actual usage tracking via LiteLLM /spend endpoint
 * or subscription-specific APIs. Currently uses heuristic estimates
 * from task counts and model usage patterns.
 */
export function SubscriptionBurn() {
  const { data: stream } = useSystemStream();

  // Heuristic burn estimates from live task data
  const tasksToday = stream?.tasks?.by_status?.completed ?? 0;
  const tasksRunning = stream?.tasks?.currently_running ?? 0;

  // Estimate burn from task volume and known routing patterns
  // Local tasks (scheduler-sourced) use Qwen3.5 = $0
  // Chat tasks use cloud = counted
  const estimatedCloudTasks = Math.max(0, tasksToday - Math.floor(tasksToday * 0.8));

  const subs: SubTier[] = [
    {
      name: "Claude Max",
      cost: 200,
      limit: "~45 Opus/mo",
      usage: `~${Math.min(45, Math.floor(estimatedCloudTasks / 3))}`,
      burnPercent: Math.min(100, Math.floor((estimatedCloudTasks / 3 / 45) * 100)),
    },
    {
      name: "Gemini",
      cost: 20,
      limit: "1000/day free",
      usage: `~${Math.min(1000, tasksToday * 2)}`,
      burnPercent: Math.min(100, Math.floor((tasksToday * 2 / 1000) * 100)),
    },
    {
      name: "Local",
      cost: 0,
      limit: "Unlimited",
      usage: `${tasksToday}`,
      burnPercent: tasksToday > 0 ? 100 : 0,
    },
  ];

  const totalMonthlyCost = 543;
  const estimatedUtilization = subs.reduce((sum, s) => sum + s.burnPercent * s.cost, 0) / totalMonthlyCost;

  /** Gradient from red (low) through amber to green (high). */
  function burnGradient(pct: number): string {
    if (pct >= 60) return "linear-gradient(90deg, var(--signal-warning), var(--signal-success))";
    if (pct >= 30) return "linear-gradient(90deg, var(--signal-danger), var(--signal-warning))";
    return "var(--signal-danger)";
  }

  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between">
        <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground/50">Furnace burn</p>
        <span className="font-mono text-xs font-bold tabular-nums">
          {Math.round(estimatedUtilization)}%
        </span>
      </div>

      {/* Main burn bar with gradient */}
      <div className="h-1.5 rounded-full bg-muted/30 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${Math.min(100, Math.round(estimatedUtilization))}%`,
            background: burnGradient(estimatedUtilization),
          }}
        />
      </div>

      {/* Per-sub rows — compact */}
      <div className="space-y-1">
        {subs.map((sub) => (
          <div key={sub.name} className="flex items-center gap-2 text-[11px]">
            <span className="text-muted-foreground/60 w-16 truncate">{sub.name}</span>
            <div className="flex-1 h-1 rounded-full bg-muted/20 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${sub.burnPercent}%`,
                  background: burnGradient(sub.burnPercent),
                }}
              />
            </div>
            <span className="font-mono tabular-nums text-muted-foreground/60 w-10 text-right">{sub.usage}</span>
          </div>
        ))}
      </div>

      {tasksRunning > 0 && (
        <p className="text-[10px] text-muted-foreground/40">
          {tasksRunning} burning
        </p>
      )}
    </div>
  );
}
