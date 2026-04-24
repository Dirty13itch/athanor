import { access, readFile } from "node:fs/promises";
import path from "node:path";

export interface MasterAtlasSummary {
  generated_at: string;
  capability_count: number;
  adopted_count: number;
  packet_ready_count: number;
  proving_count: number;
  blocked_capability_count: number;
  blocked_packet_count: number;
  governance_posture: string;
  governance_blocker_count: number;
  governance_blockers: string[];
  top_missing_proof?: string | null;
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
  capacity_harvest_state?: string | null;
  capacity_harvest_ready_now?: boolean | null;
  capacity_harvest_slot_count?: number | null;
  provider_elasticity_limited?: boolean | null;
  provider_elasticity_blocking_provider_count?: number | null;
  checkpoint_slice_count?: number | null;
  checkpoint_slice_ready_for_checkpoint_count?: number | null;
  pilot_formal_eval_complete_count?: number | null;
  pilot_formal_eval_failed_count?: number | null;
  pilot_ready_for_formal_eval_count?: number | null;
  pilot_operator_smoke_only_count?: number | null;
  pilot_readiness_blocked_count?: number | null;
  goose_stage?: string | null;
  goose_readiness?: string | null;
  goose_next_gate?: string | null;
  goose_next_action?: string | null;
  next_checkpoint_slice?: {
    id?: string | null;
    title?: string | null;
    order?: number | null;
    status?: string | null;
    blocking_gate?: string | null;
    owner_workstreams?: string[];
  } | null;
  alert_state?: string | null;
  quota_posture?: string | null;
  shadow_phase?: number | null;
  shadow_phase_label?: string | null;
  shadow_disagreement_rate?: number | null;
  lane_recommendation_count?: number | null;
  active_override_count?: number | null;
  safe_surface_queue_count?: number | null;
  autonomous_queue_count?: number | null;
  autonomous_dispatchable_queue_count?: number | null;
  autonomous_top_task_id?: string | null;
  autonomous_top_task_title?: string | null;
  project_factory_operating_mode?: string | null;
  project_factory_top_priority_project_id?: string | null;
  project_factory_top_priority_project_label?: string | null;
  project_factory_broad_ready?: boolean | null;
  accepted_project_output_count?: number | null;
  pending_project_output_candidate_count?: number | null;
  pending_hybrid_project_output_count?: number | null;
  project_factory_latest_pending_project_id?: string | null;
  project_output_stage_met?: boolean | null;
  next_required_approval?: {
    approval_class?: string | null;
    label?: string | null;
    reason?: string | null;
    allowed_actions?: string[];
  } | null;
  recommendation_summaries: Array<{
    id: string;
    subject: string;
    summary: string;
    reason: string;
  }>;
}

export interface GooseEvidenceSummary {
  capability_id: string;
  goose_stage: string | null;
  label: string;
  readiness_state: string | null;
  formal_eval_status: string | null;
  formal_eval_at: string | null;
  formal_eval_successes: number | null;
  formal_eval_failures: number | null;
  formal_eval_errors: number | null;
  formal_eval_duration_ms: number | null;
  operator_test_status: string | null;
  request_surface_hint: string | null;
  next_action: string | null;
  next_formal_gate: string | null;
  packet_path: string | null;
  packet_status: string | null;
  approval_state: string | null;
  proof_state: string | null;
  source_safe_remaining: string[];
  approval_gated_remaining: string[];
  command: string | null;
  command_available_locally: boolean | null;
  command_inventory_status: string | null;
  command_inventory_version: string | null;
  command_local_path: string | null;
  wrapper_mode: string | null;
}

export interface GovernedDispatchExecutionSummary {
  generated_at: string | null;
  source_of_truth: string | null;
  report_path: string | null;
  status: string | null;
  dispatch_outcome: string | null;
  claim_id: string | null;
  current_task_id: string | null;
  current_task_title: string | null;
  agent_server_base_url: string | null;
  backlog_id: string | null;
  backlog_status: string | null;
  dispatch_path: string | null;
  dispatch_status_code: number | null;
  governor_level: string | null;
  governor_reason: string | null;
  error: string | null;
  task_id: string | null;
  task_status: string | null;
  task_source?: string | null;
  retry_of_task_id?: string | null;
  retry_count?: number | null;
  retry_lineage_depth?: number | null;
  recovery_event?: string | null;
  recovery_reason?: string | null;
  resilience_state?: string | null;
  advisory_blockers?: string[];
}

export interface MasterAtlasRelationshipMap {
  generated_at: string;
  available?: boolean;
  degraded?: boolean;
  detail?: string | null;
  source?: string | null;
  error?: string | null;
  summary: MasterAtlasSummary | null;
  goose_evidence_summary?: GooseEvidenceSummary | null;
  governed_dispatch_execution?: GovernedDispatchExecutionSummary | null;
  governed_dispatch_execution_report_path?: string | null;
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
    capacity_harvest_summary?: {
      observed_at?: string | null;
      sample_age_seconds?: number | null;
      sample_posture?: string | null;
      scheduler_queue_depth?: number | null;
      scheduler_slot_count?: number | null;
      harvestable_scheduler_slot_count?: number | null;
      harvestable_zone_count?: number | null;
      harvestable_zone_ids?: string[];
      provisional_harvest_candidate_count?: number | null;
      protected_reserve_slot_count?: number | null;
      admission_state?: string | null;
      ready_for_harvest_now?: boolean | null;
    } | null;
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
    governed_dispatch_status?: string | null;
    governed_current_task_id?: string | null;
    governed_on_deck_task_id?: string | null;
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
    governed_dispatch_claim?: {
      status?: string | null;
      current_task_id?: string | null;
      current_task_title?: string | null;
      on_deck_task_id?: string | null;
      on_deck_task_title?: string | null;
      preferred_lane_family?: string | null;
      approved_mutation_class?: string | null;
      approved_mutation_label?: string | null;
      proof_command_or_eval_surface?: string | null;
    } | null;
  } | null;
  governed_dispatch_state: {
    status?: string | null;
    dispatch_outcome?: string | null;
    claim_id?: string | null;
    current_task_id?: string | null;
    current_task_title?: string | null;
    on_deck_task_id?: string | null;
    on_deck_task_title?: string | null;
    preferred_lane_family?: string | null;
    approved_mutation_label?: string | null;
    proof_command_or_eval_surface?: string | null;
    queue_count?: number | null;
    dispatchable_queue_count?: number | null;
    blocked_queue_count?: number | null;
    safe_surface_queue_count?: number | null;
    safe_surface_dispatchable_queue_count?: number | null;
    recent_dispatch_outcome_count?: number | null;
    provider_gate_state?: string | null;
    work_economy_status?: string | null;
    report_path?: string | null;
    materialization?: {
      status?: string | null;
      backlog_id?: string | null;
      backlog_status?: string | null;
      report_path?: string | null;
      error?: string | null;
    } | null;
    execution?: GovernedDispatchExecutionSummary | null;
  } | null;
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

function candidatePaths() {
  return [
    path.resolve(process.cwd(), "src", "generated", "master-atlas.json"),
    path.resolve(process.cwd(), "projects", "dashboard", "src", "generated", "master-atlas.json"),
  ];
}

