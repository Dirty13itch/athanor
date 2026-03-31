"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Beaker, RefreshCcw, Rocket } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  asArray,
  asObject,
  fetchJson,
  formatKey,
  getBoolean,
  getNumber,
  getOptionalString,
  getString,
  type JsonObject,
} from "@/components/runtime-panel-utils";
import { formatRelativeTime } from "@/lib/format";
import { isOperatorSessionLocked, useOperatorSessionStatus } from "@/lib/operator-session";

export function ProvingGroundCard({
  title = "Model proving ground",
  description = "Benchmark and evaluate champions, challengers, and routed pipelines against Athanor's own workload packs.",
  compact = false,
}: {
  title?: string;
  description?: string;
  compact?: boolean;
}) {
  const session = useOperatorSessionStatus();
  const locked = isOperatorSessionLocked(session);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const provingGroundQuery = useQuery({
    queryKey: ["operator-panel", "models", "proving-ground"],
    queryFn: () => fetchJson<JsonObject>("/api/models/proving-ground"),
    enabled: !locked,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  if (locked) {
    return (
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Beaker className="h-5 w-5 text-primary" />
            {title}
          </CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="Unlock required"
            description="The proving-ground benchmark and evaluation snapshot stays hidden until the operator session is unlocked."
            className="py-8"
          />
        </CardContent>
      </Card>
    );
  }

  async function runProvingGround() {
    setBusy(true);
    setFeedback(null);
    try {
      await fetchJson<JsonObject>("/api/models/proving-ground", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: compact ? 6 : 12 }),
      });
      setFeedback("Proving-ground benchmark cycle completed.");
      await provingGroundQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Failed to run the proving ground.");
    } finally {
      setBusy(false);
    }
  }

  if (provingGroundQuery.isError && !provingGroundQuery.data) {
    return (
      <ErrorPanel
        title={title}
        description={
          provingGroundQuery.error instanceof Error
            ? provingGroundQuery.error.message
            : "Failed to load proving-ground state."
        }
      />
    );
  }

  const snapshot = asObject(provingGroundQuery.data);
  if (!snapshot) {
    return (
      <EmptyState
        title="No proving-ground snapshot yet"
        description="The benchmark and evaluation runner has not returned runtime state."
      />
    );
  }

  const latestRun = asObject(snapshot.latest_run);
  const improvementSummary = asObject(snapshot.improvement_summary);
  const recentResults = asArray<JsonObject>(snapshot.recent_results);
  const laneCoverage = asArray<JsonObject>(snapshot.lane_coverage);
  const governedCorpora = asArray<JsonObject>(snapshot.governed_corpora);
  const recentExperiments = asArray<JsonObject>(snapshot.recent_experiments);
  const experimentLedger = asObject(snapshot.experiment_ledger);

  return (
    <Card className="surface-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Beaker className="h-5 w-5 text-primary" />
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {feedback ? (
          <div className="surface-metric rounded-xl border px-3 py-2 text-sm">
            {feedback}
          </div>
        ) : null}

        <div className="grid gap-3 sm:grid-cols-4">
          <Metric label="Status" value={formatKey(getString(snapshot.status, "unknown"))} />
          <Metric label="Corpora" value={`${asArray(snapshot.corpora).length}`} />
          <Metric
            label="Latest pass rate"
            value={
              latestRun
                ? `${Math.round(getNumber(latestRun.pass_rate, 0) * 100)}%`
                : "--"
            }
          />
          <Metric
            label="Open proposals"
            value={`${getNumber(improvementSummary?.pending, 0)}`}
          />
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={() => void provingGroundQuery.refetch()}
            disabled={provingGroundQuery.isFetching}
          >
            <RefreshCcw className={`mr-2 h-4 w-4 ${provingGroundQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button onClick={() => void runProvingGround()} disabled={busy}>
            <Rocket className="mr-2 h-4 w-4" />
            {busy ? "Running..." : "Run proving ground"}
          </Button>
          <Badge variant="outline">{getString(snapshot.version, "unknown version")}</Badge>
        </div>

        <div className="grid gap-3 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Latest cycle</p>
            <div className="surface-metric rounded-xl border p-3 text-sm">
              {latestRun ? (
                <>
                  <MetricRow label="Source" value={formatKey(getString(latestRun.source, "benchmark_history"))} />
                  <MetricRow
                    label="Benchmarks"
                    value={`${getNumber(latestRun.passed, 0)} / ${getNumber(latestRun.total, 0)}`}
                  />
                  <MetricRow
                    label="Patterns consumed"
                    value={`${getNumber(latestRun.patterns_consumed, 0)}`}
                  />
                  <MetricRow
                    label="Proposals generated"
                    value={`${getNumber(latestRun.proposals_generated, 0)}`}
                  />
                  {getOptionalString(latestRun.timestamp) ? (
                    <p className="mt-3 text-xs text-muted-foreground" data-volatile="true">
                      last run {formatRelativeTime(getString(latestRun.timestamp))}
                    </p>
                  ) : null}
                </>
              ) : (
                <EmptyState
                  title="No proving-ground runs yet"
                  description="Run the proving ground to populate benchmark evidence."
                  className="py-6"
                />
              )}
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Lane coverage</p>
            <div className="space-y-2">
              {laneCoverage.slice(0, compact ? 3 : 5).map((lane) => (
                <div key={getString(lane.role_id)} className="surface-metric rounded-xl border px-3 py-2 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{getString(lane.label)}</p>
                      <p className="text-xs text-muted-foreground">
                        champion {getString(lane.champion)}
                      </p>
                    </div>
                    <Badge variant="outline">
                      {getNumber(lane.challenger_count, 0)} challenger
                      {getNumber(lane.challenger_count, 0) === 1 ? "" : "s"}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-[1fr_1fr]">
          <div className="surface-metric rounded-xl border px-3 py-3">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
              Governed corpus packs
            </p>
            {governedCorpora.length > 0 ? (
              <div className="mt-2 space-y-2">
                {governedCorpora.slice(0, compact ? 2 : 4).map((corpus) => (
                  <div
                    key={getString(corpus.id)}
                    className="surface-tile rounded-lg border px-3 py-2"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium">{getString(corpus.label, getString(corpus.id))}</p>
                      <Badge variant="outline">{formatKey(getString(corpus.sensitivity, "mixed"))}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      baseline {getString(corpus.baseline_version, "unknown")} |{" "}
                      {getString(corpus.refresh_cadence, "unspecified")}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-sm text-muted-foreground">
                Governed corpus packs will appear here once the eval corpus registry is surfaced at runtime.
              </p>
            )}
          </div>

          <div className="surface-metric rounded-xl border px-3 py-3">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
              Experiment ledger posture
            </p>
            <div className="mt-2 grid gap-2 text-sm text-muted-foreground">
              <MetricRow
                label="Ledger status"
                value={formatKey(getString(experimentLedger?.status, "configured"))}
              />
              <MetricRow
                label="Evidence count"
                value={`${getNumber(experimentLedger?.evidence_count, recentExperiments.length)}`}
              />
              <MetricRow
                label="Retention"
                value={getString(experimentLedger?.retention, "unknown")}
              />
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              {getString(
                experimentLedger?.promotion_linkage,
                "Promotion linkage will appear here once recent benchmark evidence is recorded."
              )}
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Recent benchmark results</p>
          {recentResults.length > 0 ? (
            recentResults.slice(0, compact ? 3 : 6).map((result) => (
              <div key={getString(result.benchmark_id)} className="surface-metric rounded-xl border px-3 py-2 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={result.passed ? "outline" : "destructive"}>
                    {getBoolean(result.passed) ? "passed" : "failed"}
                  </Badge>
                  <Badge variant="secondary">{formatKey(getString(result.category, "benchmark"))}</Badge>
                  <p className="font-medium">{getString(result.name, getString(result.benchmark_id))}</p>
                </div>
                <div className="mt-2 grid gap-2 text-xs text-muted-foreground md:grid-cols-3">
                  <span>
                    score {getNumber(result.score, 0).toFixed(1)} / {getNumber(result.max_score, 0).toFixed(1)}
                  </span>
                  <span>{Math.round(getNumber(result.duration_ms, 0))}ms</span>
                  <span data-volatile="true">
                    {formatRelativeTime(getString(result.timestamp, new Date().toISOString()))}
                  </span>
                </div>
              </div>
            ))
          ) : (
            <EmptyState
              title="No benchmark evidence yet"
              description="Recent proving-ground results will appear here once the benchmark loop runs."
              className="py-8"
            />
          )}
        </div>

        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Recent experiments</p>
          {recentExperiments.length > 0 ? (
            recentExperiments.slice(0, compact ? 2 : 4).map((experiment) => (
              <div key={getString(experiment.id)} className="surface-metric rounded-xl border px-3 py-2 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={getBoolean(experiment.passed) ? "outline" : "destructive"}>
                    {getBoolean(experiment.passed) ? "passed" : "failed"}
                  </Badge>
                  <Badge variant="secondary">{formatKey(getString(experiment.category, "experiment"))}</Badge>
                  <p className="font-medium">{getString(experiment.name, getString(experiment.id))}</p>
                </div>
                <div className="mt-2 grid gap-2 text-xs text-muted-foreground md:grid-cols-3">
                  <span>
                    score {getNumber(experiment.score, 0).toFixed(1)} /{" "}
                    {getNumber(experiment.max_score, 0).toFixed(1)}
                  </span>
                  <span data-volatile="true">
                    {formatRelativeTime(getString(experiment.timestamp, new Date().toISOString()))}
                  </span>
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">
              Experiment-ledger evidence will appear here once the proving ground records benchmark runs.
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="surface-metric rounded-xl border px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
