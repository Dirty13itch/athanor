"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Pattern {
  type: string;
  severity: "high" | "medium" | "low";
  agent?: string;
  count?: number;
  sample_errors?: string[];
  thumbs_up?: number;
  thumbs_down?: number;
  topics?: Record<string, number>;
  dominant_type?: string;
  actions?: Record<string, number>;
  [key: string]: unknown;
}

interface PatternReport {
  timestamp: string;
  period_hours: number;
  event_count: number;
  activity_count: number;
  patterns: Pattern[];
  recommendations: string[];
  autonomy_adjustments?: Array<{
    agent: string;
    category: string;
    previous: number;
    delta: number;
    new: number;
  }>;
  agent_behavioral_patterns?: Record<string, {
    topics?: Record<string, number>;
    content?: Record<string, number>;
    actions?: Record<string, number>;
    entity_count?: number;
    dominant_type?: string;
    dominant_topic?: string;
  }>;
}

const SEVERITY_COLORS: Record<string, string> = {
  high: "text-red-400 bg-red-400/10 border-red-400/20",
  medium: "text-yellow-400 bg-yellow-400/10 border-yellow-400/20",
  low: "text-zinc-400 bg-zinc-400/10 border-zinc-400/20",
};

const PATTERN_LABELS: Record<string, string> = {
  failure_cluster: "Failure Cluster",
  negative_feedback_trend: "Negative Feedback",
  high_escalation_rate: "High Escalation Rate",
  low_task_completion: "Low Completion",
  schedule_reliability_drop: "Schedule Slip",
  convention_extracted: "Convention Learned",
  autonomy_graduation: "Autonomy Graduation",
  media_content_preference: "Media Preferences",
  home_routine: "Home Routine Detected",
  research_topics: "Research Topics",
  creative_patterns: "Creative Output Pattern",
};

function PatternCard({ pattern }: { pattern: Pattern }) {
  const label = PATTERN_LABELS[pattern.type] ?? pattern.type.replace(/_/g, " ");
  const sev = pattern.severity ?? "low";
  const sevClass = SEVERITY_COLORS[sev] ?? SEVERITY_COLORS.low;

  return (
    <div className={`rounded border p-3 ${sevClass}`}>
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="text-sm font-medium">{label}</span>
        <div className="flex items-center gap-2">
          {pattern.agent && (
            <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] uppercase tracking-wider">
              {pattern.agent}
            </span>
          )}
          <span className="rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wider opacity-70">
            {sev}
          </span>
        </div>
      </div>

      {pattern.count !== undefined && (
        <p className="text-xs opacity-70">{pattern.count} occurrences in 24h</p>
      )}
      {pattern.thumbs_up !== undefined && (
        <p className="text-xs opacity-70">
          {pattern.thumbs_up}↑ {pattern.thumbs_down ?? 0}↓ feedback
        </p>
      )}
      {pattern.sample_errors && pattern.sample_errors.length > 0 && (
        <ul className="mt-1 space-y-0.5">
          {pattern.sample_errors.map((err, i) => (
            <li key={i} className="truncate text-[10px] opacity-50">
              {err}
            </li>
          ))}
        </ul>
      )}
      {pattern.topics && Object.keys(pattern.topics).length > 0 && (
        <div className="mt-1 flex flex-wrap gap-1">
          {Object.entries(pattern.topics)
            .sort(([, a], [, b]) => (b as number) - (a as number))
            .slice(0, 5)
            .map(([topic, count]) => (
              <span key={topic} className="rounded bg-white/10 px-1.5 py-0.5 text-[10px]">
                {topic} ×{count as number}
              </span>
            ))}
        </div>
      )}
    </div>
  );
}

