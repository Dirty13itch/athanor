"use client";

import { useQuery } from "@tanstack/react-query";
import { Gavel, ShieldCheck } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getJudgePlane } from "@/lib/api";
import { compactText } from "@/lib/format";
import { isOperatorSessionLocked, useOperatorSessionStatus } from "@/lib/operator-session";
import { queryKeys } from "@/lib/query-client";

function formatLabel(value: string) {
  return value.replace(/_/g, " ");
}

function verdictVariant(verdict: string) {
  if (verdict === "reject") {
    return "destructive" as const;
  }
  if (verdict === "review_required") {
    return "secondary" as const;
  }
  return "outline" as const;
}

export function JudgePlaneCard({
  title = "Judge plane",
  description = "Local scoring, promotion gating, and recent verdicts across supervisor and worker runs.",
  limit = 6,
  compact = false,
}: {
  title?: string;
  description?: string;
  limit?: number;
  compact?: boolean;
}) {
  const session = useOperatorSessionStatus();
  const locked = isOperatorSessionLocked(session);
  const judgeQuery = useQuery({
    queryKey: queryKeys.judgePlane(limit),
    queryFn: () => getJudgePlane(limit),
    enabled: !locked,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  if (locked) {
    return (
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Gavel className="h-5 w-5 text-primary" />
            {title}
          </CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="Unlock required"
            description="Judge-plane verdicts and challenger posture stay hidden until the operator session is unlocked."
            className="py-8"
          />
        </CardContent>
      </Card>
    );
  }

  if (judgeQuery.isError && !judgeQuery.data) {
    return (
      <ErrorPanel
        title={title}
        description={
          judgeQuery.error instanceof Error
            ? judgeQuery.error.message
            : "Failed to load judge-plane state."
        }
      />
    );
  }

  const snapshot = judgeQuery.data;
  if (!snapshot) {
    return (
      <EmptyState
        title="No judge state yet"
        description="The local judge and verifier lane has not returned a runtime snapshot."
      />
    );
  }

  return (
    <Card className="surface-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Gavel className="h-5 w-5 text-primary" />
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-4">
          <Metric label="Status" value={formatLabel(snapshot.status)} />
          <Metric label="Champion" value={snapshot.champion} />
          <Metric
            label="Acceptance rate"
            value={`${Math.round(snapshot.summary.acceptance_rate * 100)}%`}
          />
          <Metric label="Pending review" value={`${snapshot.summary.pending_review_queue}`} />
        </div>

        <div className="grid gap-3 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
              Recent verdicts
            </p>
            {snapshot.recent_verdicts.length > 0 ? (
              snapshot.recent_verdicts.slice(0, compact ? 3 : limit).map((verdict) => (
                <a
                  key={verdict.run_id}
                  href={verdict.deep_link}
                className="surface-metric block rounded-xl border px-3 py-3 transition hover:bg-accent/40"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={verdictVariant(verdict.verdict)}>
                      {formatLabel(verdict.verdict)}
                    </Badge>
                    <Badge variant="secondary">{verdict.provider}</Badge>
                    {verdict.policy_class ? (
                      <Badge variant="outline">{formatLabel(verdict.policy_class)}</Badge>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm font-medium">{verdict.agent ?? "Unknown agent"}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {compactText(verdict.rationale, compact ? 120 : 180)}
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    score {Math.round(verdict.score * 100)} / 100
                  </p>
                </a>
              ))
            ) : (
              <EmptyState
                title="No verdicts yet"
                description="Judge verdicts will appear here once execution lineage is recorded."
                className="py-8"
              />
            )}
          </div>

          <div className="space-y-3">
            <div className="surface-metric rounded-xl border px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Workload coverage
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {snapshot.workload_classes.map((item) => (
                  <Badge key={item} variant="secondary">
                    {formatLabel(item)}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="surface-metric rounded-xl border px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Guardrails
              </p>
              <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                {snapshot.guardrails.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>

            <div className="surface-metric rounded-xl border px-3 py-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-primary" />
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                  Challenger posture
                </p>
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {snapshot.challengers.map((item) => (
                  <Badge key={item} variant="outline">
                    {item}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
            <div className="surface-metric rounded-xl border px-3 py-3">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}
