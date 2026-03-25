"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Flame } from "lucide-react";
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
      usage: `~${Math.min(45, Math.floor(estimatedCloudTasks / 3))} sessions`,
      burnPercent: Math.min(100, Math.floor((estimatedCloudTasks / 3 / 45) * 100)),
    },
    {
      name: "Gemini",
      cost: 20,
      limit: "1000/day free",
      usage: `~${Math.min(1000, tasksToday * 2)}/day`,
      burnPercent: Math.min(100, Math.floor((tasksToday * 2 / 1000) * 100)),
    },
    {
      name: "Local (Qwen3.5)",
      cost: 0,
      limit: "Unlimited",
      usage: `${tasksToday} tasks today`,
      burnPercent: tasksToday > 0 ? 100 : 0,
    },
  ];

  const totalMonthlyCost = 543;
  const estimatedUtilization = subs.reduce((sum, s) => sum + s.burnPercent * s.cost, 0) / totalMonthlyCost;

  return (
    <Card className="surface-instrument border">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Flame className="h-5 w-5 text-primary" />
          Furnace burn rate
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            ${totalMonthlyCost}/mo subscriptions
          </span>
          <span className="font-mono font-semibold">
            {Math.round(estimatedUtilization)}% utilized
          </span>
        </div>

        <div className="h-2 rounded-full bg-muted overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${Math.min(100, Math.round(estimatedUtilization))}%`,
              backgroundColor:
                estimatedUtilization >= 60
                  ? "var(--signal-success)"
                  : estimatedUtilization >= 30
                    ? "var(--signal-warning)"
                    : "var(--signal-danger)",
            }}
          />
        </div>

        <div className="space-y-1.5">
          {subs.map((sub) => (
            <div key={sub.name} className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">{sub.name}</span>
              <div className="flex items-center gap-2">
                <span className="font-mono">{sub.usage}</span>
                <div className="h-1.5 w-12 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${sub.burnPercent}%`,
                      backgroundColor:
                        sub.burnPercent >= 60
                          ? "var(--signal-success)"
                          : sub.burnPercent >= 30
                            ? "var(--signal-warning)"
                            : "var(--signal-danger)",
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        {tasksRunning > 0 && (
          <p className="text-xs text-muted-foreground pt-1">
            {tasksRunning} task{tasksRunning !== 1 ? "s" : ""} actively burning tokens
          </p>
        )}
      </CardContent>
    </Card>
  );
}
