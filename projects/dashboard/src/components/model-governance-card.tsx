"use client";

import type { ReactNode } from "react";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Beaker, BrainCircuit, Radar, Scale } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { StatusDot } from "@/components/status-dot";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { requestJson } from "@/features/workforce/helpers";
import { getModelGovernance } from "@/lib/api";
import { isOperatorSessionLocked, useOperatorSessionStatus } from "@/lib/operator-session";
import { queryKeys } from "@/lib/query-client";

function toneForStatus(status: string): "healthy" | "warning" {
  return status === "live" ? "healthy" : "warning";
}

function compactLabel(value: string) {
  return value.replace(/_/g, " ");
}

export function ModelGovernanceCard() {
  const session = useOperatorSessionStatus();
  const locked = isOperatorSessionLocked(session);
  const [busy, setBusy] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const governanceQuery = useQuery({
    queryKey: queryKeys.modelGovernance,
    queryFn: getModelGovernance,
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
            Model governance
          </CardTitle>
          <CardDescription>
            Champion lanes, promotion posture, and autonomy-governance detail unlock with the operator session.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="Unlock required"
            description="Model-governance posture is hidden while the operator session is locked."
            className="py-8"
          />
        </CardContent>
      </Card>
    );
  }

  async function stagePromotion(roleId: string, candidate: string, targetTier = "canary") {
    setBusy(`stage:${roleId}:${candidate}`);
    setFeedback(null);
    try {
      await requestJson("/api/models/governance/promotions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role_id: roleId,
          candidate,
          target_tier: targetTier,
          actor: "dashboard-operator",
          reason: `Stage ${candidate} for ${roleId} from the model-governance cockpit.`,
          source: "dashboard_model_governance",
        }),
      });
      setFeedback(`Staged ${candidate} for ${roleId} through the governed release ladder.`);
      await governanceQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Failed to stage promotion candidate.");
    } finally {
      setBusy(null);
    }
  }

  async function transitionPromotion(id: string, action: "advance" | "hold" | "rollback") {
    setBusy(`${action}:${id}`);
    setFeedback(null);
    try {
      await requestJson(`/api/models/governance/promotions/${id}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          actor: "dashboard-operator",
          reason: `${action} issued from the model-governance cockpit.`,
        }),
      });
      setFeedback(`Promotion ${id} ${action} action recorded.`);
      await governanceQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : `Failed to ${action} promotion candidate.`);
    } finally {
      setBusy(null);
    }
  }

  if (governanceQuery.isError && !governanceQuery.data) {
    return (
      <ErrorPanel
        title="Model governance"
        description={
          governanceQuery.error instanceof Error
            ? governanceQuery.error.message
            : "Failed to load model governance snapshot."
        }
      />
    );
  }

  const snapshot = governanceQuery.data;
  if (!snapshot) {
    return (
      <EmptyState
        title="No model governance snapshot yet"
        description="The proving-ground and model-role registries have not returned runtime state."
      />
    );
  }

  const candidateQueue = snapshot.model_intelligence.candidate_queue ?? [];
  const cadenceJobs = snapshot.model_intelligence.cadence_jobs ?? [];
  const nextActions = snapshot.model_intelligence.next_actions ?? [];
  const lastCycle = snapshot.model_intelligence.last_cycle;
  const promotionControls = snapshot.promotion_controls ?? snapshot.proving_ground.promotion_controls;
  const retirementControls = snapshot.retirement_controls;
  const activePromotions = promotionControls?.active_promotions ?? [];
  const stagedCandidates = new Set(activePromotions.map((record) => `${record.role_id}:${record.candidate}`));
  const governanceLayers = snapshot.governance_layers;
  const contractRegistry = governanceLayers.contract_registry;
  const evalCorpora = governanceLayers.eval_corpora;
  const experimentLedger = governanceLayers.experiment_ledger;
  const retirementGovernance = governanceLayers.deprecation_retirement;
  const autonomyActivation = governanceLayers.autonomy_activation;

  return (
    <Card className="surface-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Beaker className="h-5 w-5 text-primary" />
          Model governance
        </CardTitle>
        <CardDescription>
          Champion lanes, workload classes, proving-ground cadence, and governed promotion controls.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {feedback ? (
          <div className="surface-metric rounded-xl border px-3 py-2 text-sm">
            {feedback}
          </div>
        ) : null}

        <div className="grid gap-3 sm:grid-cols-4">
          <Metric
            icon={<BrainCircuit className="h-4 w-4 text-primary" />}
            label="Role lanes"
            value={`${snapshot.role_count}`}
            detail={`registry ${snapshot.role_registry_version}`}
          />
          <Metric
            icon={<Scale className="h-4 w-4 text-primary" />}
            label="Workloads"
            value={`${snapshot.workload_count}`}
            detail={`registry ${snapshot.workload_registry_version}`}
          />
          <Metric
            icon={<Beaker className="h-4 w-4 text-primary" />}
            label="Proving ground"
            value={snapshot.proving_ground.status.replace(/_/g, " ")}
            detail={`${evalCorpora.count} corpora | ${experimentLedger.evidence_count} evidence`}
          />
          <Metric
            icon={<Radar className="h-4 w-4 text-primary" />}
            label="Release ladder"
            value={`${activePromotions.length} active`}
            detail={promotionControls ? compactLabel(promotionControls.status) : "registry backed"}
          />
        </div>

        <div className="grid gap-3 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Champion lanes</p>
            <div className="grid gap-2">
              {snapshot.champion_summary.map((entry) => (
                <div key={entry.role_id} className="surface-metric rounded-xl border px-3 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <StatusDot tone={toneForStatus(entry.status)} className="mt-0.5" />
                        <p className="font-medium">{entry.label}</p>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        champion: {entry.champion} | {compactLabel(entry.plane)}
                      </p>
                    </div>
                    <Badge variant="outline">
                      {entry.challenger_count} challenger{entry.challenger_count === 1 ? "" : "s"}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <div className="surface-metric rounded-xl border px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Proving-ground phases
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {snapshot.proving_ground.pipeline_phases.map((phase) => (
                  <Badge key={phase} variant="secondary">
                    {compactLabel(phase)}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="surface-metric rounded-xl border px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Intelligence cadence
              </p>
              <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                <li>Weekly scan: {snapshot.model_intelligence.cadence.weekly_horizon_scan}</li>
                <li>Weekly triage: {snapshot.model_intelligence.cadence.weekly_candidate_triage}</li>
                <li>Monthly rebaseline: {snapshot.model_intelligence.cadence.monthly_rebaseline}</li>
                <li>Benchmarks logged: {snapshot.model_intelligence.benchmark_results ?? 0}</li>
                <li>Pending proposals: {snapshot.model_intelligence.pending_proposals ?? 0}</li>
              </ul>
            </div>

            <div className="surface-metric rounded-xl border px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Governance registries
              </p>
              <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                <li>
                  Contracts: {contractRegistry.count} ({contractRegistry.status_counts.live ?? 0} live)
                </li>
                <li>
                  Provenance contract:{" "}
                  {contractRegistry.provenance_contract
                    ? compactLabel(contractRegistry.provenance_contract.status)
                    : "missing"}
                </li>
                <li>
                  Eval corpora: {evalCorpora.count} | runtime evidence {evalCorpora.runtime_result_count}
                </li>
                <li>
                  Experiment ledger: {compactLabel(experimentLedger.status)} | {experimentLedger.required_field_count} required
                  fields
                </li>
                <li>
                  Retirement: {compactLabel(retirementGovernance.status)} | {retirementGovernance.asset_class_count} asset
                  classes
                </li>
              </ul>
            </div>

            <div className="surface-metric rounded-xl border px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Autonomy activation
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                <Badge variant="secondary">{compactLabel(autonomyActivation.activation_state)}</Badge>
                <Badge variant="outline">{autonomyActivation.current_phase_id ?? "no active phase"}</Badge>
                <Badge variant="outline">{compactLabel(autonomyActivation.current_phase_status)}</Badge>
              </div>
              <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
                <li>
                  Current scope: {compactLabel(autonomyActivation.current_phase_scope ?? "unscoped")} |{" "}
                  {autonomyActivation.enabled_agent_count} enabled agents
                </li>
                <li>
                  Allowed workloads: {autonomyActivation.allowed_workload_count} | blocked workloads:{" "}
                  {autonomyActivation.blocked_workload_count}
                </li>
                <li>
                  Approval gates: {autonomyActivation.approval_gate_count} | prerequisites:{" "}
                  {autonomyActivation.verified_prerequisite_count}/{autonomyActivation.prerequisite_count}
                </li>
                <li>
                  Next phase: {autonomyActivation.next_phase_id ?? "none"} |{" "}
                  {compactLabel(autonomyActivation.next_phase_status ?? "unknown")}
                </li>
              </ul>
              {autonomyActivation.next_phase_blocker_count > 0 ? (
                <div className="mt-3 space-y-2">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    Promotion blockers
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {autonomyActivation.next_phase_blocker_ids.map((blockerId) => (
                      <Badge key={blockerId} variant="secondary">
                        {blockerId}
                      </Badge>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>

            <div className="surface-metric rounded-xl border px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Governed corpora
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {evalCorpora.corpora.slice(0, 4).map((corpus) => (
                  <Badge key={corpus.id} variant="secondary">
                    {corpus.label}
                  </Badge>
                ))}
              </div>
              <div className="mt-3 space-y-2">
                {evalCorpora.corpora.slice(0, 3).map((corpus) => (
                  <div
                    key={corpus.id}
                    className="surface-tile rounded-lg border px-3 py-2"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium">{corpus.label}</p>
                      <Badge variant="outline">{compactLabel(corpus.sensitivity)}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      baseline {corpus.baseline_version} | {corpus.refresh_cadence}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="surface-metric rounded-xl border px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Intelligence queue
              </p>
              {candidateQueue.length > 0 ? (
                <>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {candidateQueue.slice(0, 4).map((entry) => (
                      <Badge key={entry.role_id} variant="secondary">
                        {entry.label}
                      </Badge>
                    ))}
                  </div>
                  <div className="mt-3 space-y-2">
                    {snapshot.role_registry
                      .filter((entry) => (entry.challengers?.length ?? 0) > 0)
                      .slice(0, 3)
                      .map((entry) => {
                        const candidate = entry.challengers[0];
                        const alreadyStaged = stagedCandidates.has(`${entry.id}:${candidate}`);
                        return (
                          <div
                            key={entry.id}
                            className="rounded-lg border border-border/50 bg-background/20 px-3 py-2"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <div className="min-w-0">
                                <p className="text-sm font-medium">{entry.label}</p>
                                <p className="mt-1 text-xs text-muted-foreground">
                                  next challenger {candidate}
                                </p>
                              </div>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => void stagePromotion(entry.id, candidate)}
                                disabled={busy !== null || alreadyStaged}
                              >
                                {alreadyStaged ? "Staged" : "Stage canary"}
                              </Button>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                  <p className="mt-3 text-xs text-muted-foreground">
                    {lastCycle
                      ? `last cycle ${lastCycle.benchmarks?.passed ?? 0}/${lastCycle.benchmarks?.total ?? 0} passed`
                      : "No improvement cycle recorded yet."}
                  </p>
                </>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">
                  Challenger queues will appear here as lane candidates are staged.
                </p>
              )}
            </div>

            <div className="rounded-xl border border-border/60 bg-background/30 px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Governed promotions
              </p>
              {promotionControls ? (
                <>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {promotionControls.tiers.map((tier) => (
                      <Badge key={tier} variant="secondary">
                        {compactLabel(tier)}
                      </Badge>
                    ))}
                  </div>
                  {activePromotions.length > 0 ? (
                    <div className="mt-3 space-y-2">
                      {activePromotions.slice(0, 3).map((record) => (
                        <div
                          key={record.id}
                          className="surface-tile rounded-lg border px-3 py-2"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div className="min-w-0">
                              <p className="text-sm font-medium">{record.role_label}</p>
                              <p className="mt-1 text-xs text-muted-foreground">
                                {record.candidate} | {compactLabel(record.current_tier)} {"->"}{" "}
                                {compactLabel(record.target_tier)}
                              </p>
                            </div>
                            <Badge variant="outline">{compactLabel(record.status)}</Badge>
                          </div>
                          <div className="mt-3 flex flex-wrap gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => void transitionPromotion(record.id, "advance")}
                              disabled={busy !== null}
                            >
                              Advance
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => void transitionPromotion(record.id, "hold")}
                              disabled={busy !== null}
                            >
                              Hold
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => void transitionPromotion(record.id, "rollback")}
                              disabled={busy !== null}
                            >
                              Roll back
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                <p className="mt-3 text-sm text-muted-foreground">
                  No live promotion candidates yet. Stage the next challenger directly from the governance queue.
                </p>
                  )}
                </>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">
                  Release-ladder state will appear here once promotion controls are exposed by the runtime.
                </p>
              )}
            </div>

            <div className="surface-metric rounded-xl border px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Governed retirements
              </p>
              {retirementControls ? (
                <>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {retirementControls.stages.map((stage) => (
                      <Badge key={stage} variant="secondary">
                        {compactLabel(stage)}
                      </Badge>
                    ))}
                  </div>
                  {retirementControls.recent_retirements.length > 0 ? (
                    <div className="mt-3 space-y-2">
                      {retirementControls.recent_retirements.slice(0, 3).map((record) => (
                        <div
                          key={record.id}
                          className="surface-tile rounded-lg border px-3 py-2"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div className="min-w-0">
                              <p className="text-sm font-medium">{record.label}</p>
                              <p className="mt-1 text-xs text-muted-foreground">
                                {record.asset_class} | {compactLabel(record.current_stage)} {"->"}{" "}
                                {compactLabel(record.target_stage)}
                              </p>
                            </div>
                            <Badge variant="outline">{compactLabel(record.status)}</Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-3 text-sm text-muted-foreground">
                      No governed retirement rehearsals yet. Use the runtime ladder to exercise staged retirements without
                      deleting history.
                    </p>
                  )}
                  <p className="mt-3 text-xs text-muted-foreground">
                    {retirementControls.next_actions[0] ?? retirementGovernance.rule}
                  </p>
                </>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">
                  Retirement posture will appear here once live retirement controls are exposed by the runtime.
                </p>
              )}
            </div>

            <div className="surface-metric rounded-xl border px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Live cadence
              </p>
              {cadenceJobs.length > 0 ? (
                <div className="mt-2 space-y-2">
                  {cadenceJobs.map((job) => (
                    <div key={job.id} className="rounded-lg border border-border/50 bg-background/20 px-3 py-2">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-medium">{job.title}</p>
                        <Badge variant={job.current_state === "scheduled" ? "outline" : "secondary"}>
                          {compactLabel(job.current_state)}
                        </Badge>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {job.cadence}
                        {job.governor_reason ? ` | ${job.governor_reason}` : ""}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">
                  The intelligence cadence will appear here once the scheduler exposes live posture.
                </p>
              )}
            </div>

            <div className="rounded-xl border border-border/60 bg-background/30 px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Experiment evidence
              </p>
              {experimentLedger.recent_experiments.length > 0 ? (
                <div className="mt-2 space-y-2">
                  {experimentLedger.recent_experiments.slice(0, 3).map((experiment) => (
                    <div
                      key={experiment.id}
                    className="surface-tile rounded-lg border px-3 py-2"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-medium">{experiment.name}</p>
                        <Badge variant={experiment.passed ? "outline" : "destructive"}>
                          {experiment.passed ? "passed" : "failed"}
                        </Badge>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {compactLabel(experiment.category)} | {experiment.score.toFixed(1)} /{" "}
                        {experiment.max_score.toFixed(1)}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">
                  Recent proving-ground evidence will appear here once benchmark results are recorded.
                </p>
              )}
              <p className="mt-3 text-xs text-muted-foreground">
                {experimentLedger.promotion_linkage}
              </p>
            </div>

            <div className="surface-metric rounded-xl border px-3 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                Next actions
              </p>
              <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                {(nextActions.length > 0 ? nextActions : ["No immediate action required."]).map((action) => (
                  <li key={action}>{action}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
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