export function buildFallbackMasterAtlasRelationshipMap(
  detail: string,
  error = detail,
): MasterAtlasRelationshipMap {
  return {
    generated_at: new Date().toISOString(),
    available: false,
    degraded: true,
    detail,
    source: "master-atlas-fallback",
    error,
    summary: null,
    goose_evidence_summary: null,
    governed_dispatch_execution: null,
    governed_dispatch_execution_report_path: null,
    turnover_readiness: {
      current_mode: "unknown",
      target_mode: "unknown",
      autonomous_turnover_status: "unknown",
      autonomous_turnover_ready_now: false,
      next_gate: null,
      blocker_count: 0,
      blockers: [],
      required_before_turnover: [],
      operator_answer: detail,
      provider_gate_state: "unknown",
      provider_elasticity_limited: null,
      provider_elasticity_blocking_provider_count: null,
      provider_elasticity_blocking_provider_ids: [],
      self_acceleration_status: "unknown",
      self_acceleration_ready_now: null,
      capacity_harvest_summary: null,
      work_economy_status: "unknown",
      work_economy_ready_now: null,
      work_economy_blocked_burn_class_ids: [],
      work_economy_degraded_burn_class_ids: [],
      burn_dispatch_phase: null,
      burn_dispatch_phase_label: "unknown",
      dispatchable_safe_surface_queue_count: 0,
      autonomous_queue_count: 0,
      dispatchable_autonomous_queue_count: 0,
      top_dispatchable_autonomous_task_id: null,
      top_dispatchable_autonomous_task_title: null,
      checkpoint_slice_summary: null,
      next_checkpoint_slice: null,
    },
    authority_surfaces: [],
    promotion_flow: {
      source_label: "Devstack proof lanes",
      packet_ready_count: 0,
      next_promotion_candidate: null,
      target_label: "Athanor adopted truth",
      governance_posture: null,
    },
    blocked_packets: [],
    node_capacity: [],
    dispatch_lanes: [],
    quota_posture: null,
    router_shadow_summary: null,
    next_required_approval: null,
    safe_surface_summary: {
      last_outcome: "degraded",
      last_success_at: null,
      current_task_id: null,
      on_deck_task_id: null,
      queue_count: 0,
      dispatchable_queue_count: 0,
      approval_gated_queue_count: 0,
      blocked_queue_count: 0,
      top_dispatchable_task_id: null,
      top_dispatchable_title: null,
      governed_dispatch_status: "idle",
      governed_current_task_id: null,
      governed_on_deck_task_id: null,
      current_task_threads: 0,
    },
    autonomous_queue_summary: {
      queue_count: 0,
      dispatchable_queue_count: 0,
      blocked_queue_count: 0,
      top_dispatchable_task_id: null,
      top_dispatchable_title: null,
      top_dispatchable_value_class: null,
      top_dispatchable_lane_family: null,
      governed_dispatch_claim: null,
    },
    governed_dispatch_state: null,
    lane_recommendations: [],
  };
}

export async function readGeneratedMasterAtlas(): Promise<Record<string, unknown> | null> {
  for (const candidate of candidatePaths()) {
    try {
      await access(candidate);
      const text = await readFile(candidate, "utf-8");
      return JSON.parse(text) as Record<string, unknown>;
    } catch {
      continue;
    }
  }

  return null;
}

export function pickMasterAtlasSummary(bundle: Record<string, unknown> | null) {
  if (!bundle || typeof bundle !== "object") {
    return null;
  }

  const summary = bundle.dashboard_summary;
  return summary && typeof summary === "object" ? (summary as MasterAtlasSummary) : null;
}

function pickGooseEvidenceSummary(bundle: Record<string, unknown>): GooseEvidenceSummary | null {
  const readinessFeed =
    bundle.capability_pilot_readiness &&
    typeof bundle.capability_pilot_readiness === "object" &&
    Array.isArray((bundle.capability_pilot_readiness as { records?: unknown[] }).records)
      ? ((bundle.capability_pilot_readiness as { records: Array<Record<string, unknown>> }).records ?? [])
      : [];
  const readinessRecord = readinessFeed.find(
    (record) => record.capability_id === "goose-operator-shell"
  );

  if (!readinessRecord) {
    return null;
  }

  const evalFeed =
    bundle.capability_pilot_evals &&
    typeof bundle.capability_pilot_evals === "object" &&
    Array.isArray((bundle.capability_pilot_evals as { records?: unknown[] }).records)
      ? ((bundle.capability_pilot_evals as { records: Array<Record<string, unknown>> }).records ?? [])
      : [];
  const evalRecord = evalFeed.find((record) => record.capability_id === "goose-operator-shell");

  const commandCheck = Array.isArray(readinessRecord.command_checks) ? readinessRecord.command_checks[0] : null;
  const adoptionFeed =
    bundle.capability_adoption_registry &&
    typeof bundle.capability_adoption_registry === "object" &&
    Array.isArray((bundle.capability_adoption_registry as { capabilities?: unknown[] }).capabilities)
      ? ((bundle.capability_adoption_registry as { capabilities: Array<Record<string, unknown>> }).capabilities ?? [])
      : Array.isArray((bundle.capability_adoption_registry as { records?: unknown[] }).records)
        ? ((bundle.capability_adoption_registry as { records: Array<Record<string, unknown>> }).records ?? [])
      : [];
  const adoptionRecord = adoptionFeed.find(
    (record) => record.capability_id === "goose-operator-shell" || record.id === "goose-operator-shell"
  );
  const operatorTestRecord =
    evalRecord?.operator_test_record && typeof evalRecord.operator_test_record === "object"
      ? (evalRecord.operator_test_record as Record<string, unknown>)
      : null;
  const operatorDetails =
    operatorTestRecord?.details && typeof operatorTestRecord.details === "object"
      ? (operatorTestRecord.details as Record<string, unknown>)
      : null;
  const evalSummary =
    readinessRecord.formal_eval_promptfoo_summary &&
    typeof readinessRecord.formal_eval_promptfoo_summary === "object"
      ? (readinessRecord.formal_eval_promptfoo_summary as Record<string, unknown>)
      : null;
  const gooseStage =
    typeof readinessRecord.capability_stage === "string"
      ? readinessRecord.capability_stage
      : typeof adoptionRecord?.capability_stage === "string"
        ? adoptionRecord.capability_stage
        : null;

  return {
    capability_id: "goose-operator-shell",
    goose_stage: gooseStage,
    label: typeof readinessRecord.label === "string" ? readinessRecord.label : "Goose Operator Shell",
    readiness_state:
      typeof readinessRecord.readiness_state === "string" ? readinessRecord.readiness_state : null,
    formal_eval_status:
      typeof readinessRecord.formal_eval_status === "string" ? readinessRecord.formal_eval_status : null,
    formal_eval_at:
      typeof readinessRecord.formal_eval_at === "string" ? readinessRecord.formal_eval_at : null,
    formal_eval_successes:
      typeof evalSummary?.successes === "number" ? evalSummary.successes : null,
    formal_eval_failures: typeof evalSummary?.failures === "number" ? evalSummary.failures : null,
    formal_eval_errors: typeof evalSummary?.errors === "number" ? evalSummary.errors : null,
    formal_eval_duration_ms: typeof evalSummary?.duration_ms === "number" ? evalSummary.duration_ms : null,
    operator_test_status:
      typeof evalRecord?.operator_test_status === "string" ? evalRecord.operator_test_status : null,
    request_surface_hint:
      typeof readinessRecord.request_surface_hint === "string" ? readinessRecord.request_surface_hint : null,
    next_action:
      gooseStage === "adopted"
        ? "Maintain adopted Goose shell truth."
        : typeof readinessRecord.next_action === "string"
          ? readinessRecord.next_action
          : null,
    next_formal_gate:
      gooseStage === "adopted"
        ? null
        : typeof readinessRecord.next_formal_gate === "string"
          ? readinessRecord.next_formal_gate
          : null,
    packet_path: typeof readinessRecord.packet_path === "string" ? readinessRecord.packet_path : null,
    packet_status:
      typeof adoptionRecord?.packet_status === "string"
        ? adoptionRecord.packet_status
        : typeof adoptionRecord?.stage === "string"
          ? adoptionRecord.stage
          : null,
    approval_state: typeof adoptionRecord?.approval_state === "string" ? adoptionRecord.approval_state : null,
    proof_state: typeof adoptionRecord?.proof_state === "string" ? adoptionRecord.proof_state : null,
    source_safe_remaining: Array.isArray(adoptionRecord?.source_safe_remaining)
      ? adoptionRecord.source_safe_remaining.filter((value): value is string => typeof value === "string")
      : [],
    approval_gated_remaining: Array.isArray(adoptionRecord?.approval_gated_remaining)
      ? adoptionRecord.approval_gated_remaining.filter((value): value is string => typeof value === "string")
      : [],
    command: typeof commandCheck?.command === "string" ? commandCheck.command : null,
    command_available_locally:
      typeof commandCheck?.available_locally === "boolean" ? commandCheck.available_locally : null,
    command_inventory_status:
      typeof commandCheck?.inventory_status === "string" ? commandCheck.inventory_status : null,
    command_inventory_version:
      typeof commandCheck?.inventory_version === "string" ? commandCheck.inventory_version : null,
    command_local_path: typeof commandCheck?.local_path === "string" ? commandCheck.local_path : null,
    wrapper_mode: typeof operatorDetails?.wrapper_mode === "string" ? operatorDetails.wrapper_mode : null,
  };
}

