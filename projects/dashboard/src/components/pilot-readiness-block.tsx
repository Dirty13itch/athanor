"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { requestJson } from "@/features/workforce/helpers";
import type { CapabilityPilotReadinessRecord, CapabilityPilotReadinessSnapshot } from "@/lib/contracts";
import { cn } from "@/lib/utils";

function compactStateLabel(value: string) {
  return value.replace(/_/g, " ");
}

function blockerLabel(reason: string) {
  if (reason === "missing_packet") return "packet missing";
  if (reason.startsWith("missing_env:")) return `env ${reason.slice("missing_env:".length)}`;
  if (reason.startsWith("missing_command:")) return `command ${reason.slice("missing_command:".length)}`;
  if (reason === "manual_review_rejected") return "manual review rejected";
  return compactStateLabel(reason);
}

function reviewLabel(outcome: string) {
  if (outcome === "rejected_as_redundant_for_current_stack") {
    return "manual review rejected";
  }
  return `manual review ${compactStateLabel(outcome)}`;
}

function readinessTone(state: string, blockers: string[], manualReviewOutcome: string | null) {
  if (state === "adopted" || state === "formal_eval_complete") return "secondary" as const;
  if (manualReviewOutcome === "rejected_as_redundant_for_current_stack" || state === "formal_eval_failed") {
    return "destructive" as const;
  }
  if (blockers.length > 0 || state === "blocked") return "outline" as const;
  return "secondary" as const;
}

async function loadPilotReadiness(): Promise<CapabilityPilotReadinessSnapshot> {
  const data = await requestJson("/api/operator/pilot-readiness");
  return (data ?? {}) as CapabilityPilotReadinessSnapshot;
}

export function PilotReadinessBlock({ compact = false }: { compact?: boolean }) {
  const readinessQuery = useQuery({
    queryKey: ["pilot-readiness"],
    queryFn: loadPilotReadiness,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const payload = readinessQuery.data ?? null;
  const lanes = Array.isArray(payload?.records) ? payload.records : [];
  const blockedCount = payload?.summary?.blocked ?? 0;
  const manualReviewCount = lanes.filter(
    (lane) => lane.manualReviewOutcome && lane.manualReviewOutcome !== "accepted",
  ).length;
  const payloadAvailable = Boolean(payload) && payload?.available !== false && Array.isArray(payload?.records);

  return (
      <section className={cn("surface-panel rounded-[28px] border px-5 py-5 sm:px-6", compact && "px-4 py-4 sm:px-5") }>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="page-eyebrow">Pilot readiness</p>
          <h2 className={cn("font-heading text-2xl font-medium tracking-[-0.03em]", compact && "text-xl")}>Letta, OpenHands, AGT</h2>
          <p className={cn("max-w-4xl text-sm leading-6 text-muted-foreground", compact && "text-xs leading-5") }>
            Three activation lanes are tracked here. Each card shows the current readiness state, the exact blockers, and the next gate that still needs to be closed.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline">{lanes.length} lanes</Badge>
          <Badge variant={blockedCount > 0 ? "destructive" : "secondary"}>{blockedCount} blocked</Badge>
          {manualReviewCount > 0 ? <Badge variant="outline">{manualReviewCount} manual review</Badge> : null}
        </div>
      </div>

      {!payloadAvailable ? (
        <div className="mt-4 rounded-2xl border border-[color:var(--signal-warning)]/40 bg-background/40 px-4 py-3 text-sm text-muted-foreground">
          {payload?.detail ?? "Pilot readiness data could not be loaded from the canonical operator route."}
        </div>
      ) : null}

      {!readinessQuery.isError && !payload ? (
        <div className="mt-4 rounded-2xl border border-border/70 bg-background/40 px-4 py-3 text-sm text-muted-foreground">
          Loading pilot readiness lanes...
        </div>
      ) : null}

      {payload ? (
        <div className={cn("mt-4 grid gap-4 lg:grid-cols-3", compact && "gap-3")}>
          {lanes.map((lane) => {
            const tone = readinessTone(lane.readinessState, lane.blockingReasons, lane.manualReviewOutcome ?? null);
            return (
              <article key={lane.capabilityId} className={cn("surface-instrument rounded-2xl border px-4 py-4", compact && "px-3 py-3")}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className={cn("text-sm font-medium text-foreground", compact && "text-xs uppercase tracking-[0.18em] text-muted-foreground")}>{lane.label}</p>
                    {lane.formalPreflightBlockerClass ? (
                      <p className="mt-1 text-xs text-muted-foreground">
                        {compactStateLabel(lane.formalPreflightBlockerClass)}
                      </p>
                    ) : null}
                  </div>
                  <Badge variant={tone}>{compactStateLabel(lane.readinessState)}</Badge>
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  {lane.blockingReasons.length > 0 ? (
                    lane.blockingReasons.slice(0, 3).map((reason) => (
                      <Badge key={`${lane.capabilityId}-${reason}`} variant="secondary" className="text-[11px]">
                        {blockerLabel(reason)}
                      </Badge>
                    ))
                  ) : (
                    <Badge variant="secondary" className="text-[11px]">
                      no blockers surfaced
                    </Badge>
                  )}
                  {lane.blockingReasons.length > 3 ? (
                    <Badge variant="outline" className="text-[11px]">
                      +{lane.blockingReasons.length - 3} more
                    </Badge>
                  ) : null}
                  {lane.proofTier ? (
                    <Badge variant="outline" className="text-[11px]">
                      {compactStateLabel(lane.proofTier)}
                    </Badge>
                  ) : null}
                  {lane.manualReviewOutcome ? (
                    <Badge variant={lane.manualReviewOutcome.startsWith("rejected") ? "destructive" : "outline"} className="text-[11px]">
                      {reviewLabel(lane.manualReviewOutcome)}
                    </Badge>
                  ) : null}
                </div>

                <div className="mt-3 space-y-2 text-sm leading-6 text-muted-foreground">
                  <p>
                    <span className="font-medium text-foreground">Next action:</span> {lane.nextAction ?? "No next action published."}
                  </p>
                  <p>
                    <span className="font-medium text-foreground">Next gate:</span> {lane.nextFormalGate ?? "No next gate published."}
                  </p>
                  {lane.manualReviewSummary ? <p>{lane.manualReviewSummary}</p> : null}
                </div>
              </article>
            );
          })}
        </div>
      ) : null}

      {payload?.generatedAt ? (
        <p className="mt-3 text-xs text-muted-foreground">
          Source: {payload.sourceKind ?? "operator route"}
          {payload.sourcePath ? ` · ${payload.sourcePath}` : ""}
        </p>
      ) : null}
    </section>
  );
}