export default function InsightsPage() {
  const [report, setReport] = useState<PatternReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [lastRun, setLastRun] = useState<string | null>(null);

  const fetchPatterns = useCallback(async () => {
    try {
      const resp = await fetch("/api/agents/proxy?path=/v1/patterns");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      if (data.patterns !== undefined) {
        setReport(data as PatternReport);
        setLastRun(data.timestamp ?? null);
      }
    } catch (err) {
      console.error("patterns fetch error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPatterns();
    const id = setInterval(fetchPatterns, 60_000);
    return () => clearInterval(id);
  }, [fetchPatterns]);

  async function triggerRun() {
    setTriggering(true);
    try {
      await fetch("/api/agents/proxy?path=/v1/patterns/run", { method: "POST" });
      await fetchPatterns();
    } finally {
      setTriggering(false);
    }
  }

  const highCount = report?.patterns.filter((p) => p.severity === "high").length ?? 0;
  const medCount = report?.patterns.filter((p) => p.severity === "medium").length ?? 0;

  const behavioralAgents = Object.entries(report?.agent_behavioral_patterns ?? {});

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Insights</h1>
          <p className="text-sm text-muted-foreground">
            Pattern detections from the last 24h of agent activity
          </p>
        </div>
        <button
          onClick={triggerRun}
          disabled={triggering}
          className="rounded border border-white/10 bg-white/5 px-4 py-2 text-sm text-muted-foreground transition-colors hover:border-white/20 hover:text-foreground disabled:opacity-50"
        >
          {triggering ? "Running…" : "Run Now"}
        </button>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-16">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/20 border-t-white/70" />
        </div>
      )}

      {!loading && !report && (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No pattern report yet. Runs automatically at 5:00 AM daily, or click &quot;Run Now&quot;.
          </CardContent>
        </Card>
      )}

      {report && (
        <>
          {/* Summary row */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Card>
              <CardHeader className="pb-1 pt-4">
                <CardTitle className="text-xs text-muted-foreground">Patterns</CardTitle>
              </CardHeader>
              <CardContent className="pb-4">
                <p className="text-3xl font-bold">{report.patterns.length}</p>
                <p className="text-xs text-muted-foreground">
                  {highCount > 0 && <span className="text-red-400">{highCount} high</span>}
                  {highCount > 0 && medCount > 0 && ", "}
                  {medCount > 0 && <span className="text-yellow-400">{medCount} medium</span>}
                  {highCount === 0 && medCount === 0 && "all low severity"}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1 pt-4">
                <CardTitle className="text-xs text-muted-foreground">Events Analyzed</CardTitle>
              </CardHeader>
              <CardContent className="pb-4">
                <p className="text-3xl font-bold">{report.event_count}</p>
                <p className="text-xs text-muted-foreground">{report.period_hours}h window</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1 pt-4">
                <CardTitle className="text-xs text-muted-foreground">Recommendations</CardTitle>
              </CardHeader>
              <CardContent className="pb-4">
                <p className="text-3xl font-bold">{report.recommendations.length}</p>
                <p className="text-xs text-muted-foreground">action items</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1 pt-4">
                <CardTitle className="text-xs text-muted-foreground">Last Run</CardTitle>
              </CardHeader>
              <CardContent className="pb-4">
                <p className="text-sm font-medium">
                  {lastRun
                    ? new Date(lastRun).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                    : "—"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {lastRun ? new Date(lastRun).toLocaleDateString() : "never"}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Patterns grid */}
          {report.patterns.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Detected Patterns</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 sm:grid-cols-2">
                  {report.patterns.map((p, i) => (
                    <PatternCard key={i} pattern={p} />
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Recommendations */}
          {report.recommendations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Recommendations</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {report.recommendations.map((rec, i) => (
                    <li key={i} className="flex gap-2 text-sm text-muted-foreground">
                      <span className="mt-0.5 h-4 w-4 shrink-0 text-amber-400">›</span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Autonomy adjustments */}
          {report.autonomy_adjustments && report.autonomy_adjustments.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Autonomy Threshold Adjustments</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {report.autonomy_adjustments.map((adj, i) => (
                    <div key={i} className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">
                        <span className="font-medium text-foreground">{adj.agent}</span>
                        {" · "}{adj.category}
                      </span>
                      <span className={adj.delta < 0 ? "text-green-400" : adj.delta > 0 ? "text-red-400" : "text-muted-foreground"}>
                        {adj.delta < 0 ? "▼" : adj.delta > 0 ? "▲" : "="}
                        {" "}{Math.abs(adj.delta * 100).toFixed(1)}%
                        <span className="ml-1 text-xs text-muted-foreground">
                          ({(adj.previous * 100).toFixed(0)} → {(adj.new * 100).toFixed(0)})
                        </span>
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Behavioral patterns by agent */}
          {behavioralAgents.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Agent Behavioral Patterns</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {behavioralAgents.map(([agent, beh]) => (
                    <div key={agent} className="rounded border border-white/5 p-3">
                      <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                        {agent}
                      </h3>
                      {beh.dominant_topic && (
                        <p className="mb-1 text-xs">
                          <span className="text-muted-foreground">Top topic: </span>
                          <span className="text-amber-400">{beh.dominant_topic}</span>
                        </p>
                      )}
                      {beh.dominant_type && (
                        <p className="mb-1 text-xs">
                          <span className="text-muted-foreground">Output type: </span>
                          <span className="text-amber-400">{beh.dominant_type}</span>
                        </p>
                      )}
                      {beh.entity_count !== undefined && (
                        <p className="mb-1 text-xs">
                          <span className="text-muted-foreground">Entities tracked: </span>
                          <span>{beh.entity_count}</span>
                        </p>
                      )}
                      {beh.actions && Object.keys(beh.actions).length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {Object.entries(beh.actions)
                            .sort(([, a], [, b]) => (b as number) - (a as number))
                            .slice(0, 4)
                            .map(([action, cnt]) => (
                              <span key={action} className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-muted-foreground">
                                {action} ×{cnt as number}
                              </span>
                            ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
