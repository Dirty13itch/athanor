"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface Goal {
  id: string;
  text: string;
  agent: string;
  priority: string;
  created_at: number;
  active: boolean;
}

interface TrustScore {
  agent: string;
  trust_score: number;
  positive_feedback: number;
  negative_feedback: number;
  total_feedback: number;
  escalation_count: number;
}

interface ImprovementSummary {
  total_proposals: number;
  pending: number;
  validated: number;
  deployed: number;
  failed: number;
  benchmark_results: number;
  last_cycle: {
    timestamp: string;
    patterns_consumed: number;
    proposals_generated: number;
    benchmarks: { passed: number; total: number; pass_rate: number } | null;
  } | null;
}

function TrustBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    score > 0.7
      ? "bg-green-400"
      : score > 0.4
        ? "bg-yellow-400"
        : "bg-red-400";
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm font-mono w-10 text-right">{pct}%</span>
    </div>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    high: "bg-red-400/20 text-red-400",
    normal: "bg-blue-400/20 text-blue-400",
    low: "bg-zinc-400/20 text-zinc-400",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[priority] || colors.normal}`}>
      {priority}
    </span>
  );
}

export default function GoalsPage() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [trust, setTrust] = useState<TrustScore[]>([]);
  const [improvement, setImprovement] = useState<ImprovementSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [newGoalText, setNewGoalText] = useState("");
  const [newGoalAgent] = useState("global");
  const [newGoalPriority, setNewGoalPriority] = useState("normal");

  const fetchData = useCallback(async () => {
    try {
      const [goalsRes, trustRes, improvRes] = await Promise.all([
        fetch("/api/agents/proxy?path=/v1/goals"),
        fetch("/api/agents/proxy?path=/v1/trust"),
        fetch("/api/agents/proxy?path=/v1/improvement/summary"),
      ]);
      if (goalsRes.ok) {
        const g = await goalsRes.json();
        setGoals(g.goals || []);
      }
      if (trustRes.ok) {
        const t = await trustRes.json();
        setTrust(t.scores || []);
      }
      if (improvRes.ok) {
        setImprovement(await improvRes.json());
      }
    } catch {
      // Silent fail — page shows empty state
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const iv = setInterval(fetchData, 30000);
    return () => clearInterval(iv);
  }, [fetchData]);

  const createGoal = async () => {
    if (!newGoalText.trim()) return;
    try {
      await fetch("/api/agents/proxy?path=/v1/goals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: newGoalText.trim(),
          agent: newGoalAgent,
          priority: newGoalPriority,
        }),
      });
      setNewGoalText("");
      fetchData();
    } catch {
      // Silent fail
    }
  };

  const deleteGoal = async (id: string) => {
    try {
      await fetch(`/api/agents/proxy?path=/v1/goals/${id}`, { method: "DELETE" });
      fetchData();
    } catch {
      // Silent fail
    }
  };

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <h1 className="text-2xl font-bold">Goals & Feedback</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="h-24 bg-muted animate-pulse rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Goals & Feedback</h1>
          <p className="text-sm text-muted-foreground">
            Steering goals, agent trust scores, and self-improvement cycle status.
          </p>
        </div>
        <button
          onClick={fetchData}
          className="px-3 py-1.5 text-sm border rounded-md hover:bg-muted transition-colors"
        >
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Steering Goals */}
        <Card className="lg:row-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Steering Goals</CardTitle>
            <CardDescription>
              Active directives that influence agent behavior via context injection.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Create goal form */}
            <div className="flex gap-2">
              <input
                type="text"
                value={newGoalText}
                onChange={(e) => setNewGoalText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && createGoal()}
                placeholder="Add a steering goal..."
                className="flex-1 px-3 py-2 text-sm bg-muted border rounded-md focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <select
                value={newGoalPriority}
                onChange={(e) => setNewGoalPriority(e.target.value)}
                className="px-2 py-2 text-sm bg-muted border rounded-md"
              >
                <option value="low">Low</option>
                <option value="normal">Normal</option>
                <option value="high">High</option>
              </select>
              <button
                onClick={createGoal}
                disabled={!newGoalText.trim()}
                className="px-3 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
              >
                Add
              </button>
            </div>

            {/* Goal list */}
            {goals.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                No active goals. Add one to steer agent behavior.
              </p>
            ) : (
              <div className="space-y-2">
                {goals.map((goal) => (
                  <div
                    key={goal.id}
                    className="flex items-start gap-3 p-3 rounded-md border border-border group"
                  >
                    <div className="flex-1 space-y-1">
                      <p className="text-sm">{goal.text}</p>
                      <div className="flex items-center gap-2">
                        <PriorityBadge priority={goal.priority} />
                        <span className="text-xs text-muted-foreground">
                          {goal.agent === "global" ? "All agents" : goal.agent}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => deleteGoal(goal.id)}
                      className="text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity text-sm"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Agent Trust Scores */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Agent Trust</CardTitle>
            <CardDescription>
              Derived from feedback history and escalation frequency.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {trust.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                No trust data yet. Send feedback via chat to build trust scores.
              </p>
            ) : (
              <div className="space-y-3">
                {trust
                  .sort((a, b) => b.trust_score - a.trust_score)
                  .map((t) => (
                    <div key={t.agent} className="space-y-1">
                      <div className="flex justify-between items-center">
                        <span className="text-sm font-medium">{t.agent}</span>
                        <span className="text-xs text-muted-foreground">
                          {t.positive_feedback}↑ {t.negative_feedback}↓
                        </span>
                      </div>
                      <TrustBar score={t.trust_score} />
                    </div>
                  ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Self-Improvement Cycle */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Self-Improvement</CardTitle>
            <CardDescription>
              Daily cycle: benchmarks → patterns → proposals → auto-deploy.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!improvement ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                Improvement engine not responding.
              </p>
            ) : (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-md bg-muted">
                    <p className="text-2xl font-bold">{improvement.total_proposals}</p>
                    <p className="text-xs text-muted-foreground">Total Proposals</p>
                  </div>
                  <div className="p-3 rounded-md bg-muted">
                    <p className="text-2xl font-bold">{improvement.deployed}</p>
                    <p className="text-xs text-muted-foreground">Deployed</p>
                  </div>
                  <div className="p-3 rounded-md bg-muted">
                    <p className="text-2xl font-bold">{improvement.validated}</p>
                    <p className="text-xs text-muted-foreground">Validated</p>
                  </div>
                  <div className="p-3 rounded-md bg-muted">
                    <p className="text-2xl font-bold">{improvement.benchmark_results}</p>
                    <p className="text-xs text-muted-foreground">Benchmarks Run</p>
                  </div>
                </div>
                {improvement.last_cycle && (
                  <div className="p-3 rounded-md border border-border space-y-1">
                    <p className="text-xs font-medium text-muted-foreground">Last Cycle</p>
                    <p className="text-sm">
                      {improvement.last_cycle.benchmarks
                        ? `${improvement.last_cycle.benchmarks.passed}/${improvement.last_cycle.benchmarks.total} benchmarks passed`
                        : "No benchmark data"}
                    </p>
                    <p className="text-sm">
                      {improvement.last_cycle.patterns_consumed} patterns →{" "}
                      {improvement.last_cycle.proposals_generated} proposals
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(improvement.last_cycle.timestamp).toLocaleString()}
                    </p>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <p className="text-xs text-muted-foreground text-center">
        Auto-refreshes every 30s
      </p>
    </div>
  );
}