export function pickMasterAtlasRelationshipMap(
  bundle: Record<string, unknown> | null
): MasterAtlasRelationshipMap | null {
  if (!bundle || typeof bundle !== "object") {
    return null;
  }

  const summary = pickMasterAtlasSummary(bundle);
  const waveAdmissibility = Array.isArray(bundle.wave_admissibility)
    ? (bundle.wave_admissibility as Array<Record<string, unknown>>)
    : [];
  const capacityNodes =
    bundle.capacity_envelope_registry &&
    typeof bundle.capacity_envelope_registry === "object" &&
    Array.isArray((bundle.capacity_envelope_registry as { nodes?: unknown[] }).nodes)
      ? ((bundle.capacity_envelope_registry as { nodes: Array<Record<string, unknown>> }).nodes ?? [])
      : [];
  const dispatchLanes =
    bundle.economic_dispatch_ledger &&
    typeof bundle.economic_dispatch_ledger === "object" &&
    Array.isArray((bundle.economic_dispatch_ledger as { lanes?: unknown[] }).lanes)
      ? ((bundle.economic_dispatch_ledger as { lanes: Array<Record<string, unknown>> }).lanes ?? [])
      : [];
  const laneRecommendations = Array.isArray(bundle.lane_recommendations)
    ? (bundle.lane_recommendations as Array<Record<string, unknown>>)
    : [];
  const quotaPosture =
    bundle.routing_decisions_latest &&
    typeof bundle.routing_decisions_latest === "object" &&
    (bundle.routing_decisions_latest as { quota_posture?: unknown }).quota_posture &&
    typeof (bundle.routing_decisions_latest as { quota_posture?: unknown }).quota_posture === "object"
      ? ((bundle.routing_decisions_latest as { quota_posture: Record<string, unknown> }).quota_posture ?? null)
      : null;
  const routerShadowSummary =
    bundle.router_shadow_summary && typeof bundle.router_shadow_summary === "object"
      ? (bundle.router_shadow_summary as Record<string, unknown>)
      : null;
  const nextRequiredApproval =
    bundle.routing_decisions_latest &&
    typeof bundle.routing_decisions_latest === "object" &&
    (bundle.routing_decisions_latest as { next_required_approval?: unknown }).next_required_approval &&
    typeof (bundle.routing_decisions_latest as { next_required_approval?: unknown }).next_required_approval === "object"
      ? ((bundle.routing_decisions_latest as { next_required_approval: Record<string, unknown> }).next_required_approval ??
          null)
      : null;
  const safeSurfaceSummary =
    bundle.safe_surface_summary && typeof bundle.safe_surface_summary === "object"
      ? (bundle.safe_surface_summary as Record<string, unknown>)
      : null;
  const autonomousQueueSummary =
    bundle.autonomous_queue_summary && typeof bundle.autonomous_queue_summary === "object"
      ? (bundle.autonomous_queue_summary as Record<string, unknown>)
      : null;
  const governedDispatchState =
    bundle.governed_dispatch_state && typeof bundle.governed_dispatch_state === "object"
      ? (bundle.governed_dispatch_state as Record<string, unknown>)
      : null;
  const governedDispatchExecution =
    bundle.governed_dispatch_execution && typeof bundle.governed_dispatch_execution === "object"
      ? (bundle.governed_dispatch_execution as Record<string, unknown>)
      : governedDispatchState?.execution && typeof governedDispatchState.execution === "object"
        ? (governedDispatchState.execution as Record<string, unknown>)
        : null;
  const governedDispatchExecutionReportPath =
    typeof bundle.governed_dispatch_execution_report_path === "string"
      ? bundle.governed_dispatch_execution_report_path
      : typeof governedDispatchExecution?.report_path === "string"
        ? governedDispatchExecution.report_path
      : null;
  const gooseEvidenceSummary = pickGooseEvidenceSummary(bundle);

  return {
    generated_at: typeof bundle.generated_at === "string" ? bundle.generated_at : new Date().toISOString(),
    summary,
    turnover_readiness:
      bundle.turnover_readiness && typeof bundle.turnover_readiness === "object"
        ? {
            current_mode:
              typeof (bundle.turnover_readiness as Record<string, unknown>).current_mode === "string"
                ? ((bundle.turnover_readiness as Record<string, string>).current_mode ?? "unknown")
                : "unknown",
            target_mode:
              typeof (bundle.turnover_readiness as Record<string, unknown>).target_mode === "string"
                ? ((bundle.turnover_readiness as Record<string, string>).target_mode ?? "unknown")
                : "unknown",
            autonomous_turnover_status:
              typeof (bundle.turnover_readiness as Record<string, unknown>).autonomous_turnover_status === "string"
                ? ((bundle.turnover_readiness as Record<string, string>).autonomous_turnover_status ?? "unknown")
                : "unknown",
            autonomous_turnover_ready_now:
              typeof (bundle.turnover_readiness as Record<string, unknown>).autonomous_turnover_ready_now === "boolean"
                ? ((bundle.turnover_readiness as Record<string, boolean>).autonomous_turnover_ready_now ?? false)
                : false,
            next_gate:
              typeof (bundle.turnover_readiness as Record<string, unknown>).next_gate === "string"
                ? ((bundle.turnover_readiness as Record<string, string>).next_gate ?? null)
                : null,
            blocker_count:
              typeof (bundle.turnover_readiness as Record<string, unknown>).blocker_count === "number"
                ? ((bundle.turnover_readiness as Record<string, number>).blocker_count ?? 0)
                : 0,
            blockers: Array.isArray((bundle.turnover_readiness as Record<string, unknown>).blockers)
              ? (((bundle.turnover_readiness as Record<string, unknown>).blockers as unknown[]).filter(
                  (value): value is string => typeof value === "string"
                ))
              : [],
            required_before_turnover: Array.isArray((bundle.turnover_readiness as Record<string, unknown>).required_before_turnover)
              ? (((bundle.turnover_readiness as Record<string, unknown>).required_before_turnover as unknown[]).filter(
                  (value): value is string => typeof value === "string"
                ))
              : [],
            operator_answer:
              typeof (bundle.turnover_readiness as Record<string, unknown>).operator_answer === "string"
                ? ((bundle.turnover_readiness as Record<string, string>).operator_answer ?? "")
                : "",
            provider_gate_state:
              typeof (bundle.turnover_readiness as Record<string, unknown>).provider_gate_state === "string"
                ? ((bundle.turnover_readiness as Record<string, string>).provider_gate_state ?? null)
                : null,
            provider_elasticity_limited:
              typeof (bundle.turnover_readiness as Record<string, unknown>).provider_elasticity_limited === "boolean"
                ? ((bundle.turnover_readiness as Record<string, boolean>).provider_elasticity_limited ?? null)
                : null,
            provider_elasticity_blocking_provider_count:
              typeof (bundle.turnover_readiness as Record<string, unknown>).provider_elasticity_blocking_provider_count === "number"
                ? ((bundle.turnover_readiness as Record<string, number>).provider_elasticity_blocking_provider_count ?? null)
                : null,
            provider_elasticity_blocking_provider_ids: Array.isArray(
              (bundle.turnover_readiness as Record<string, unknown>).provider_elasticity_blocking_provider_ids,
            )
              ? (((bundle.turnover_readiness as Record<string, unknown>).provider_elasticity_blocking_provider_ids as unknown[]).filter(
                  (value): value is string => typeof value === "string",
                ))
              : [],
            self_acceleration_status:
              typeof (bundle.turnover_readiness as Record<string, unknown>).self_acceleration_status === "string"
                ? ((bundle.turnover_readiness as Record<string, string>).self_acceleration_status ?? null)
                : null,
            self_acceleration_ready_now:
              typeof (bundle.turnover_readiness as Record<string, unknown>).self_acceleration_ready_now === "boolean"
                ? ((bundle.turnover_readiness as Record<string, boolean>).self_acceleration_ready_now ?? null)
                : null,
            capacity_harvest_summary:
              (bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary &&
              typeof (bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary === "object"
                ? {
                    observed_at:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, unknown>).observed_at) === "string"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, string>).observed_at) ?? null)
                        : null,
                    sample_age_seconds:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, unknown>).sample_age_seconds) === "number"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, number>).sample_age_seconds) ?? null)
                        : null,
                    sample_posture:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, unknown>).sample_posture) === "string"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, string>).sample_posture) ?? null)
                        : null,
                    scheduler_queue_depth:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, unknown>).scheduler_queue_depth) === "number"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, number>).scheduler_queue_depth) ?? null)
                        : null,
                    scheduler_slot_count:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, unknown>).scheduler_slot_count) === "number"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, number>).scheduler_slot_count) ?? null)
                        : null,
                    harvestable_scheduler_slot_count:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, unknown>).harvestable_scheduler_slot_count) === "number"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, number>).harvestable_scheduler_slot_count) ?? null)
                        : null,
                    harvestable_zone_count:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, unknown>).harvestable_zone_count) === "number"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, number>).harvestable_zone_count) ?? null)
                        : null,
                    harvestable_zone_ids: Array.isArray(
                      ((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, unknown>).harvestable_zone_ids,
                    )
                      ? ((((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, unknown>).harvestable_zone_ids as unknown[]).filter(
                          (value): value is string => typeof value === "string",
                        ))
                      : [],
                    provisional_harvest_candidate_count:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, unknown>).provisional_harvest_candidate_count) === "number"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, number>).provisional_harvest_candidate_count) ?? null)
                        : null,
                    protected_reserve_slot_count:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, unknown>).protected_reserve_slot_count) === "number"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, number>).protected_reserve_slot_count) ?? null)
                        : null,
                    admission_state:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, unknown>).admission_state) === "string"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, string>).admission_state) ?? null)
                        : null,
                    ready_for_harvest_now:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, unknown>).ready_for_harvest_now) === "boolean"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).capacity_harvest_summary as Record<string, boolean>).ready_for_harvest_now) ?? null)
                        : null,
                  }
                : null,
            work_economy_status:
              typeof (bundle.turnover_readiness as Record<string, unknown>).work_economy_status === "string"
                ? ((bundle.turnover_readiness as Record<string, string>).work_economy_status ?? null)
                : null,
            work_economy_ready_now:
              typeof (bundle.turnover_readiness as Record<string, unknown>).work_economy_ready_now === "boolean"
                ? ((bundle.turnover_readiness as Record<string, boolean>).work_economy_ready_now ?? null)
                : null,
            work_economy_blocked_burn_class_ids: Array.isArray(
              (bundle.turnover_readiness as Record<string, unknown>).work_economy_blocked_burn_class_ids,
            )
              ? (((bundle.turnover_readiness as Record<string, unknown>).work_economy_blocked_burn_class_ids as unknown[]).filter(
                  (value): value is string => typeof value === "string",
                ))
              : [],
            work_economy_degraded_burn_class_ids: Array.isArray(
              (bundle.turnover_readiness as Record<string, unknown>).work_economy_degraded_burn_class_ids,
            )
              ? (((bundle.turnover_readiness as Record<string, unknown>).work_economy_degraded_burn_class_ids as unknown[]).filter(
                  (value): value is string => typeof value === "string",
                ))
              : [],
            burn_dispatch_phase:
              typeof (bundle.turnover_readiness as Record<string, unknown>).burn_dispatch_phase === "number"
                ? ((bundle.turnover_readiness as Record<string, number>).burn_dispatch_phase ?? null)
                : null,
            burn_dispatch_phase_label:
              typeof (bundle.turnover_readiness as Record<string, unknown>).burn_dispatch_phase_label === "string"
                ? ((bundle.turnover_readiness as Record<string, string>).burn_dispatch_phase_label ?? null)
                : null,
            dispatchable_safe_surface_queue_count:
              typeof (bundle.turnover_readiness as Record<string, unknown>).dispatchable_safe_surface_queue_count === "number"
                ? ((bundle.turnover_readiness as Record<string, number>).dispatchable_safe_surface_queue_count ?? null)
                : null,
            autonomous_queue_count:
              typeof (bundle.turnover_readiness as Record<string, unknown>).autonomous_queue_count === "number"
                ? ((bundle.turnover_readiness as Record<string, number>).autonomous_queue_count ?? null)
                : null,
            dispatchable_autonomous_queue_count:
              typeof (bundle.turnover_readiness as Record<string, unknown>).dispatchable_autonomous_queue_count === "number"
                ? ((bundle.turnover_readiness as Record<string, number>).dispatchable_autonomous_queue_count ?? null)
                : null,
            top_dispatchable_autonomous_task_id:
              typeof (bundle.turnover_readiness as Record<string, unknown>).top_dispatchable_autonomous_task_id === "string"
                ? ((bundle.turnover_readiness as Record<string, string>).top_dispatchable_autonomous_task_id ?? null)
                : null,
            top_dispatchable_autonomous_task_title:
              typeof (bundle.turnover_readiness as Record<string, unknown>).top_dispatchable_autonomous_task_title === "string"
                ? ((bundle.turnover_readiness as Record<string, string>).top_dispatchable_autonomous_task_title ?? null)
                : null,
            checkpoint_slice_summary:
              (bundle.turnover_readiness as Record<string, unknown>).checkpoint_slice_summary &&
              typeof (bundle.turnover_readiness as Record<string, unknown>).checkpoint_slice_summary === "object"
                ? {
                    sequence_id:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).checkpoint_slice_summary as Record<string, unknown>).sequence_id) === "string"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).checkpoint_slice_summary as Record<string, string>).sequence_id) ?? null)
                        : null,
                    total:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).checkpoint_slice_summary as Record<string, unknown>).total) === "number"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).checkpoint_slice_summary as Record<string, number>).total) ?? null)
                        : null,
                    ready_for_checkpoint:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).checkpoint_slice_summary as Record<string, unknown>).ready_for_checkpoint) === "number"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).checkpoint_slice_summary as Record<string, number>).ready_for_checkpoint) ?? null)
                        : null,
                    active:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).checkpoint_slice_summary as Record<string, unknown>).active) === "number"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).checkpoint_slice_summary as Record<string, number>).active) ?? null)
                        : null,
                        approval_gated:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).checkpoint_slice_summary as Record<string, unknown>).approval_gated) === "number"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).checkpoint_slice_summary as Record<string, number>).approval_gated) ?? null)
                        : null,
                    published:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).checkpoint_slice_summary as Record<string, unknown>).published) === "number"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).checkpoint_slice_summary as Record<string, number>).published) ?? null)
                        : null,
                  }
                : null,
            next_checkpoint_slice:
              (bundle.turnover_readiness as Record<string, unknown>).next_checkpoint_slice &&
              typeof (bundle.turnover_readiness as Record<string, unknown>).next_checkpoint_slice === "object"
                ? {
                    id:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).next_checkpoint_slice as Record<string, unknown>).id) === "string"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).next_checkpoint_slice as Record<string, string>).id) ?? null)
                        : null,
                    title:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).next_checkpoint_slice as Record<string, unknown>).title) === "string"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).next_checkpoint_slice as Record<string, string>).title) ?? null)
                        : null,
                    order:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).next_checkpoint_slice as Record<string, unknown>).order) === "number"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).next_checkpoint_slice as Record<string, number>).order) ?? null)
                        : null,
                    status:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).next_checkpoint_slice as Record<string, unknown>).status) === "string"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).next_checkpoint_slice as Record<string, string>).status) ?? null)
                        : null,
                    blocking_gate:
                      typeof (((bundle.turnover_readiness as Record<string, unknown>).next_checkpoint_slice as Record<string, unknown>).blocking_gate) === "string"
                        ? ((((bundle.turnover_readiness as Record<string, unknown>).next_checkpoint_slice as Record<string, string>).blocking_gate) ?? null)
                        : null,
                    owner_workstreams: Array.isArray(((bundle.turnover_readiness as Record<string, unknown>).next_checkpoint_slice as Record<string, unknown>).owner_workstreams)
                      ? ((((bundle.turnover_readiness as Record<string, unknown>).next_checkpoint_slice as Record<string, unknown>).owner_workstreams as unknown[]).filter(
                          (value): value is string => typeof value === "string"
                        ))
                      : [],
                  }
                : null,
          }
        : null,
    authority_surfaces: [
      {
        id: "athanor",
        label: "Athanor",
        authority_class: "adopted_system",
        root: "C:/Athanor",
        role: "Canonical adopted-system and runtime-governance truth.",
        front_door: "/operator",
      },
      {
        id: "devstack",
        label: "Devstack",
        authority_class: "build_system",
        root: "C:/athanor-devstack",
        role: "Capability forge, proof system, and packet-drafting lane.",
        front_door: "/topology",
      },
      {
        id: "codex-home",
        label: "Codex Home",
        authority_class: "operator_local",
        root: "C:/Users/Shaun/.codex",
        role: "Operator-local control, doctrine, safe-surface routing, and inbox-facing coordination.",
        front_door: "/governor",
      },
      {
        id: "lineage-archive",
        label: "Lineage / Archive",
        authority_class: "archive_evidence",
        root: "C:/Users/Shaun/dev/athanor-next",
        role: "Lineage and archived evidence that informs but never outranks current truth.",
        front_door: "/catalog",
      },
    ],
    promotion_flow: {
      source_label: "Devstack proof lanes",
      packet_ready_count: summary?.packet_ready_count ?? 0,
      next_promotion_candidate: summary?.best_next_promotion_candidate ?? null,
      target_label: "Athanor adopted truth",
      governance_posture: summary?.governance_posture ?? null,
    },
    blocked_packets: waveAdmissibility
      .filter((item) => Array.isArray(item.blocked_by) && item.blocked_by.length > 0)
      .slice(0, 5)
      .map((item) => ({
        packet_id: typeof item.packet_id === "string" ? item.packet_id : "unknown",
        capability_id: typeof item.capability_id === "string" ? item.capability_id : "unknown",
        blocked_by: Array.isArray(item.blocked_by) ? item.blocked_by.filter((value): value is string => typeof value === "string") : [],
        runtime_target: typeof item.runtime_target === "string" ? item.runtime_target : "unknown",
      })),
    node_capacity: capacityNodes.map((item) => ({
      node_id: typeof item.node_id === "string" ? item.node_id : "unknown",
      node_role: typeof item.node_role === "string" ? item.node_role : "unknown",
      gpu_count: Array.isArray(item.gpus) ? item.gpus.length : 0,
      interactive_reserve_gpu_slots: typeof item.interactive_reserve_gpu_slots === "number" ? item.interactive_reserve_gpu_slots : 0,
      background_fill_gpu_slots: typeof item.background_fill_gpu_slots === "number" ? item.background_fill_gpu_slots : 0,
      utilization_targets:
        item.utilization_targets && typeof item.utilization_targets === "object"
          ? {
              interactive_reserve_floor_gpu_slots:
                typeof (item.utilization_targets as Record<string, unknown>).interactive_reserve_floor_gpu_slots === "number"
                  ? ((item.utilization_targets as Record<string, number>).interactive_reserve_floor_gpu_slots ?? 0)
                  : 0,
              background_harvest_target_gpu_slots:
                typeof (item.utilization_targets as Record<string, unknown>).background_harvest_target_gpu_slots === "number"
                  ? ((item.utilization_targets as Record<string, number>).background_harvest_target_gpu_slots ?? 0)
                  : 0,
              max_noncritical_preemptible_gpu_slots:
                typeof (item.utilization_targets as Record<string, unknown>).max_noncritical_preemptible_gpu_slots === "number"
                  ? ((item.utilization_targets as Record<string, number>).max_noncritical_preemptible_gpu_slots ?? 0)
                  : 0,
            }
          : null,
    })),
    dispatch_lanes: dispatchLanes.slice(0, 6).map((item) => ({
      lane_id: typeof item.lane_id === "string" ? item.lane_id : "unknown",
      provider_id: typeof item.provider_id === "string" ? item.provider_id : "unknown",
      reserve_class: typeof item.reserve_class === "string" ? item.reserve_class : "unknown",
      max_parallel_slots: typeof item.max_parallel_slots === "number" ? item.max_parallel_slots : 0,
      reserved_parallel_slots: typeof item.reserved_parallel_slots === "number" ? item.reserved_parallel_slots : 0,
      harvestable_parallel_slots: typeof item.harvestable_parallel_slots === "number" ? item.harvestable_parallel_slots : 0,
      selection_reason:
        Array.isArray(item.selection_reasons) && typeof item.selection_reasons[0] === "string"
          ? item.selection_reasons[0]
          : null,
    })),
    quota_posture: quotaPosture
      ? {
          quota_posture:
            typeof quotaPosture.quota_posture === "string" ? ((quotaPosture.quota_posture as string) ?? "unknown") : "unknown",
          respect_vendor_policy_before_harvest: Boolean(quotaPosture.respect_vendor_policy_before_harvest),
          other_metered_disabled_for_auto_harvest_by_default: Boolean(
            quotaPosture.other_metered_disabled_for_auto_harvest_by_default
          ),
          record_count: typeof quotaPosture.record_count === "number" ? quotaPosture.record_count : 0,
          degraded_record_count:
            typeof quotaPosture.degraded_record_count === "number" ? quotaPosture.degraded_record_count : 0,
          low_confidence_record_count:
            typeof quotaPosture.low_confidence_record_count === "number" ? quotaPosture.low_confidence_record_count : 0,
          degraded_records: Array.isArray(quotaPosture.degraded_records)
            ? (quotaPosture.degraded_records.filter(
                (value): value is { family_id: string; degraded_reason: string } =>
                  Boolean(value) &&
                  typeof value === "object" &&
                  typeof (value as { family_id?: unknown }).family_id === "string" &&
                  typeof (value as { degraded_reason?: unknown }).degraded_reason === "string"
              ))
            : [],
          local_compute_capacity:
            quotaPosture.local_compute_capacity && typeof quotaPosture.local_compute_capacity === "object"
              ? {
                  remaining_units:
                    typeof (quotaPosture.local_compute_capacity as Record<string, unknown>).remaining_units === "number"
                      ? ((quotaPosture.local_compute_capacity as Record<string, number>).remaining_units ?? 0)
                      : 0,
                  sample_posture:
                    typeof (quotaPosture.local_compute_capacity as Record<string, unknown>).sample_posture === "string"
                      ? ((quotaPosture.local_compute_capacity as Record<string, string>).sample_posture ?? "unknown")
                      : "unknown",
                  scheduler_queue_depth:
                    typeof (quotaPosture.local_compute_capacity as Record<string, unknown>).scheduler_queue_depth ===
                    "number"
                      ? ((quotaPosture.local_compute_capacity as Record<string, number>).scheduler_queue_depth ?? 0)
                      : 0,
                  scheduler_slot_count:
                    typeof (quotaPosture.local_compute_capacity as Record<string, unknown>).scheduler_slot_count ===
                    "number"
                      ? ((quotaPosture.local_compute_capacity as Record<string, number>).scheduler_slot_count ?? 0)
                      : 0,
                  harvestable_scheduler_slot_count:
                    typeof (quotaPosture.local_compute_capacity as Record<string, unknown>)
                      .harvestable_scheduler_slot_count === "number"
                      ? ((quotaPosture.local_compute_capacity as Record<string, number>)
                          .harvestable_scheduler_slot_count ?? 0)
                      : 0,
                  harvestable_by_zone:
                    (quotaPosture.local_compute_capacity as Record<string, unknown>).harvestable_by_zone &&
                    typeof (quotaPosture.local_compute_capacity as Record<string, unknown>).harvestable_by_zone ===
                      "object"
                      ? Object.fromEntries(
                          Object.entries(
                            (quotaPosture.local_compute_capacity as { harvestable_by_zone: Record<string, unknown> })
                              .harvestable_by_zone ?? {}
                          ).filter((entry): entry is [string, number] => typeof entry[0] === "string" && typeof entry[1] === "number")
                        )
                      : {},
                  harvestable_by_slot:
                    (quotaPosture.local_compute_capacity as Record<string, unknown>).harvestable_by_slot &&
                    typeof (quotaPosture.local_compute_capacity as Record<string, unknown>).harvestable_by_slot ===
                      "object"
                      ? Object.fromEntries(
                          Object.entries(
                            (quotaPosture.local_compute_capacity as { harvestable_by_slot: Record<string, unknown> })
                              .harvestable_by_slot ?? {}
                          ).filter((entry): entry is [string, number] => typeof entry[0] === "string" && typeof entry[1] === "number")
                        )
                      : {},
                  provisional_harvest_candidate_count:
                    typeof (quotaPosture.local_compute_capacity as Record<string, unknown>)
                      .provisional_harvest_candidate_count === "number"
                      ? ((quotaPosture.local_compute_capacity as Record<string, number>)
                          .provisional_harvest_candidate_count ?? 0)
                      : 0,
                  provisional_harvestable_by_node:
                    (quotaPosture.local_compute_capacity as Record<string, unknown>).provisional_harvestable_by_node &&
                    typeof (quotaPosture.local_compute_capacity as Record<string, unknown>).provisional_harvestable_by_node ===
                      "object"
                      ? Object.fromEntries(
                          Object.entries(
                            (quotaPosture.local_compute_capacity as {
                              provisional_harvestable_by_node: Record<string, unknown>;
                            }).provisional_harvestable_by_node ?? {}
                          ).filter((entry): entry is [string, number] => typeof entry[0] === "string" && typeof entry[1] === "number")
                        )
                      : {},
                  open_harvest_slot_ids: Array.isArray(
                    (quotaPosture.local_compute_capacity as Record<string, unknown>).open_harvest_slot_ids
                  )
                    ? (
                        (quotaPosture.local_compute_capacity as { open_harvest_slot_ids: unknown[] })
                          .open_harvest_slot_ids ?? []
                      ).filter((value): value is string => typeof value === "string")
                    : [],
                  open_harvest_slot_target_ids: Array.isArray(
                    (quotaPosture.local_compute_capacity as Record<string, unknown>).open_harvest_slot_target_ids
                  )
                    ? (
                        (quotaPosture.local_compute_capacity as { open_harvest_slot_target_ids: unknown[] })
                          .open_harvest_slot_target_ids ?? []
                      ).filter((value): value is string => typeof value === "string")
                    : [],
                  scheduler_conflict_gpu_count:
                    typeof (quotaPosture.local_compute_capacity as Record<string, unknown>)
                      .scheduler_conflict_gpu_count === "number"
                      ? ((quotaPosture.local_compute_capacity as Record<string, number>).scheduler_conflict_gpu_count ??
                          0)
                      : 0,
                }
              : null,
        }
      : null,
    router_shadow_summary: routerShadowSummary
      ? {
          phase: typeof routerShadowSummary.phase === "number" ? routerShadowSummary.phase : 0,
          phase_label: typeof routerShadowSummary.phase_label === "string" ? routerShadowSummary.phase_label : "unknown",
          shadow_disagreement_rate:
            typeof routerShadowSummary.shadow_disagreement_rate === "number"
              ? routerShadowSummary.shadow_disagreement_rate
              : 0,
          routing_proof_total:
            typeof routerShadowSummary.routing_proof_total === "number" ? routerShadowSummary.routing_proof_total : 0,
          routing_proof_failed:
            typeof routerShadowSummary.routing_proof_failed === "number" ? routerShadowSummary.routing_proof_failed : 0,
          ready_for_phase_1: Boolean(routerShadowSummary.ready_for_phase_1),
          ready_for_phase_2: Boolean(routerShadowSummary.ready_for_phase_2),
        }
      : null,
    next_required_approval: nextRequiredApproval
      ? {
          approval_class:
            typeof nextRequiredApproval.approval_class === "string" ? nextRequiredApproval.approval_class : "unknown",
          label: typeof nextRequiredApproval.label === "string" ? nextRequiredApproval.label : "unknown",
          reason: typeof nextRequiredApproval.reason === "string" ? nextRequiredApproval.reason : "",
          allowed_actions: Array.isArray(nextRequiredApproval.allowed_actions)
            ? nextRequiredApproval.allowed_actions.filter((value): value is string => typeof value === "string")
            : [],
        }
      : null,
    safe_surface_summary: safeSurfaceSummary
      ? {
          last_outcome: typeof safeSurfaceSummary.last_outcome === "string" ? safeSurfaceSummary.last_outcome : null,
          last_success_at:
            typeof safeSurfaceSummary.last_success_at === "string" ? safeSurfaceSummary.last_success_at : null,
          current_task_id:
            typeof safeSurfaceSummary.current_task_id === "string" ? safeSurfaceSummary.current_task_id : null,
          on_deck_task_id:
            typeof safeSurfaceSummary.on_deck_task_id === "string" ? safeSurfaceSummary.on_deck_task_id : null,
          queue_count: typeof safeSurfaceSummary.queue_count === "number" ? safeSurfaceSummary.queue_count : 0,
          dispatchable_queue_count:
            typeof safeSurfaceSummary.dispatchable_queue_count === "number" ? safeSurfaceSummary.dispatchable_queue_count : 0,
          approval_gated_queue_count:
            typeof safeSurfaceSummary.approval_gated_queue_count === "number" ? safeSurfaceSummary.approval_gated_queue_count : 0,
          blocked_queue_count:
            typeof safeSurfaceSummary.blocked_queue_count === "number" ? safeSurfaceSummary.blocked_queue_count : 0,
          top_dispatchable_task_id:
            typeof safeSurfaceSummary.top_dispatchable_task_id === "string" ? safeSurfaceSummary.top_dispatchable_task_id : null,
          top_dispatchable_title:
            typeof safeSurfaceSummary.top_dispatchable_title === "string" ? safeSurfaceSummary.top_dispatchable_title : null,
          governed_dispatch_status:
            typeof safeSurfaceSummary.governed_dispatch_status === "string"
              ? safeSurfaceSummary.governed_dispatch_status
              : "idle",
          governed_current_task_id:
            typeof safeSurfaceSummary.governed_current_task_id === "string"
              ? safeSurfaceSummary.governed_current_task_id
              : null,
          governed_on_deck_task_id:
            typeof safeSurfaceSummary.governed_on_deck_task_id === "string"
              ? safeSurfaceSummary.governed_on_deck_task_id
              : null,
          current_task_threads:
            typeof safeSurfaceSummary.current_task_threads === "number" ? safeSurfaceSummary.current_task_threads : 0,
        }
      : null,
    goose_evidence_summary: gooseEvidenceSummary,
    governed_dispatch_execution: governedDispatchExecution
      ? {
          generated_at:
            typeof governedDispatchExecution.generated_at === "string" ? governedDispatchExecution.generated_at : null,
          source_of_truth:
            typeof governedDispatchExecution.source_of_truth === "string"
              ? governedDispatchExecution.source_of_truth
              : null,
          report_path:
            typeof governedDispatchExecution.report_path === "string" ? governedDispatchExecution.report_path : null,
          status: typeof governedDispatchExecution.status === "string" ? governedDispatchExecution.status : null,
          dispatch_outcome:
            typeof governedDispatchExecution.dispatch_outcome === "string"
              ? governedDispatchExecution.dispatch_outcome
              : null,
          claim_id: typeof governedDispatchExecution.claim_id === "string" ? governedDispatchExecution.claim_id : null,
          current_task_id:
            typeof governedDispatchExecution.current_task_id === "string"
              ? governedDispatchExecution.current_task_id
              : null,
          current_task_title:
            typeof governedDispatchExecution.current_task_title === "string"
              ? governedDispatchExecution.current_task_title
              : null,
          agent_server_base_url:
            typeof governedDispatchExecution.agent_server_base_url === "string"
              ? governedDispatchExecution.agent_server_base_url
              : null,
          backlog_id:
            typeof governedDispatchExecution.backlog_id === "string" ? governedDispatchExecution.backlog_id : null,
          backlog_status:
            typeof governedDispatchExecution.backlog_status === "string"
              ? governedDispatchExecution.backlog_status
              : null,
          dispatch_path:
            typeof governedDispatchExecution.dispatch_path === "string"
              ? governedDispatchExecution.dispatch_path
              : null,
          dispatch_status_code:
            typeof governedDispatchExecution.dispatch_status_code === "number"
              ? governedDispatchExecution.dispatch_status_code
              : null,
          governor_level:
            typeof governedDispatchExecution.governor_level === "string"
              ? governedDispatchExecution.governor_level
              : null,
          governor_reason:
            typeof governedDispatchExecution.governor_reason === "string"
              ? governedDispatchExecution.governor_reason
              : null,
          error: typeof governedDispatchExecution.error === "string" ? governedDispatchExecution.error : null,
          task_id: typeof governedDispatchExecution.task_id === "string" ? governedDispatchExecution.task_id : null,
          task_status:
            typeof governedDispatchExecution.task_status === "string"
              ? governedDispatchExecution.task_status
              : null,
          task_source:
            typeof governedDispatchExecution.task_source === "string"
              ? governedDispatchExecution.task_source
              : null,
          retry_of_task_id:
            typeof governedDispatchExecution.retry_of_task_id === "string"
              ? governedDispatchExecution.retry_of_task_id
              : null,
          retry_count:
            typeof governedDispatchExecution.retry_count === "number"
              ? governedDispatchExecution.retry_count
              : null,
          retry_lineage_depth:
            typeof governedDispatchExecution.retry_lineage_depth === "number"
              ? governedDispatchExecution.retry_lineage_depth
              : null,
          recovery_event:
            typeof governedDispatchExecution.recovery_event === "string"
              ? governedDispatchExecution.recovery_event
              : null,
          recovery_reason:
            typeof governedDispatchExecution.recovery_reason === "string"
              ? governedDispatchExecution.recovery_reason
              : null,
          resilience_state:
            typeof governedDispatchExecution.resilience_state === "string"
              ? governedDispatchExecution.resilience_state
              : null,
          advisory_blockers: Array.isArray(governedDispatchExecution.advisory_blockers)
            ? governedDispatchExecution.advisory_blockers.filter(
                (item): item is string => typeof item === "string" && item.length > 0
              )
            : [],
        }
      : null,
    governed_dispatch_execution_report_path: governedDispatchExecutionReportPath,
    autonomous_queue_summary: autonomousQueueSummary
      ? (() => {
          const governedDispatchClaim =
            autonomousQueueSummary.governed_dispatch_claim &&
            typeof autonomousQueueSummary.governed_dispatch_claim === "object"
              ? (autonomousQueueSummary.governed_dispatch_claim as Record<string, unknown>)
              : null;

          return {
          queue_count: typeof autonomousQueueSummary.queue_count === "number" ? autonomousQueueSummary.queue_count : 0,
          dispatchable_queue_count:
            typeof autonomousQueueSummary.dispatchable_queue_count === "number"
              ? autonomousQueueSummary.dispatchable_queue_count
              : 0,
          blocked_queue_count:
            typeof autonomousQueueSummary.blocked_queue_count === "number"
              ? autonomousQueueSummary.blocked_queue_count
              : 0,
          top_dispatchable_task_id:
            typeof autonomousQueueSummary.top_dispatchable_task_id === "string"
              ? autonomousQueueSummary.top_dispatchable_task_id
              : null,
          top_dispatchable_title:
            typeof autonomousQueueSummary.top_dispatchable_title === "string"
              ? autonomousQueueSummary.top_dispatchable_title
              : null,
          top_dispatchable_value_class:
            typeof autonomousQueueSummary.top_dispatchable_value_class === "string"
              ? autonomousQueueSummary.top_dispatchable_value_class
              : null,
          top_dispatchable_lane_family:
            typeof autonomousQueueSummary.top_dispatchable_lane_family === "string"
              ? autonomousQueueSummary.top_dispatchable_lane_family
              : null,
          governed_dispatch_claim: governedDispatchClaim
            ? {
                status: typeof governedDispatchClaim.status === "string" ? governedDispatchClaim.status : null,
                current_task_id:
                  typeof governedDispatchClaim.current_task_id === "string" ? governedDispatchClaim.current_task_id : null,
                current_task_title:
                  typeof governedDispatchClaim.current_task_title === "string"
                    ? governedDispatchClaim.current_task_title
                    : null,
                on_deck_task_id:
                  typeof governedDispatchClaim.on_deck_task_id === "string" ? governedDispatchClaim.on_deck_task_id : null,
                on_deck_task_title:
                  typeof governedDispatchClaim.on_deck_task_title === "string"
                    ? governedDispatchClaim.on_deck_task_title
                    : null,
                preferred_lane_family:
                  typeof governedDispatchClaim.preferred_lane_family === "string"
                    ? governedDispatchClaim.preferred_lane_family
                    : null,
                approved_mutation_class:
                  typeof governedDispatchClaim.approved_mutation_class === "string"
                    ? governedDispatchClaim.approved_mutation_class
                    : null,
                approved_mutation_label:
                  typeof governedDispatchClaim.approved_mutation_label === "string"
                    ? governedDispatchClaim.approved_mutation_label
                    : null,
                proof_command_or_eval_surface:
                  typeof governedDispatchClaim.proof_command_or_eval_surface === "string"
                    ? governedDispatchClaim.proof_command_or_eval_surface
                    : null,
              }
            : null,
        };
        })()
      : null,
    governed_dispatch_state: governedDispatchState
      ? {
          materialization:
            governedDispatchState.materialization &&
            typeof governedDispatchState.materialization === "object"
              ? {
                  status:
                    typeof (governedDispatchState.materialization as Record<string, unknown>).status === "string"
                      ? ((governedDispatchState.materialization as Record<string, string>).status ?? null)
                      : null,
                  backlog_id:
                    typeof (governedDispatchState.materialization as Record<string, unknown>).backlog_id === "string"
                      ? ((governedDispatchState.materialization as Record<string, string>).backlog_id ?? null)
                      : null,
                  backlog_status:
                    typeof (governedDispatchState.materialization as Record<string, unknown>).backlog_status === "string"
                      ? ((governedDispatchState.materialization as Record<string, string>).backlog_status ?? null)
                      : null,
                  report_path:
                    typeof (governedDispatchState.materialization as Record<string, unknown>).report_path === "string"
                      ? ((governedDispatchState.materialization as Record<string, string>).report_path ?? null)
                      : null,
                  error:
                    typeof (governedDispatchState.materialization as Record<string, unknown>).error === "string"
                      ? ((governedDispatchState.materialization as Record<string, string>).error ?? null)
                      : null,
                }
              : null,
          status: typeof governedDispatchState.status === "string" ? governedDispatchState.status : null,
          dispatch_outcome:
            typeof governedDispatchState.dispatch_outcome === "string" ? governedDispatchState.dispatch_outcome : null,
          claim_id: typeof governedDispatchState.claim_id === "string" ? governedDispatchState.claim_id : null,
          current_task_id:
            typeof governedDispatchState.current_task_id === "string" ? governedDispatchState.current_task_id : null,
          current_task_title:
            typeof governedDispatchState.current_task_title === "string"
              ? governedDispatchState.current_task_title
              : null,
          on_deck_task_id:
            typeof governedDispatchState.on_deck_task_id === "string" ? governedDispatchState.on_deck_task_id : null,
          on_deck_task_title:
            typeof governedDispatchState.on_deck_task_title === "string"
              ? governedDispatchState.on_deck_task_title
              : null,
          preferred_lane_family:
            typeof governedDispatchState.preferred_lane_family === "string"
              ? governedDispatchState.preferred_lane_family
              : null,
          approved_mutation_label:
            typeof governedDispatchState.approved_mutation_label === "string"
              ? governedDispatchState.approved_mutation_label
              : null,
          proof_command_or_eval_surface:
            typeof governedDispatchState.proof_command_or_eval_surface === "string"
              ? governedDispatchState.proof_command_or_eval_surface
              : null,
          queue_count: typeof governedDispatchState.queue_count === "number" ? governedDispatchState.queue_count : 0,
          dispatchable_queue_count:
            typeof governedDispatchState.dispatchable_queue_count === "number"
              ? governedDispatchState.dispatchable_queue_count
              : 0,
          blocked_queue_count:
            typeof governedDispatchState.blocked_queue_count === "number"
              ? governedDispatchState.blocked_queue_count
              : 0,
          safe_surface_queue_count:
            typeof governedDispatchState.safe_surface_queue_count === "number"
              ? governedDispatchState.safe_surface_queue_count
              : 0,
          safe_surface_dispatchable_queue_count:
            typeof governedDispatchState.safe_surface_dispatchable_queue_count === "number"
              ? governedDispatchState.safe_surface_dispatchable_queue_count
              : 0,
          recent_dispatch_outcome_count:
            typeof governedDispatchState.recent_dispatch_outcome_count === "number"
              ? governedDispatchState.recent_dispatch_outcome_count
              : 0,
          provider_gate_state:
            typeof governedDispatchState.provider_gate_state === "string"
              ? governedDispatchState.provider_gate_state
              : null,
          work_economy_status:
            typeof governedDispatchState.work_economy_status === "string"
              ? governedDispatchState.work_economy_status
              : null,
          report_path: typeof governedDispatchState.report_path === "string" ? governedDispatchState.report_path : null,
          execution: governedDispatchExecution
            ? {
                generated_at:
                  typeof governedDispatchExecution.generated_at === "string"
                    ? governedDispatchExecution.generated_at
                    : null,
                source_of_truth:
                  typeof governedDispatchExecution.source_of_truth === "string"
                    ? governedDispatchExecution.source_of_truth
                    : null,
                report_path:
                  typeof governedDispatchExecution.report_path === "string"
                    ? governedDispatchExecution.report_path
                    : null,
                status: typeof governedDispatchExecution.status === "string" ? governedDispatchExecution.status : null,
                dispatch_outcome:
                  typeof governedDispatchExecution.dispatch_outcome === "string"
                    ? governedDispatchExecution.dispatch_outcome
                    : null,
                claim_id:
                  typeof governedDispatchExecution.claim_id === "string"
                    ? governedDispatchExecution.claim_id
                    : null,
                current_task_id:
                  typeof governedDispatchExecution.current_task_id === "string"
                    ? governedDispatchExecution.current_task_id
                    : null,
                current_task_title:
                  typeof governedDispatchExecution.current_task_title === "string"
                    ? governedDispatchExecution.current_task_title
                    : null,
                agent_server_base_url:
                  typeof governedDispatchExecution.agent_server_base_url === "string"
                    ? governedDispatchExecution.agent_server_base_url
                    : null,
                backlog_id:
                  typeof governedDispatchExecution.backlog_id === "string"
                    ? governedDispatchExecution.backlog_id
                    : null,
                backlog_status:
                  typeof governedDispatchExecution.backlog_status === "string"
                    ? governedDispatchExecution.backlog_status
                    : null,
                dispatch_path:
                  typeof governedDispatchExecution.dispatch_path === "string"
                    ? governedDispatchExecution.dispatch_path
                    : null,
                dispatch_status_code:
                  typeof governedDispatchExecution.dispatch_status_code === "number"
                    ? governedDispatchExecution.dispatch_status_code
                    : null,
                governor_level:
                  typeof governedDispatchExecution.governor_level === "string"
                    ? governedDispatchExecution.governor_level
                    : null,
                governor_reason:
                  typeof governedDispatchExecution.governor_reason === "string"
                    ? governedDispatchExecution.governor_reason
                    : null,
                error: typeof governedDispatchExecution.error === "string" ? governedDispatchExecution.error : null,
                task_id:
                  typeof governedDispatchExecution.task_id === "string"
                    ? governedDispatchExecution.task_id
                    : null,
                task_status:
                  typeof governedDispatchExecution.task_status === "string"
                    ? governedDispatchExecution.task_status
                    : null,
                task_source:
                  typeof governedDispatchExecution.task_source === "string"
                    ? governedDispatchExecution.task_source
                    : null,
                retry_of_task_id:
                  typeof governedDispatchExecution.retry_of_task_id === "string"
                    ? governedDispatchExecution.retry_of_task_id
                    : null,
                retry_count:
                  typeof governedDispatchExecution.retry_count === "number"
                    ? governedDispatchExecution.retry_count
                    : null,
                retry_lineage_depth:
                  typeof governedDispatchExecution.retry_lineage_depth === "number"
                    ? governedDispatchExecution.retry_lineage_depth
                    : null,
                recovery_event:
                  typeof governedDispatchExecution.recovery_event === "string"
                    ? governedDispatchExecution.recovery_event
                    : null,
                recovery_reason:
                  typeof governedDispatchExecution.recovery_reason === "string"
                    ? governedDispatchExecution.recovery_reason
                    : null,
                resilience_state:
                  typeof governedDispatchExecution.resilience_state === "string"
                    ? governedDispatchExecution.resilience_state
                    : null,
                advisory_blockers: Array.isArray(governedDispatchExecution.advisory_blockers)
                  ? governedDispatchExecution.advisory_blockers.filter(
                      (item): item is string => typeof item === "string" && item.length > 0
                    )
                  : [],
              }
            : null,
        }
      : null,
    lane_recommendations: laneRecommendations.slice(0, 6).map((item) => ({
      task_class: typeof item.task_class === "string" ? item.task_class : "unknown",
      sensitivity_class: typeof item.sensitivity_class === "string" ? item.sensitivity_class : "unknown",
      preferred_lane: typeof item.preferred_lane === "string" ? item.preferred_lane : "unknown",
      secondary_lane: typeof item.secondary_lane === "string" ? item.secondary_lane : "unknown",
      overflow_lane: typeof item.overflow_lane === "string" ? item.overflow_lane : "unknown",
      default_execution_mode: typeof item.default_execution_mode === "string" ? item.default_execution_mode : "unknown",
      provider: typeof item.provider === "string" ? item.provider : "unknown",
      runtime: typeof item.runtime === "string" ? item.runtime : "unknown",
      privacy: typeof item.privacy === "string" ? item.privacy : "unknown",
      degraded: Boolean(item.degraded),
      degraded_failure_class:
        typeof item.degraded_failure_class === "string" ? item.degraded_failure_class : null,
      selection_reason: typeof item.selection_reason === "string" ? item.selection_reason : "",
      quota_signal:
        item.quota_signal && typeof item.quota_signal === "object"
          ? {
              provider_or_family:
                typeof (item.quota_signal as Record<string, unknown>).provider_or_family === "string"
                  ? ((item.quota_signal as Record<string, string>).provider_or_family ?? null)
                  : null,
              confidence:
                typeof (item.quota_signal as Record<string, unknown>).confidence === "string"
                  ? ((item.quota_signal as Record<string, string>).confidence ?? null)
                  : null,
              remaining_units:
                typeof (item.quota_signal as Record<string, unknown>).remaining_units === "number"
                  ? ((item.quota_signal as Record<string, number>).remaining_units ?? null)
                  : null,
              budget_remaining_usd:
                typeof (item.quota_signal as Record<string, unknown>).budget_remaining_usd === "number"
                  ? ((item.quota_signal as Record<string, number>).budget_remaining_usd ?? null)
                  : null,
              degraded_reason:
                typeof (item.quota_signal as Record<string, unknown>).degraded_reason === "string"
                  ? ((item.quota_signal as Record<string, string>).degraded_reason ?? null)
                  : null,
            }
          : null,
    })),
  };
}
