"use client";

import Link from "next/link";
import { ArrowRight, Ban, Boxes, HardDrive, Shield, Workflow } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export interface MasterAtlasRelationshipMap {
  generated_at: string;
  summary: {
    capability_count: number;
    adopted_count: number;
    packet_ready_count: number;
    proving_count: number;
    blocked_packet_count: number;
    governance_posture: string;
    governance_blockers: string[];
    best_next_implementation_wave?: string | null;
    best_next_promotion_candidate?: string | null;
    turnover_status: string;
    turnover_ready_now: boolean;
    turnover_next_gate?: string | null;
    turnover_current_mode: string;
    turnover_target_mode: string;
    turnover_blocker_count: number;
    self_acceleration_status?: string | null;
    self_acceleration_ready_now?: boolean | null;
    provider_elasticity_limited?: boolean | null;
    provider_elasticity_blocking_provider_count?: number | null;
    checkpoint_slice_count?: number | null;
    checkpoint_slice_ready_for_checkpoint_count?: number | null;
    pilot_formal_eval_complete_count?: number | null;
    pilot_formal_eval_failed_count?: number | null;
    pilot_ready_for_formal_eval_count?: number | null;
    pilot_operator_smoke_only_count?: number | null;
    pilot_readiness_blocked_count?: number | null;
    next_checkpoint_slice?: {
      id?: string | null;
      title?: string | null;
      order?: number | null;
      status?: string | null;
      blocking_gate?: string | null;
      owner_workstreams?: string[];
    } | null;
  } | null;
  turnover_readiness: {
    current_mode: string;
    target_mode: string;
    autonomous_turnover_status: string;
    autonomous_turnover_ready_now: boolean;
    next_gate?: string | null;
    blocker_count: number;
    blockers: string[];
    required_before_turnover: string[];
    operator_answer: string;
    provider_gate_state?: string | null;
    provider_elasticity_limited?: boolean | null;
    provider_elasticity_blocking_provider_count?: number | null;
    provider_elasticity_blocking_provider_ids?: string[];
    self_acceleration_status?: string | null;
    self_acceleration_ready_now?: boolean | null;
    work_economy_status?: string | null;
    work_economy_ready_now?: boolean | null;
    work_economy_blocked_burn_class_ids?: string[];
    work_economy_degraded_burn_class_ids?: string[];
    burn_dispatch_phase?: number | null;
    burn_dispatch_phase_label?: string | null;
    dispatchable_safe_surface_queue_count?: number | null;
    autonomous_queue_count?: number | null;
    dispatchable_autonomous_queue_count?: number | null;
    top_dispatchable_autonomous_task_id?: string | null;
    top_dispatchable_autonomous_task_title?: string | null;
    checkpoint_slice_summary?: {
      sequence_id?: string | null;
      total?: number | null;
      ready_for_checkpoint?: number | null;
      active?: number | null;
      approval_gated?: number | null;
      published?: number | null;
    } | null;
    next_checkpoint_slice?: {
      id?: string | null;
      title?: string | null;
      order?: number | null;
      status?: string | null;
      blocking_gate?: string | null;
      owner_workstreams?: string[];
    } | null;
  } | null;
  authority_surfaces: Array<{
    id: string;
    label: string;
    authority_class: "adopted_system" | "build_system" | "operator_local" | "archive_evidence";
    root: string;
    role: string;
    front_door: string;
  }>;
  promotion_flow: {
    source_label: string;
    packet_ready_count: number;
    next_promotion_candidate: string | null;
    target_label: string;
    governance_posture: string | null;
  };
  blocked_packets: Array<{
    packet_id: string;
    capability_id: string;
    blocked_by: string[];
    runtime_target: string;
  }>;
  node_capacity: Array<{
    node_id: string;
    node_role: string;
    gpu_count: number;
    interactive_reserve_gpu_slots: number;
    background_fill_gpu_slots: number;
    utilization_targets: {
      interactive_reserve_floor_gpu_slots: number;
      background_harvest_target_gpu_slots: number;
      max_noncritical_preemptible_gpu_slots: number;
    } | null;
  }>;
  dispatch_lanes: Array<{
    lane_id: string;
    provider_id: string;
    reserve_class: string;
    max_parallel_slots: number;
    reserved_parallel_slots: number;
    harvestable_parallel_slots: number;
    selection_reason: string | null;
  }>;
  quota_posture: {
    quota_posture: string;
    respect_vendor_policy_before_harvest: boolean;
    other_metered_disabled_for_auto_harvest_by_default: boolean;
    record_count: number;
    degraded_record_count: number;
    low_confidence_record_count: number;
    degraded_records: Array<{
      family_id: string;
      degraded_reason: string;
    }>;
    local_compute_capacity?: {
      remaining_units: number;
      sample_posture: string;
      scheduler_queue_depth: number;
      scheduler_slot_count: number;
      harvestable_scheduler_slot_count: number;
      harvestable_by_zone: Record<string, number>;
      harvestable_by_slot: Record<string, number>;
      provisional_harvest_candidate_count: number;
      provisional_harvestable_by_node: Record<string, number>;
      open_harvest_slot_ids: string[];
      open_harvest_slot_target_ids: string[];
      scheduler_conflict_gpu_count: number;
    } | null;
  } | null;
  router_shadow_summary: {
    phase: number;
    phase_label: string;
    shadow_disagreement_rate: number;
    routing_proof_total: number;
    routing_proof_failed: number;
    ready_for_phase_1: boolean;
    ready_for_phase_2: boolean;
  } | null;
  next_required_approval: {
    approval_class: string;
    label: string;
    reason: string;
    allowed_actions: string[];
  } | null;
  safe_surface_summary: {
    last_outcome?: string | null;
    last_success_at?: string | null;
    current_task_id?: string | null;
    on_deck_task_id?: string | null;
    queue_count: number;
    dispatchable_queue_count?: number | null;
    approval_gated_queue_count?: number | null;
    blocked_queue_count?: number | null;
    top_dispatchable_task_id?: string | null;
    top_dispatchable_title?: string | null;
    current_task_threads: number;
  } | null;
  autonomous_queue_summary: {
    queue_count: number;
    dispatchable_queue_count?: number | null;
    blocked_queue_count?: number | null;
    top_dispatchable_task_id?: string | null;
    top_dispatchable_title?: string | null;
    top_dispatchable_value_class?: string | null;
    top_dispatchable_lane_family?: string | null;
  } | null;
  governed_dispatch_execution?: {
    status?: string | null;
    dispatch_outcome?: string | null;
    backlog_id?: string | null;
    backlog_status?: string | null;
    task_id?: string | null;
    task_status?: string | null;
    governor_level?: string | null;
    governor_reason?: string | null;
    repaired_stale_task_id?: string | null;
    report_path?: string | null;
  } | null;
  governed_dispatch_execution_report_path?: string | null;
  lane_recommendations: Array<{
    task_class: string;
    sensitivity_class: string;
    preferred_lane: string;
    secondary_lane: string;
    overflow_lane: string;
    default_execution_mode: string;
    provider: string;
    runtime: string;
    privacy: string;
    degraded: boolean;
    degraded_failure_class?: string | null;
    selection_reason: string;
    quota_signal: {
      provider_or_family?: string | null;
      confidence?: string | null;
      remaining_units?: number | null;
      budget_remaining_usd?: number | null;
      degraded_reason?: string | null;
    } | null;
  }>;
}

