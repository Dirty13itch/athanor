"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Goal, RefreshCcw, ShieldCheck, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { getWorkforce } from "@/lib/api";
import { type WorkforceGoal, type WorkforceSnapshot } from "@/lib/contracts";
import { formatPercent, formatRelativeTime, formatTimestamp } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import { deleteRequest, getAgentName, postJson } from "@/features/workforce/helpers";

function priorityTone(priority: WorkforceGoal["priority"]) {
  if (priority === "high") {
    return "destructive";
  }
  if (priority === "low") {
    return "outline";
  }
  return "secondary";
}

export function GoalsConsole({ initialSnapshot }: { initialSnapshot: WorkforceSnapshot }) {
  const [feedback, setFeedback] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [agentId, setAgentId] = useState("global");
  const [priority, setPriority] = useState<WorkforceGoal["priority"]>("normal");

  const workforceQuery = useQuery({
    queryKey: queryKeys.workforce,
    queryFn: getWorkforce,
    initialData: initialSnapshot,
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });
  const snapshot = workforceQuery.data ?? initialSnapshot;
  const activeGoals = snapshot.goals.filter((goal) => goal.active);
  const topTrust = useMemo(
    () => snapshot.trust.slice().sort((left, right) => right.trustScore - left.trustScore),
    [snapshot.trust]
  );

  async function handleAction(action: string, run: () => Promise<void>) {
    setBusy(action);
    setFeedback(null);
    try {
      await run();
      await workforceQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Request failed.");
    } finally {
      setBusy(null);
    }
  }

  if (workforceQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Workforce" title="Goals and Trust" description="The workforce goals snapshot failed to load." />
        <ErrorPanel
          description={
            workforceQuery.error instanceof Error
              ? workforceQuery.error.message
              : "Failed to load workforce data."
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Workforce"
        title="Goals and Trust"
        description="Steering goals, trust posture, and self-improvement visibility for the operator loop."
        actions={
          <Button variant="outline" onClick={() => void workforceQuery.refetch()} disabled={workforceQuery.isFetching}>
            <RefreshCcw className={`mr-2 h-4 w-4 ${workforceQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Active goals" value={`${activeGoals.length}`} detail="Live steering context for the workforce." icon={<Goal className="h-5 w-5" />} />
          <StatCard label="Average trust" value={formatPercent(snapshot.summary.avgTrustScore)} detail={`${snapshot.trust.length} agents with trust samples.`} icon={<ShieldCheck className="h-5 w-5" />} />
          <StatCard label="Pending proposals" value={`${snapshot.improvement?.pending ?? 0}`} detail={`${snapshot.improvement?.deployed ?? 0} improvement proposals already deployed.`} icon={<Sparkles className="h-5 w-5" />} />
          <StatCard label="Unread notifications" value={`${snapshot.summary.unreadNotifications}`} detail="Signals that may require operator judgment." />
        </div>
      </PageHeader>

      {feedback ? <ErrorPanel title="Goals feedback" description={feedback} /> : null}

      <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <Card className="border-border/70 bg-card/70">
          <CardHeader>
            <CardTitle className="text-lg">Steering goals</CardTitle>
            <CardDescription>Persistent direction shaping planner runs and agent choices.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-[1fr_180px_160px_auto]">
              <input
                type="text"
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder="Add a goal for Athanor or EoBQ."
                className="w-full rounded-xl border border-border/70 bg-background/30 px-3 py-2 text-sm outline-none transition focus:border-primary"
              />
              <label htmlFor="goal-agent-selector" className="sr-only">
                Assign goal to agent
              </label>
              <select
                id="goal-agent-selector"
                aria-label="Assign goal to agent"
                value={agentId}
                onChange={(event) => setAgentId(event.target.value)}
                className="w-full rounded-xl border border-border/70 bg-background/30 px-3 py-2 text-sm outline-none transition focus:border-primary"
              >
                <option value="global">All agents</option>
                {snapshot.agents.map((entry) => (
                  <option key={entry.id} value={entry.id}>
                    {entry.name}
                  </option>
                ))}
              </select>
              <label htmlFor="goal-priority-selector" className="sr-only">
                Goal priority
              </label>
              <select
                id="goal-priority-selector"
                aria-label="Goal priority"
                value={priority}
                onChange={(event) => setPriority(event.target.value as WorkforceGoal["priority"])}
                className="w-full rounded-xl border border-border/70 bg-background/30 px-3 py-2 text-sm outline-none transition focus:border-primary"
              >
                {["low", "normal", "high"].map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
              <Button
                onClick={() =>
                  void handleAction("create-goal", async () => {
                    await postJson("/api/workforce/goals", {
                      text: text.trim(),
                      agent: agentId,
                      priority,
                    });
                    setText("");
                    setAgentId("global");
                    setPriority("normal");
                  })
                }
                disabled={busy === "create-goal" || !text.trim()}
              >
                Add goal
              </Button>
            </div>

            {activeGoals.length > 0 ? (
              <div className="space-y-3">
                {activeGoals.map((goal) => (
                  <div key={goal.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={priorityTone(goal.priority)}>{goal.priority}</Badge>
                      <Badge variant="secondary">
                        {goal.agentId === "global" ? "All agents" : getAgentName(snapshot, goal.agentId)}
                      </Badge>
                      <span className="text-xs text-muted-foreground">{formatRelativeTime(goal.createdAt)}</span>
                    </div>
                    <p className="mt-3 text-sm">{goal.text}</p>
                    <div className="mt-3">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                          void handleAction(`delete:${goal.id}`, () =>
                            deleteRequest(`/api/workforce/goals/${goal.id}`)
                          )
                        }
                      >
                        Remove
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="No active goals" description="Add a steering goal to shape the next planner cycle." className="py-8" />
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="border-border/70 bg-card/70">
            <CardHeader>
              <CardTitle className="text-lg">Trust posture</CardTitle>
              <CardDescription>Feedback and escalation-derived confidence by agent.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {topTrust.length > 0 ? (
                topTrust.map((entry) => (
                  <div key={entry.agentId} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                      <p className="font-medium">{getAgentName(snapshot, entry.agentId)}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {entry.positiveFeedback} up / {entry.negativeFeedback} down / {entry.escalationCount} escalations
                      </p>
                    </div>
                      <Badge variant="outline">{formatPercent(entry.trustScore)}</Badge>
                    </div>
                    <div className="mt-3 h-2 rounded-full bg-background/70">
                      <div className="h-full rounded-full bg-primary" style={{ width: `${Math.round(entry.trustScore * 100)}%` }} />
                    </div>
                  </div>
                ))
              ) : (
                <EmptyState title="No trust samples yet" description="Feedback and escalation data will appear here once available." className="py-8" />
              )}
            </CardContent>
          </Card>

          <Card className="border-border/70 bg-card/70">
            <CardHeader>
              <CardTitle className="text-lg">Improvement engine</CardTitle>
              <CardDescription>Systemic learning and proposal deployment posture.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {snapshot.improvement ? (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <Metric label="Proposals" value={`${snapshot.improvement.totalProposals}`} />
                    <Metric label="Deployed" value={`${snapshot.improvement.deployed}`} />
                    <Metric label="Validated" value={`${snapshot.improvement.validated}`} />
                    <Metric label="Benchmarks" value={`${snapshot.improvement.benchmarkResults}`} />
                  </div>
                  {snapshot.improvement.lastCycle ? (
                    <div className="rounded-2xl border border-border/70 bg-background/20 p-4">
                      <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">Last cycle</p>
                      <p className="mt-2 text-sm">
                        {snapshot.improvement.lastCycle.patternsConsumed} patterns produced{" "}
                        {snapshot.improvement.lastCycle.proposalsGenerated} proposals.
                      </p>
                      <p className="mt-2 text-xs text-muted-foreground">
                        {snapshot.improvement.lastCycle.benchmarks
                          ? `${snapshot.improvement.lastCycle.benchmarks.passed}/${snapshot.improvement.lastCycle.benchmarks.total} benchmarks passed`
                          : "No benchmark results recorded"}
                      </p>
                      <p className="mt-2 text-xs text-muted-foreground">
                        {formatTimestamp(snapshot.improvement.lastCycle.timestamp)}
                      </p>
                    </div>
                  ) : null}
                </>
              ) : (
                <EmptyState title="Improvement engine unavailable" description="No self-improvement summary is currently available." className="py-8" />
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/30 px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 font-medium">{value}</p>
    </div>
  );
}
