"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ActivitySquare, ArchiveRestore, ShieldAlert, TestTube2 } from "lucide-react";
import { requestJson } from "@/features/workforce/helpers";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getOperationsReadiness } from "@/lib/api";
import { formatRelativeTime } from "@/lib/format";
import { isOperatorSessionLocked, useOperatorSessionStatus } from "@/lib/operator-session";
import { queryKeys } from "@/lib/query-client";

function compactLabel(value: string) {
  return value.replace(/_/g, " ");
}

function statusVariant(status: string) {
  if (status === "configured" || status === "planned drill") {
    return "secondary" as const;
  }
  if (status === "degraded" || status === "blocked") {
    return "destructive" as const;
  }
  return "outline" as const;
}

export function OperationsReadinessCard({
  compact = false,
}: {
  compact?: boolean;
}) {
  const session = useOperatorSessionStatus();
  const locked = isOperatorSessionLocked(session);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const readinessQuery = useQuery({
    queryKey: queryKeys.operationsReadiness,
    queryFn: getOperationsReadiness,
    enabled: !locked,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  if (locked) {
    return (
      <Card className="surface-panel">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <CardTitle className="flex items-center gap-2 text-lg">
                <ShieldAlert className="h-5 w-5 text-primary" />
                Operations readiness
              </CardTitle>
              <CardDescription>
                Restore posture, release ladder, lifecycle governance, and synthetic operator tests unlock with the operator session.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="Unlock required"
            description="Operations-readiness evidence is hidden while the operator session is locked."
            className="py-8"
          />
        </CardContent>
      </Card>
    );
  }

  async function runOperatorTests() {
    setBusy(true);
    setFeedback(null);
    try {
      await requestJson("/api/governor/operator-tests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actor: "dashboard-operator" }),
      });
      await readinessQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Failed to run synthetic operator tests.");
    } finally {
      setBusy(false);
    }
  }

  if (readinessQuery.isError && !readinessQuery.data) {
    return (
      <ErrorPanel
        title="Operations readiness"
        description={
          readinessQuery.error instanceof Error
            ? readinessQuery.error.message
            : "Failed to load operations-readiness posture."
        }
      />
    );
  }

  const snapshot = readinessQuery.data;
  if (!snapshot) {
    return (
      <EmptyState
        title="No operations-readiness snapshot yet"
        description="Restore posture, release ritual, and operator-test evidence have not been surfaced yet."
      />
    );
  }

  const runbooks = compact ? snapshot.runbooks.items.slice(0, 3) : snapshot.runbooks.items;
  const stores = compact
    ? snapshot.backup_restore.critical_stores.slice(0, 3)
    : snapshot.backup_restore.critical_stores;
  const flows = compact
    ? snapshot.synthetic_operator_tests.flows.slice(0, 3)
    : snapshot.synthetic_operator_tests.flows;
  const verifiedStores =
    snapshot.backup_restore.verified_store_count ??
    snapshot.backup_restore.critical_stores.filter((store) => store.verified).length;
  const totalStores =
    snapshot.backup_restore.store_count ?? snapshot.backup_restore.critical_stores.length;

  return (
    <Card className="surface-panel">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-lg">
              <ShieldAlert className="h-5 w-5 text-primary" />
              Operations readiness
            </CardTitle>
            <CardDescription>
              Restore posture, release ladder, lifecycle governance, and synthetic operator-test evidence.
            </CardDescription>
          </div>
          <Button size="sm" variant="outline" onClick={() => void runOperatorTests()} disabled={busy}>
            {busy ? "Running..." : "Run tests"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {feedback ? (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-100">
            {feedback}
          </div>
        ) : null}

        <div className="grid gap-3 sm:grid-cols-4">
          <Metric
            icon={<ArchiveRestore className="h-4 w-4 text-primary" />}
            label="Restore"
            value={`${verifiedStores}/${totalStores} verified`}
            detail={
              snapshot.backup_restore.last_drill_at
                ? `${compactLabel(snapshot.backup_restore.status)} | ${formatRelativeTime(
                    snapshot.backup_restore.last_drill_at
                  )}`
                : compactLabel(snapshot.backup_restore.status)
            }
          />
          <Metric
            icon={<ActivitySquare className="h-4 w-4 text-primary" />}
            label="Release ladder"
            value={`${snapshot.release_ritual.tiers.length} tiers`}
            detail={
              snapshot.release_ritual.last_rehearsal_at
                ? `${compactLabel(snapshot.release_ritual.status)} | ${formatRelativeTime(
                    snapshot.release_ritual.last_rehearsal_at
                  )}`
                : compactLabel(snapshot.release_ritual.status)
            }
          />
          <Metric
            icon={<TestTube2 className="h-4 w-4 text-primary" />}
            label="Synthetic flows"
            value={`${snapshot.synthetic_operator_tests.flows.length}`}
            detail={
              snapshot.synthetic_operator_tests.last_run_at
                ? `${compactLabel(snapshot.synthetic_operator_tests.status)} · ${formatRelativeTime(
                    snapshot.synthetic_operator_tests.last_run_at
                  )}`
                : compactLabel(snapshot.synthetic_operator_tests.status)
            }
          />
          <Metric
            icon={<ShieldAlert className="h-4 w-4 text-primary" />}
            label="Lifecycle"
            value={`${snapshot.data_lifecycle.classes.length} classes`}
            detail={`${snapshot.deprecation_retirement.asset_classes.length} retirement classes`}
          />
        </div>

        {snapshot.master_atlas ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <SectionTitle title="Atlas readiness gates" />
              <Link href="/topology#master-atlas-map" className="text-xs font-medium text-primary hover:underline">
                Open relationship map
              </Link>
            </div>
            <div className="grid gap-3 sm:grid-cols-4">
              <Metric
                icon={<ShieldAlert className="h-4 w-4 text-primary" />}
                label="Packet-ready"
                value={`${snapshot.master_atlas.packet_ready_count}`}
                detail={`${snapshot.master_atlas.blocked_packet_count} blocked packets`}
              />
              <Metric
                icon={<ActivitySquare className="h-4 w-4 text-primary" />}
                label="Capabilities"
                value={`${snapshot.master_atlas.capability_count}`}
                detail={`${snapshot.master_atlas.adopted_count} adopted | ${snapshot.master_atlas.proving_count} proving`}
              />
              <Metric
                icon={<TestTube2 className="h-4 w-4 text-primary" />}
                label="Governance"
                value={compactLabel(snapshot.master_atlas.governance_posture)}
                detail={`${snapshot.master_atlas.governance_blocker_count} blocker classes`}
              />
              <Metric
                icon={<ArchiveRestore className="h-4 w-4 text-primary" />}
                label="Turnover"
                value={compactLabel(snapshot.master_atlas.turnover_status)}
                detail={
                  (snapshot.master_atlas.self_acceleration_ready_now
                    ? snapshot.master_atlas.provider_elasticity_limited
                      ? `compounding live | ${snapshot.master_atlas.provider_elasticity_blocking_provider_count ?? 0} provider lanes limiting elasticity`
                      : "compounding live"
                    : null) ??
                  snapshot.master_atlas.autonomous_top_task_title ??
                  (snapshot.master_atlas.autonomous_dispatchable_queue_count !== undefined
                    ? `${snapshot.master_atlas.autonomous_dispatchable_queue_count} autonomous tasks dispatchable`
                    : null) ??
                  snapshot.master_atlas.turnover_next_gate ??
                  snapshot.master_atlas.next_checkpoint_slice?.title ??
                  snapshot.master_atlas.top_missing_proof ??
                  "no gate selected"
                }
              />
            </div>

            <div className="grid gap-3 lg:grid-cols-[1.05fr_0.95fr]">
              <div className="surface-metric rounded-xl border px-3 py-3">
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Governance blockers</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {snapshot.master_atlas.governance_blockers.length > 0 ? (
                    snapshot.master_atlas.governance_blockers.map((blocker) => (
                      <Badge key={blocker} variant="secondary">
                        {compactLabel(blocker)}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">none</span>
                  )}
                </div>
              </div>

              <div className="surface-metric rounded-xl border px-3 py-3">
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Recommended next move</p>
                <div className="mt-2 space-y-2">
                  {snapshot.master_atlas.recommendation_summaries.slice(0, 2).map((item) => (
                    <div key={item.id}>
                      <p className="text-sm font-medium">{item.summary}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{item.reason}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : null}

        <div className="grid gap-3 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="space-y-3">
            <SectionTitle title="Runbooks" />
            <div className="space-y-2">
              {runbooks.map((runbook) => (
                <div
                  key={runbook.id}
                className="surface-metric rounded-xl border px-3 py-3"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium">{runbook.label}</p>
                    <div className="flex flex-wrap items-center gap-2">
                      {runbook.support_status ? (
                        <Badge variant={statusVariant(runbook.support_status)}>
                          {compactLabel(runbook.support_status)}
                        </Badge>
                      ) : null}
                      <Badge variant="outline">{runbook.cadence ?? "as-needed"}</Badge>
                    </div>
                  </div>
                  {runbook.description ? (
                    <p className="mt-1 text-sm text-muted-foreground">{runbook.description}</p>
                  ) : null}
                  {runbook.related_surface ? (
                    <p className="mt-2 text-xs text-muted-foreground">
                      cockpit surface {runbook.related_surface}
                    </p>
                  ) : null}
                  {runbook.evidence_flow_ids && runbook.evidence_flow_ids.length > 0 ? (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {runbook.evidence_flow_ids.slice(0, compact ? 2 : 3).map((flowId) => (
                        <Badge key={flowId} variant="secondary">
                          {compactLabel(flowId)}
                        </Badge>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>

            <SectionTitle title="Synthetic operator tests" />
            <div className="space-y-2">
              {flows.map((flow) => (
                <div
                  key={flow.id}
                className="surface-metric rounded-xl border px-3 py-3"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium">{flow.title}</p>
                    <Badge variant={statusVariant(flow.status)}>{compactLabel(flow.status)}</Badge>
                  </div>
                  {flow.description ? (
                    <p className="mt-1 text-sm text-muted-foreground">{flow.description}</p>
                  ) : null}
                  <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span>
                      checks {flow.checks_passed ?? 0}/{flow.checks_total ?? 0}
                    </span>
                    {flow.last_outcome ? <span>outcome {compactLabel(flow.last_outcome)}</span> : null}
                    {flow.last_run_at ? (
                      <span data-volatile="true">updated {formatRelativeTime(flow.last_run_at)}</span>
                    ) : (
                      <span>not run yet</span>
                    )}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {flow.evidence.map((item) => (
                      <Badge key={item} variant="secondary">
                        {item}
                      </Badge>
                    ))}
                  </div>
                  {flow.notes && flow.notes.length > 0 ? (
                    <div className="mt-2 space-y-1 text-xs text-muted-foreground">
                      {flow.notes.slice(0, compact ? 1 : 2).map((note) => (
                        <p key={note}>{note}</p>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <SectionTitle title="Backup and release posture" />
            <div className="space-y-2">
              {stores.map((store) => (
                <div
                  key={store.id}
                className="surface-metric rounded-xl border px-3 py-3"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium">{store.label ?? compactLabel(store.id)}</p>
                    <Badge variant={statusVariant(store.drill_status ?? "configured")}>
                      {compactLabel(store.drill_status ?? "configured")}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    order {store.restore_order ?? "--"}
                    {store.cadence ? ` | ${store.cadence}` : ""}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span>{store.verified ? "verified" : "awaiting live proof"}</span>
                    {store.last_drill_at ? (
                      <span data-volatile="true">updated {formatRelativeTime(store.last_drill_at)}</span>
                    ) : null}
                    {store.last_outcome ? <span>outcome {compactLabel(store.last_outcome)}</span> : null}
                  </div>
                  {store.probe_summary ? (
                    <p className="mt-2 text-xs text-muted-foreground">{store.probe_summary}</p>
                  ) : null}
                </div>
              ))}
            </div>

          <div className="surface-metric rounded-xl border px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Release ritual
              </p>
              <div className="mt-2 grid gap-2 text-sm text-muted-foreground">
                <span>status {compactLabel(snapshot.release_ritual.status)}</span>
                <span>
                  rehearsal{" "}
                  {compactLabel(snapshot.release_ritual.rehearsal_status ?? "configured")}
                  {snapshot.release_ritual.last_outcome
                    ? ` | outcome ${compactLabel(snapshot.release_ritual.last_outcome)}`
                    : ""}
                </span>
                {snapshot.release_ritual.last_rehearsal_at ? (
                  <span data-volatile="true">
                    last rehearsal {formatRelativeTime(snapshot.release_ritual.last_rehearsal_at)}
                  </span>
                ) : null}
                <span>
                  active promotions {snapshot.release_ritual.active_promotion_count ?? 0}
                </span>
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {snapshot.release_ritual.tiers.map((tier) => (
                  <Badge key={tier} variant="secondary">
                    {compactLabel(tier)}
                  </Badge>
                ))}
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                {snapshot.release_ritual.ritual.map((step) => (
                  <span key={step} className="rounded-full border border-border/60 px-2 py-1">
                    {compactLabel(step)}
                  </span>
                ))}
              </div>
            </div>

          <div className="surface-metric rounded-xl border px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Economic and lifecycle posture
              </p>
              <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                <li>economic status: {compactLabel(snapshot.economic_governance.status)}</li>
                <li>
                  reserve lanes: {snapshot.economic_governance.premium_reserve_lanes.join(", ")}
                </li>
                <li>
                  live providers: {snapshot.economic_governance.provider_count ?? 0}
                  {" | "}
                  recent leases: {snapshot.economic_governance.recent_lease_count ?? 0}
                  {" | "}
                  constrained: {snapshot.economic_governance.constrained_count ?? 0}
                </li>
                <li>
                  approval-required lanes:{" "}
                  {snapshot.economic_governance.approval_required_lanes.join(", ")}
                </li>
                <li>
                  downgrade order: {snapshot.economic_governance.downgrade_order.join(" -> ")}
                </li>
                {snapshot.economic_governance.last_verified_at ? (
                  <li data-volatile="true">
                    last verified {formatRelativeTime(snapshot.economic_governance.last_verified_at)}
                  </li>
                ) : null}
                <li>lifecycle status: {compactLabel(snapshot.data_lifecycle.status)}</li>
                <li>
                  sovereign-only lifecycle classes:{" "}
                  {snapshot.data_lifecycle.classes.filter((item) => item.sovereign_only).length}
                </li>
                <li>
                  runtime runs: {snapshot.data_lifecycle.run_count ?? 0}
                  {" | "}
                  eval artifacts: {snapshot.data_lifecycle.eval_artifact_count ?? 0}
                </li>
                {snapshot.data_lifecycle.last_verified_at ? (
                  <li data-volatile="true">
                    lifecycle verified {formatRelativeTime(snapshot.data_lifecycle.last_verified_at)}
                  </li>
                ) : null}
                <li>
                  retirement status: {compactLabel(snapshot.deprecation_retirement.status)}
                </li>
                <li>
                  retirement candidates: {snapshot.deprecation_retirement.active_retirement_count ?? 0}
                  {" | "}
                  rehearsed records: {snapshot.deprecation_retirement.recent_retirement_count ?? 0}
                </li>
                {snapshot.deprecation_retirement.last_rehearsal_at ? (
                  <li data-volatile="true">
                    retirement rehearsal{" "}
                    {formatRelativeTime(snapshot.deprecation_retirement.last_rehearsal_at)}
                  </li>
                ) : null}
                <li>tool-permission status: {compactLabel(snapshot.tool_permissions.status)}</li>
                <li>default tool mode: {compactLabel(snapshot.tool_permissions.default_mode)}</li>
                <li>
                  enforced subjects: {snapshot.tool_permissions.enforced_subject_count ?? 0}
                  {" | "}
                  denied checks: {snapshot.tool_permissions.denied_action_count ?? 0}
                </li>
                {snapshot.tool_permissions.last_verified_at ? (
                  <li data-volatile="true">
                    tool permissions verified{" "}
                    {formatRelativeTime(snapshot.tool_permissions.last_verified_at)}
                  </li>
                ) : null}
              </ul>
              <div className="mt-3 flex flex-wrap gap-2">
                {snapshot.deprecation_retirement.asset_classes.map((assetClass) => (
                  <Badge key={`retirement-${assetClass}`} variant="secondary">
                    retire {compactLabel(assetClass)}
                  </Badge>
                ))}
                {snapshot.tool_permissions.subjects.map((subject) => (
                  <Badge key={subject.subject} variant="secondary">
                    {(subject.label ?? compactLabel(subject.subject)).toLowerCase()}{" "}
                    {"|"} {compactLabel(subject.mode ?? snapshot.tool_permissions.default_mode)}
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

function SectionTitle({ title }: { title: string }) {
  return (
    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{title}</p>
  );
}

function Metric({
  icon,
  label,
  value,
  detail,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  detail: string;
}) {
  return (
          <div className="surface-metric rounded-xl border px-3 py-3">
      <div className="flex items-center gap-2 text-muted-foreground">{icon}</div>
      <p className="mt-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}