function compactLabel(value: string | null | undefined) {
  if (!value) return "n/a";
  return value.replace(/[-_]/g, " ");
}

function formatCapacityEntries(values: Record<string, number> | null | undefined) {
  if (!values) return [];
  return Object.entries(values)
    .filter(([, amount]) => typeof amount === "number")
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([label, amount]) => `${label}:${amount}`);
}

function toneClasses(authorityClass: MasterAtlasRelationshipMap["authority_surfaces"][number]["authority_class"]) {
  switch (authorityClass) {
    case "adopted_system":
      return "border-[color:var(--signal-success)]/30 bg-[color:var(--signal-success)]/5";
    case "build_system":
      return "border-[color:var(--signal-info)]/30 bg-[color:var(--signal-info)]/5";
    case "operator_local":
      return "border-[color:var(--signal-warning)]/30 bg-[color:var(--signal-warning)]/5";
    default:
      return "border-border/70 bg-muted/20";
  }
}

export function MasterAtlasRelationshipPanel({ map }: { map: MasterAtlasRelationshipMap }) {
  return (
    <Card className="surface-panel" id="master-atlas-map">
      <CardHeader className="pb-3">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <CardTitle className="text-lg">Master Atlas Relationship Map</CardTitle>
            <CardDescription>
              One synthesized view of authority, promotion flow, local capacity, and lane orchestration across the
              federated Athanor stack.
            </CardDescription>
          </div>
          {map.summary ? (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <div className="surface-metric rounded-xl border px-3 py-2">
                <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Capabilities</p>
                <p className="mt-1 text-sm font-semibold">
                  {map.summary.capability_count} total
                </p>
                <p className="text-[11px] text-muted-foreground">
                  {map.summary.adopted_count} adopted
                </p>
              </div>
              <div className="surface-metric rounded-xl border px-3 py-2">
                <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Promotion</p>
                <p className="mt-1 text-sm font-semibold">
                  {map.summary.packet_ready_count} ready
                </p>
                <p className="text-[11px] text-muted-foreground">
                  {map.summary.proving_count} proving
                </p>
              </div>
              <div className="surface-metric rounded-xl border px-3 py-2">
                <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Governance</p>
                <p className="mt-1 text-sm font-semibold">{compactLabel(map.summary.governance_posture)}</p>
                <p className="text-[11px] text-muted-foreground">
                  {map.summary.blocked_packet_count} blocked packets
                </p>
              </div>
              <div className="surface-metric rounded-xl border px-3 py-2">
                <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Next Wave</p>
                <p className="mt-1 text-sm font-semibold">
                  {compactLabel(map.summary.best_next_implementation_wave)}
                </p>
                <p className="text-[11px] text-muted-foreground">
                  {compactLabel(map.summary.best_next_promotion_candidate)}
                </p>
              </div>
            </div>
          ) : null}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        <section className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Shield className="h-4 w-4 text-muted-foreground" />
            Authority Surfaces
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {map.authority_surfaces.map((surface) => (
              <Link
                key={surface.id}
                href={surface.front_door}
                className={`rounded-2xl border p-4 transition hover:bg-accent/60 ${toneClasses(surface.authority_class)}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold">{surface.label}</p>
                    <p className="mt-1 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                      {compactLabel(surface.authority_class)}
                    </p>
                  </div>
                  <Badge variant="outline" className="text-[10px]">
                    {surface.front_door}
                  </Badge>
                </div>
                <p className="mt-3 text-sm text-muted-foreground">{surface.role}</p>
                <p className="mt-3 font-mono text-[11px] text-muted-foreground">{surface.root}</p>
              </Link>
            ))}
          </div>
        </section>

        <section className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Workflow className="h-4 w-4 text-muted-foreground" />
            Promotion Flow
          </div>
          <div className="grid gap-3 lg:grid-cols-[1fr_auto_1fr_auto_1fr]">
            <div className="surface-metric rounded-2xl border p-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Source</p>
              <p className="mt-1 text-sm font-semibold">{map.promotion_flow.source_label}</p>
              <p className="mt-2 text-sm text-muted-foreground">
                {map.promotion_flow.packet_ready_count} packet-ready capabilities are staged here.
              </p>
            </div>
            <div className="hidden items-center justify-center lg:flex">
              <ArrowRight className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="surface-metric rounded-2xl border p-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Current Handoff</p>
              <p className="mt-1 text-sm font-semibold">{compactLabel(map.promotion_flow.next_promotion_candidate)}</p>
              <p className="mt-2 text-sm text-muted-foreground">
                Governance posture: {compactLabel(map.promotion_flow.governance_posture)}
              </p>
            </div>
            <div className="hidden items-center justify-center lg:flex">
              <ArrowRight className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="surface-metric rounded-2xl border p-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Target</p>
              <p className="mt-1 text-sm font-semibold">{map.promotion_flow.target_label}</p>
              <p className="mt-2 text-sm text-muted-foreground">
                Devstack proves and packets; Athanor adopts and governs.
              </p>
            </div>
          </div>
        </section>

        {map.turnover_readiness ? (
          <section className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Workflow className="h-4 w-4 text-muted-foreground" />
              Turnover Readiness
            </div>
            <div className="grid gap-3 lg:grid-cols-[0.9fr_1.1fr]">
              <div className="surface-metric rounded-2xl border p-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Current posture</p>
                <p className="mt-1 text-sm font-semibold">
                  {compactLabel(map.turnover_readiness.autonomous_turnover_status)}
                </p>
                <p className="mt-2 text-sm text-muted-foreground">{map.turnover_readiness.operator_answer}</p>
                <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] text-muted-foreground">
                  <div className="rounded-xl border px-2 py-2">
                    <p className="uppercase tracking-[0.15em]">Now</p>
                    <p className="mt-1 text-sm font-semibold text-foreground">
                      {compactLabel(map.turnover_readiness.current_mode)}
                    </p>
                  </div>
                  <div className="rounded-xl border px-2 py-2">
                    <p className="uppercase tracking-[0.15em]">Target</p>
                    <p className="mt-1 text-sm font-semibold text-foreground">
                      {compactLabel(map.turnover_readiness.target_mode)}
                    </p>
                  </div>
                </div>
                <p className="mt-3 text-sm text-muted-foreground">
                  self acceleration {compactLabel(map.turnover_readiness.self_acceleration_status)} | provider gate{" "}
                  {compactLabel(map.turnover_readiness.provider_gate_state)}
                </p>
                <p className="mt-2 text-sm text-muted-foreground">
                  provider elasticity{" "}
                  {map.turnover_readiness.provider_elasticity_limited
                    ? `limited (${map.turnover_readiness.provider_elasticity_blocking_provider_count ?? 0} blocked)`
                    : "ready"}{" "}
                  | burn dispatch {compactLabel(map.turnover_readiness.burn_dispatch_phase_label)}
                </p>
              </div>

              <div className="surface-metric rounded-2xl border p-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Before full turnover</p>
                <p className="mt-1 text-sm font-semibold">
                  Next gate: {compactLabel(map.turnover_readiness.next_gate)}
                </p>
                <div className="mt-3 space-y-2">
                  {map.turnover_readiness.required_before_turnover.map((item) => (
                    <p key={item} className="text-sm text-muted-foreground">
                      {item}
                    </p>
                  ))}
                </div>
                {map.turnover_readiness.blockers.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {map.turnover_readiness.blockers.slice(0, 6).map((blocker) => (
                      <Badge key={blocker} variant="secondary" className="text-[10px]">
                        {compactLabel(blocker)}
                      </Badge>
                    ))}
                  </div>
                ) : null}
                {map.turnover_readiness.next_checkpoint_slice ? (
                  <div className="mt-4 rounded-xl border px-3 py-3">
                    <p className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground">Checkpoint publication</p>
                    <p className="mt-1 text-sm font-semibold text-foreground">
                      {map.turnover_readiness.next_checkpoint_slice.title ??
                        compactLabel(map.turnover_readiness.next_checkpoint_slice.id)}
                    </p>
                    <p className="mt-2 text-sm text-muted-foreground">
                      slice {map.turnover_readiness.next_checkpoint_slice.order ?? "?"} |{" "}
                      {compactLabel(map.turnover_readiness.next_checkpoint_slice.status)} |{" "}
                      {map.turnover_readiness.checkpoint_slice_summary?.ready_for_checkpoint ?? 0} ready of{" "}
                      {map.turnover_readiness.checkpoint_slice_summary?.total ?? 0}
                    </p>
                    {map.turnover_readiness.next_checkpoint_slice.blocking_gate &&
                    map.turnover_readiness.next_checkpoint_slice.blocking_gate !== "none" ? (
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        <Badge variant="secondary" className="text-[10px]">
                          {compactLabel(map.turnover_readiness.next_checkpoint_slice.blocking_gate)}
                        </Badge>
                      </div>
                    ) : null}
                  </div>
                ) : null}
                {map.summary ? (
                  <div className="mt-4 rounded-xl border px-3 py-3">
                    <p className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground">Pilot conversion</p>
                    <p className="mt-1 text-sm font-semibold text-foreground">
                      {map.summary.pilot_formal_eval_complete_count ?? 0} complete |{" "}
                      {map.summary.pilot_operator_smoke_only_count ?? 0} smoke-only |{" "}
                      {map.summary.pilot_readiness_blocked_count ?? 0} blocked
                    </p>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {map.summary.pilot_formal_eval_failed_count ?? 0} failed |{" "}
                      {map.summary.pilot_ready_for_formal_eval_count ?? 0} ready for formal eval
                    </p>
                  </div>
                ) : null}
              </div>
            </div>
          </section>
        ) : null}

        <section className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Workflow className="h-4 w-4 text-muted-foreground" />
            Routing and Quota Posture
          </div>
          <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-4">
            <div className="surface-metric rounded-2xl border p-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Quota posture</p>
              <p className="mt-1 text-sm font-semibold">
                {compactLabel(map.quota_posture?.quota_posture)}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                {map.quota_posture?.degraded_record_count ?? 0} degraded | {map.quota_posture?.low_confidence_record_count ?? 0} low-confidence
              </p>
            </div>
            <div className="surface-metric rounded-2xl border p-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Shadow rollout</p>
              <p className="mt-1 text-sm font-semibold">
                {compactLabel(map.router_shadow_summary?.phase_label)}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                disagreement {(map.router_shadow_summary?.shadow_disagreement_rate ?? 0).toFixed(3)} | proof {map.router_shadow_summary?.routing_proof_total ?? 0}
              </p>
            </div>
            <div className="surface-metric rounded-2xl border p-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Next approval</p>
              <p className="mt-1 text-sm font-semibold">
                {map.next_required_approval?.label ?? "No human approval is currently leading the queue."}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                {map.next_required_approval
                  ? `${compactLabel(map.next_required_approval.approval_class)} | ${compactLabel(map.next_required_approval.reason)}`
                  : "Approval pressure is clear right now; no manual gate is leading the queue."}
              </p>
            </div>
            <div className="surface-metric rounded-2xl border p-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Autonomous queue</p>
              <p className="mt-1 text-sm font-semibold">
                {map.autonomous_queue_summary?.queue_count ??
                  map.turnover_readiness?.autonomous_queue_count ??
                  0} queued
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                {map.autonomous_queue_summary?.dispatchable_queue_count ??
                  map.turnover_readiness?.dispatchable_autonomous_queue_count ??
                  0} dispatchable |{" "}
                {map.autonomous_queue_summary?.blocked_queue_count ?? 0} approval held
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                top{" "}
                {map.autonomous_queue_summary?.top_dispatchable_title ??
                  map.turnover_readiness?.top_dispatchable_autonomous_task_title ??
                  "no dispatchable task selected"}
              </p>
              {map.autonomous_queue_summary?.top_dispatchable_value_class ? (
                <p className="mt-2 text-sm text-muted-foreground">
                  {compactLabel(map.autonomous_queue_summary.top_dispatchable_value_class)} via{" "}
                  {compactLabel(map.autonomous_queue_summary.top_dispatchable_lane_family)}
                </p>
              ) : null}
              <p className="mt-2 text-sm text-muted-foreground">
                safe surface {map.safe_surface_summary?.queue_count ?? 0} queued | outcome{" "}
                {compactLabel(map.safe_surface_summary?.last_outcome)}
              </p>
            </div>
          </div>
          {map.governed_dispatch_execution ? (
            <div className="surface-metric rounded-2xl border p-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Governed dispatch handoff</p>
              <p className="mt-1 text-sm font-semibold">
                {compactLabel(map.governed_dispatch_execution.status)} |{" "}
                {compactLabel(map.governed_dispatch_execution.dispatch_outcome)}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                backlog {compactLabel(map.governed_dispatch_execution.backlog_status)} | task{" "}
                {compactLabel(map.governed_dispatch_execution.task_status)}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                governor {compactLabel(map.governed_dispatch_execution.governor_level)} |{" "}
                {map.governed_dispatch_execution.governor_reason ?? "No governor rationale recorded."}
              </p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {map.governed_dispatch_execution.backlog_id ? (
                  <Badge variant="secondary" className="text-[10px]">
                    backlog {map.governed_dispatch_execution.backlog_id}
                  </Badge>
                ) : null}
                {map.governed_dispatch_execution.task_id ? (
                  <Badge variant="secondary" className="text-[10px]">
                    task {map.governed_dispatch_execution.task_id}
                  </Badge>
                ) : null}
                {map.governed_dispatch_execution.repaired_stale_task_id ? (
                  <Badge variant="outline" className="text-[10px]">
                    repaired {map.governed_dispatch_execution.repaired_stale_task_id}
                  </Badge>
                ) : null}
              </div>
            </div>
          ) : null}
          {map.next_required_approval?.allowed_actions?.length ? (
            <div className="flex flex-wrap gap-1.5">
              {map.next_required_approval.allowed_actions.slice(0, 6).map((action) => (
                <Badge key={action} variant="secondary" className="text-[10px]">
                  {compactLabel(action)}
                </Badge>
              ))}
            </div>
          ) : null}
          {map.turnover_readiness || map.quota_posture?.local_compute_capacity ? (
            <div className="grid gap-3 lg:grid-cols-2">
              <div className="surface-metric rounded-2xl border p-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Work economy</p>
                <p className="mt-1 text-sm font-semibold">
                  {compactLabel(map.turnover_readiness?.work_economy_status)}
                </p>
                <p className="mt-2 text-sm text-muted-foreground">
                  {map.turnover_readiness?.work_economy_ready_now
                    ? "Live compounding is currently ready."
                    : "At least one work-economy gate still needs follow-through."}
                </p>
                <p className="mt-2 text-sm text-muted-foreground">
                  burn dispatch {compactLabel(map.turnover_readiness?.burn_dispatch_phase_label)} | safe surface{" "}
                  {map.turnover_readiness?.dispatchable_safe_surface_queue_count ?? 0} dispatchable | autonomous{" "}
                  {map.turnover_readiness?.dispatchable_autonomous_queue_count ?? 0} dispatchable
                </p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {(map.turnover_readiness?.work_economy_blocked_burn_class_ids ?? []).map((burnClass) => (
                    <Badge key={`blocked-${burnClass}`} variant="destructive" className="text-[10px]">
                      blocked {compactLabel(burnClass)}
                    </Badge>
                  ))}
                  {(map.turnover_readiness?.work_economy_degraded_burn_class_ids ?? []).map((burnClass) => (
                    <Badge key={`degraded-${burnClass}`} variant="secondary" className="text-[10px]">
                      degraded {compactLabel(burnClass)}
                    </Badge>
                  ))}
                  {!(map.turnover_readiness?.work_economy_blocked_burn_class_ids?.length ?? 0) &&
                  !(map.turnover_readiness?.work_economy_degraded_burn_class_ids?.length ?? 0) ? (
                    <Badge variant="outline" className="text-[10px]">
                      no burn classes blocked
                    </Badge>
                  ) : null}
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {(map.quota_posture?.degraded_records ?? []).map((record) => (
                    <Badge
                      key={`${record.family_id}-${record.degraded_reason}`}
                      variant="secondary"
                      className="text-[10px]"
                    >
                      {compactLabel(record.family_id)} | {compactLabel(record.degraded_reason)}
                    </Badge>
                  ))}
                  {!(map.quota_posture?.degraded_records?.length ?? 0) ? (
                    <p className="text-sm text-muted-foreground">No degraded quota families are currently recorded.</p>
                  ) : null}
                </div>
              </div>

              <div className="surface-metric rounded-2xl border p-4">
                <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Local harvest window</p>
                <p className="mt-1 text-sm font-semibold">
                  {map.quota_posture?.local_compute_capacity
                    ? `${map.quota_posture.local_compute_capacity.remaining_units} local units available`
                    : "No local harvest telemetry is currently attached."}
                </p>
                {map.quota_posture?.local_compute_capacity ? (
                  <>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {compactLabel(map.quota_posture.local_compute_capacity.sample_posture)} | queue depth{" "}
                      {map.quota_posture.local_compute_capacity.scheduler_queue_depth} | harvestable slots{" "}
                      {map.quota_posture.local_compute_capacity.harvestable_scheduler_slot_count}
                    </p>
                    <p className="mt-2 text-sm text-muted-foreground">
                      scheduler conflicts {map.quota_posture.local_compute_capacity.scheduler_conflict_gpu_count} | total
                      slots {map.quota_posture.local_compute_capacity.scheduler_slot_count}
                    </p>
                    <p className="mt-2 text-sm text-muted-foreground">
                      provisional outside scheduler{" "}
                      {map.quota_posture.local_compute_capacity.provisional_harvest_candidate_count}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {formatCapacityEntries(map.quota_posture.local_compute_capacity.harvestable_by_zone).map((entry) => (
                        <Badge key={`zone-${entry}`} variant="secondary" className="text-[10px]">
                          zone {entry}
                        </Badge>
                      ))}
                      {formatCapacityEntries(map.quota_posture.local_compute_capacity.harvestable_by_slot).map((entry) => (
                        <Badge key={`slot-${entry}`} variant="outline" className="text-[10px]">
                          slot {entry}
                        </Badge>
                      ))}
                      {formatCapacityEntries(
                        map.quota_posture.local_compute_capacity.provisional_harvestable_by_node
                      ).map((entry) => (
                        <Badge key={`provisional-${entry}`} variant="secondary" className="text-[10px]">
                          provisional {entry}
                        </Badge>
                      ))}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {map.quota_posture.local_compute_capacity.open_harvest_slot_target_ids.map((targetId) => (
                        <Badge key={targetId} variant="outline" className="text-[10px]">
                          target {compactLabel(targetId)}
                        </Badge>
                      ))}
                      {!map.quota_posture.local_compute_capacity.open_harvest_slot_target_ids.length ? (
                        <p className="text-sm text-muted-foreground">No open harvest targets are currently recorded.</p>
                      ) : null}
                    </div>
                  </>
                ) : (
                  <p className="mt-2 text-sm text-muted-foreground">
                    Capacity telemetry needs to refresh before harvest-slot provenance can be shown here.
                  </p>
                )}
              </div>
            </div>
          ) : null}
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-medium">
              <HardDrive className="h-4 w-4 text-muted-foreground" />
              Node Capacity Envelopes
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {map.node_capacity.map((node) => (
                <div key={node.node_id} className="surface-metric rounded-2xl border p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold">{node.node_id.toUpperCase()}</p>
                      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                        {compactLabel(node.node_role)}
                      </p>
                    </div>
                    <Badge variant="secondary">{node.gpu_count} GPU</Badge>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-[11px] text-muted-foreground">
                    <div className="rounded-xl border px-2 py-2">
                      <p className="uppercase tracking-[0.15em]">Reserve</p>
                      <p className="mt-1 text-sm font-semibold text-foreground">{node.interactive_reserve_gpu_slots}</p>
                    </div>
                    <div className="rounded-xl border px-2 py-2">
                      <p className="uppercase tracking-[0.15em]">Fill</p>
                      <p className="mt-1 text-sm font-semibold text-foreground">{node.background_fill_gpu_slots}</p>
                    </div>
                    <div className="rounded-xl border px-2 py-2">
                      <p className="uppercase tracking-[0.15em]">Preempt</p>
                      <p className="mt-1 text-sm font-semibold text-foreground">
                        {node.utilization_targets?.max_noncritical_preemptible_gpu_slots ?? 0}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Boxes className="h-4 w-4 text-muted-foreground" />
              Dispatch Lanes
            </div>
            <div className="space-y-3">
              {map.dispatch_lanes.map((lane) => (
                <div key={lane.lane_id} className="surface-metric rounded-2xl border p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold">{compactLabel(lane.lane_id)}</p>
                      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                        {compactLabel(lane.reserve_class)}
                      </p>
                    </div>
                    <Badge variant="outline">{compactLabel(lane.provider_id)}</Badge>
                  </div>
                  <p className="mt-3 text-sm text-muted-foreground">
                    {lane.selection_reason ?? "No selection reason recorded."}
                  </p>
                  <p className="mt-2 text-[11px] text-muted-foreground">
                    {lane.reserved_parallel_slots} reserved / {lane.harvestable_parallel_slots} harvestable / {lane.max_parallel_slots} max
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Boxes className="h-4 w-4 text-muted-foreground" />
            Lane Recommendations
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {map.lane_recommendations.map((lane) => (
              <div key={`${lane.task_class}-${lane.preferred_lane}`} className="surface-metric rounded-2xl border p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold">{compactLabel(lane.task_class)}</p>
                    <p className="mt-1 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                      {compactLabel(lane.sensitivity_class)}
                    </p>
                  </div>
                  <Badge variant={lane.degraded ? "destructive" : "outline"}>
                    {lane.degraded ? "degraded" : "preferred"}
                  </Badge>
                </div>
                <p className="mt-3 text-sm text-muted-foreground">
                  {compactLabel(lane.preferred_lane)} via {compactLabel(lane.default_execution_mode)}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  {lane.selection_reason}
                </p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  <Badge variant="secondary" className="text-[10px]">
                    secondary {compactLabel(lane.secondary_lane)}
                  </Badge>
                  <Badge variant="secondary" className="text-[10px]">
                    overflow {compactLabel(lane.overflow_lane)}
                  </Badge>
                  {lane.quota_signal?.confidence ? (
                    <Badge variant="secondary" className="text-[10px]">
                      quota {compactLabel(lane.quota_signal.confidence)}
                    </Badge>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Ban className="h-4 w-4 text-muted-foreground" />
            Current Blockers
          </div>
          {map.blocked_packets.length > 0 ? (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {map.blocked_packets.map((packet) => (
                <div key={packet.packet_id} className="surface-metric rounded-2xl border p-4">
                  <p className="text-sm font-semibold">{compactLabel(packet.capability_id)}</p>
                  <p className="mt-1 font-mono text-[11px] text-muted-foreground">{packet.packet_id}</p>
                  <p className="mt-2 text-sm text-muted-foreground">{packet.runtime_target}</p>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {packet.blocked_by.slice(0, 4).map((blocker) => (
                      <Badge key={blocker} variant="secondary" className="text-[10px]">
                        {compactLabel(blocker)}
                      </Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No packet-level blockers are currently recorded.</p>
          )}
        </section>
      </CardContent>
    </Card>
  );
}
