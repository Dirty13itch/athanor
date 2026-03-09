"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface LearningMetrics {
  timestamp: string;
  metrics: {
    cache: { total_entries: number; hit_rate: number; tokens_saved: number; avg_similarity: number } | null;
    circuits: { services: number; open: number; half_open: number; closed: number; total_failures: number } | null;
    preferences: { model_task_pairs: number; total_samples: number; avg_composite_score: number; converged: number } | null;
    trust: { agents_tracked: number; avg_trust_score: number; high_trust: number; low_trust: number } | null;
    diagnosis: { recent_failures: number; patterns_detected: number; auto_remediations: number } | null;
    memory: { collections: number; total_points: number } | null;
    tasks: { total: number; completed: number; failed: number; success_rate: number } | null;
  };
  summary: {
    overall_health: number;
    data_points: number;
    positive_signals: string[];
    assessment: string;
  };
}

interface PatternReport {
  timestamp: string;
  period_hours: number;
  event_count: number;
  activity_count: number;
  patterns: Array<{ type: string; severity: string; [key: string]: unknown }>;
  recommendations: string[];
  autonomy_adjustments: Array<{
    agent: string;
    category: string;
    previous: number;
    delta: number;
    new: number;
  }>;
}

interface ImprovementSummary {
  total_proposals: number;
  pending: number;
  validated: number;
  deployed: number;
  failed: number;
  benchmark_results: number;
}

function HealthGauge({ score, assessment }: { score: number; assessment: string }) {
  const pct = Math.round(score * 100);
  const color = score > 0.8 ? "text-green-400" : score > 0.6 ? "text-emerald-400" : score > 0.3 ? "text-yellow-400" : "text-zinc-500";
  const bg = score > 0.8 ? "bg-green-400/20" : score > 0.6 ? "bg-emerald-400/20" : score > 0.3 ? "bg-yellow-400/20" : "bg-zinc-500/20";

  return (
    <div className="flex flex-col items-center gap-2">
      <div className={`text-5xl font-bold ${color}`}>{pct}%</div>
      <div className={`px-3 py-1 rounded-full text-sm font-medium ${bg} ${color}`}>
        {assessment}
      </div>
    </div>
  );
}

function MetricCard({ title, children, available }: { title: string; children: React.ReactNode; available: boolean }) {
  return (
    <Card className={available ? "" : "opacity-50"}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {available ? children : <p className="text-xs text-muted-foreground">No data yet</p>}
      </CardContent>
    </Card>
  );
}

function StatRow({ label, value, unit }: { label: string; value: string | number; unit?: string }) {
  return (
    <div className="flex justify-between items-center py-1">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-sm font-mono">
        {value}{unit && <span className="text-xs text-muted-foreground ml-1">{unit}</span>}
      </span>
    </div>
  );
}

export default function LearningPage() {
  const [data, setData] = useState<LearningMetrics | null>(null);
  const [patterns, setPatterns] = useState<PatternReport | null>(null);
  const [improvement, setImprovement] = useState<ImprovementSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runningBenchmark, setRunningBenchmark] = useState(false);

  const fetchAll = useCallback(async () => {
    const [pRes, iRes] = await Promise.allSettled([
      fetch("/api/agents/proxy?path=/v1/patterns"),
      fetch("/api/agents/proxy?path=/v1/improvement/summary"),
    ]);
    if (pRes.status === "fulfilled" && pRes.value.ok) setPatterns(await pRes.value.json());
    if (iRes.status === "fulfilled" && iRes.value.ok) setImprovement(await iRes.value.json());
  }, []);

  const fetchMetrics = useCallback(async () => {
    try {
      const res = await fetch("/api/agents/proxy?path=/v1/learning/metrics");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
    fetchAll();
    const iv = setInterval(() => { fetchMetrics(); fetchAll(); }, 30000);
    return () => clearInterval(iv);
  }, [fetchMetrics, fetchAll]);

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <h1 className="text-2xl font-bold">Learning Metrics</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(7)].map((_, i) => (
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

  if (error || !data) {
    return (
      <div className="p-6 space-y-6">
        <h1 className="text-2xl font-bold">Learning Metrics</h1>
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            {error || "Unable to load metrics"}. Agent server may be unavailable.
          </CardContent>
        </Card>
      </div>
    );
  }

  const { metrics, summary } = data;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Learning Metrics</h1>
          <p className="text-sm text-muted-foreground">
            Is the system actually learning? Compound improvement tracking.
          </p>
        </div>
        <button
          onClick={() => { fetchMetrics(); fetchAll(); }}
          className="px-3 py-1.5 text-sm border rounded-md hover:bg-muted transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Overall Health */}
      <Card>
        <CardContent className="p-6 flex flex-col md:flex-row items-center gap-6">
          <HealthGauge score={summary.overall_health} assessment={summary.assessment} />
          <div className="flex-1 space-y-2">
            <CardDescription>
              Computed from {summary.data_points} data sources
            </CardDescription>
            {summary.positive_signals.length > 0 ? (
              <ul className="space-y-1">
                {summary.positive_signals.map((s, i) => (
                  <li key={i} className="text-sm flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                    {s}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">
                System is in cold start — metrics will appear as data accumulates.
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <MetricCard title="Semantic Cache" available={!!metrics.cache}>
          {metrics.cache && (
            <div className="space-y-0.5">
              <StatRow label="Entries" value={metrics.cache.total_entries} />
              <StatRow label="Hit Rate" value={`${(metrics.cache.hit_rate * 100).toFixed(1)}`} unit="%" />
              <StatRow label="Tokens Saved" value={metrics.cache.tokens_saved.toLocaleString()} />
              <StatRow label="Avg Similarity" value={metrics.cache.avg_similarity.toFixed(3)} />
            </div>
          )}
        </MetricCard>

        <MetricCard title="Circuit Breakers" available={!!metrics.circuits}>
          {metrics.circuits && (
            <div className="space-y-0.5">
              <StatRow label="Services" value={metrics.circuits.services} />
              <StatRow label="Closed (healthy)" value={metrics.circuits.closed} />
              <StatRow label="Open (tripped)" value={metrics.circuits.open} />
              <StatRow label="Half-Open" value={metrics.circuits.half_open} />
              <StatRow label="Total Failures" value={metrics.circuits.total_failures} />
            </div>
          )}
        </MetricCard>

        <MetricCard title="Preference Learning" available={!!metrics.preferences && metrics.preferences.model_task_pairs > 0}>
          {metrics.preferences && (
            <div className="space-y-0.5">
              <StatRow label="Model-Task Pairs" value={metrics.preferences.model_task_pairs} />
              <StatRow label="Total Samples" value={metrics.preferences.total_samples} />
              <StatRow label="Converged" value={metrics.preferences.converged} />
              <StatRow label="Avg Score" value={metrics.preferences.avg_composite_score.toFixed(3)} />
            </div>
          )}
        </MetricCard>

        <MetricCard title="Agent Trust" available={!!metrics.trust && metrics.trust.agents_tracked > 0}>
          {metrics.trust && (
            <div className="space-y-0.5">
              <StatRow label="Agents Tracked" value={metrics.trust.agents_tracked} />
              <StatRow label="Avg Trust" value={metrics.trust.avg_trust_score.toFixed(3)} />
              <StatRow label="High Trust (>0.7)" value={metrics.trust.high_trust} />
              <StatRow label="Low Trust (<0.3)" value={metrics.trust.low_trust} />
            </div>
          )}
        </MetricCard>

        <MetricCard title="Self-Diagnosis" available={!!metrics.diagnosis}>
          {metrics.diagnosis && (
            <div className="space-y-0.5">
              <StatRow label="Recent Failures" value={metrics.diagnosis.recent_failures} />
              <StatRow label="Patterns Detected" value={metrics.diagnosis.patterns_detected} />
              <StatRow label="Auto-Remediations" value={metrics.diagnosis.auto_remediations} />
            </div>
          )}
        </MetricCard>

        <MetricCard title="Memory" available={!!metrics.memory}>
          {metrics.memory && (
            <div className="space-y-0.5">
              <StatRow label="Collections" value={metrics.memory.collections} />
              <StatRow label="Total Points" value={metrics.memory.total_points.toLocaleString()} />
            </div>
          )}
        </MetricCard>

        <MetricCard title="Task Execution" available={!!metrics.tasks && metrics.tasks.total > 0}>
          {metrics.tasks && (
            <div className="space-y-0.5">
              <StatRow label="Total" value={metrics.tasks.total} />
              <StatRow label="Completed" value={metrics.tasks.completed} />
              <StatRow label="Failed" value={metrics.tasks.failed} />
              <StatRow label="Success Rate" value={`${(metrics.tasks.success_rate * 100).toFixed(1)}`} unit="%" />
            </div>
          )}
        </MetricCard>
      </div>

      {/* Autonomy Adjustments */}
      {patterns && patterns.autonomy_adjustments.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Autonomy Adjustments</CardTitle>
            <CardDescription>
              Dynamic threshold changes from pattern detection · last run {new Date(patterns.timestamp).toLocaleTimeString()}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {patterns.autonomy_adjustments.map((adj, i) => {
                const isMore = adj.delta > 0;
                const isLess = adj.delta < 0;
                return (
                  <div key={i} className="flex items-center justify-between py-1.5 border-b last:border-0 border-border/50">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium">{adj.agent}</span>
                      <span className="text-xs text-muted-foreground">{adj.category}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs font-mono">
                      <span className="text-muted-foreground">{adj.previous.toFixed(3)}</span>
                      <span className={isMore ? "text-green-400" : isLess ? "text-red-400" : "text-zinc-500"}>
                        {isMore ? "+" : ""}{adj.delta.toFixed(3)}
                      </span>
                      <span className="font-medium">{adj.new.toFixed(3)}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${isMore ? "bg-green-500/10 text-green-400" : isLess ? "bg-red-500/10 text-red-400" : "bg-zinc-500/10 text-zinc-400"}`}>
                        {isMore ? "more autonomous" : isLess ? "more cautious" : "unchanged"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Improvement Cycle */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">Self-Improvement Cycle</CardTitle>
              <CardDescription>5 AM daily: benchmark → patterns → proposals</CardDescription>
            </div>
            <button
              onClick={async () => {
                setRunningBenchmark(true);
                try {
                  await fetch("/api/agents/proxy?path=/v1/improvement/benchmarks/run", { method: "POST" });
                  await fetchAll();
                } finally {
                  setRunningBenchmark(false);
                }
              }}
              disabled={runningBenchmark}
              className="px-3 py-1.5 text-xs border rounded-md hover:bg-muted disabled:opacity-50"
            >
              {runningBenchmark ? "Running..." : "Run Benchmarks"}
            </button>
          </div>
        </CardHeader>
        <CardContent>
          {improvement ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: "Proposals", value: improvement.total_proposals, color: "text-blue-400" },
                { label: "Pending Review", value: improvement.pending, color: "text-yellow-400" },
                { label: "Deployed", value: improvement.deployed, color: "text-green-400" },
                { label: "Benchmarks Run", value: improvement.benchmark_results, color: "text-cyan-400" },
              ].map(({ label, value, color }) => (
                <div key={label} className="text-center p-3 rounded-lg bg-muted/30">
                  <div className={`text-2xl font-bold ${color}`}>{value}</div>
                  <div className="text-xs text-muted-foreground mt-1">{label}</div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">No improvement data yet. Runs at 5:00 AM daily.</p>
          )}
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground text-center">
        Last updated: {new Date(data.timestamp).toLocaleString()} · Auto-refreshes every 30s
      </p>
    </div>
  );
}
