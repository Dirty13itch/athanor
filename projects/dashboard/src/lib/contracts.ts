import { z } from "zod";

export const serviceCategorySchema = z.enum([
  "inference",
  "observability",
  "media",
  "experience",
  "platform",
  "knowledge",
  "home",
]);

export const statusToneSchema = z.enum(["healthy", "warning", "degraded", "muted"]);
export const taskPrioritySchema = z.enum(["critical", "high", "normal", "low"]);
export const taskStatusSchema = z.enum([
  "pending",
  "pending_approval",
  "running",
  "completed",
  "failed",
  "cancelled",
]);

export const chartPointSchema = z.object({
  timestamp: z.string(),
  value: z.number().nullable(),
});

export const timelinePointSchema = z.object({
  timestamp: z.string(),
  availability: z.number().min(0).max(1).nullable(),
  latencyMs: z.number().nullable(),
});

export const clusterNodeSchema = z.object({
  id: z.string(),
  name: z.string(),
  ip: z.string(),
  role: z.string(),
  totalServices: z.number().int().nonnegative(),
  healthyServices: z.number().int().nonnegative(),
  degradedServices: z.number().int().nonnegative(),
  averageLatencyMs: z.number().nullable(),
  gpuUtilization: z.number().nullable(),
});

export const serviceSnapshotSchema = z.object({
  id: z.string(),
  name: z.string(),
  nodeId: z.string(),
  node: z.string(),
  category: serviceCategorySchema,
  description: z.string(),
  url: z.string().url(),
  healthy: z.boolean(),
  latencyMs: z.number().nullable(),
  checkedAt: z.string(),
  state: statusToneSchema,
});

export const serviceHistorySeriesSchema = z.object({
  serviceId: z.string(),
  serviceName: z.string(),
  nodeId: z.string(),
  category: serviceCategorySchema,
  points: z.array(timelinePointSchema),
});

export const gpuSnapshotSchema = z.object({
  id: z.string(),
  gpuName: z.string(),
  gpuBusId: z.string(),
  instance: z.string(),
  nodeId: z.string(),
  node: z.string(),
  utilization: z.number().nullable(),
  memoryUsedMiB: z.number().nullable(),
  memoryTotalMiB: z.number().nullable(),
  temperatureC: z.number().nullable(),
  powerW: z.number().nullable(),
});

export const gpuNodeSummarySchema = z.object({
  nodeId: z.string(),
  node: z.string(),
  gpuCount: z.number().int().nonnegative(),
  averageUtilization: z.number().nullable(),
  averageTemperature: z.number().nullable(),
  totalPowerW: z.number().nullable(),
  totalMemoryUsedMiB: z.number().nullable(),
  totalMemoryMiB: z.number().nullable(),
});

export const metricSeriesSchema = z.object({
  id: z.string(),
  label: z.string(),
  points: z.array(chartPointSchema),
});

export const externalToolSchema = z.object({
  id: z.string(),
  label: z.string(),
  description: z.string(),
  url: z.string().url(),
});

export const modelInventoryEntrySchema = z.object({
  id: z.string(),
  backendId: z.string(),
  backend: z.string(),
  target: z.string(),
  description: z.string(),
  available: z.boolean(),
});

export const backendSnapshotSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  nodeId: z.string(),
  url: z.string().url(),
  reachable: z.boolean(),
  modelCount: z.number().int().nonnegative(),
  models: z.array(z.string()),
});

export const agentInfoSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  icon: z.string(),
  tools: z.array(z.string()),
  status: z.enum(["ready", "unavailable"]),
});

export const alertSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  tone: statusToneSchema,
  href: z.string(),
});

export const commandRightsProfileSchema = z.object({
  subject: z.string(),
  can: z.array(z.string()),
  cannot: z.array(z.string()),
  approval_mode: z.string(),
});

export const commandHierarchyLayerSchema = z.object({
  id: z.string(),
  label: z.string(),
  role: z.string(),
  summary: z.string(),
});

export const metaLaneSelectionRecordSchema = z.object({
  id: z.string(),
  label: z.string(),
  lead: z.string(),
  default_for: z.array(z.string()),
  cloud_allowed: z.boolean(),
  status: z.string(),
  examples: z.array(z.string()),
});

export const policyClassRecordSchema = z.object({
  id: z.string(),
  label: z.string(),
  default_meta_lane: z.string(),
  cloud_allowed: z.boolean(),
  sovereign_required: z.boolean(),
  description: z.string(),
});

export const navAttentionTierSchema = z.enum(["none", "watch", "action", "urgent"]);
export const navAttentionSourceSchema = z.enum([
  "clear",
  "pending_approvals",
  "failed_tasks",
  "queued_work",
  "critical_notifications",
  "actionable_notifications",
  "informational_notifications",
  "pending_review_queue",
  "review_activity",
  "degraded_core_services",
  "degraded_services",
  "workplan_refill",
  "planning_backlog",
  "agent_roster_missing",
  "agent_unavailable",
  "agent_degraded",
]);

export const navAttentionSignalSchema = z.object({
  routeHref: z.string(),
  tier: navAttentionTierSchema,
  count: z.number().int().nonnegative().nullable(),
  reason: z.string(),
  source: navAttentionSourceSchema,
  updatedAt: z.string(),
  signature: z.string(),
});

export const modelRoleProfileSchema = z.object({
  id: z.string(),
  label: z.string(),
  plane: z.string(),
  status: z.string(),
  champion: z.string(),
  challengers: z.array(z.string()),
  workload_classes: z.array(z.string()),
  strengths: z.array(z.string()),
  weaknesses: z.array(z.string()),
  refusal_posture: z.string(),
  privacy_posture: z.string(),
});

export const workloadClassProfileSchema = z.object({
  id: z.string(),
  label: z.string(),
  policy_default: z.string(),
  frontier_supervisor: z.string(),
  sovereign_supervisor: z.string(),
  primary_worker_lane: z.string(),
  fallback_worker_lanes: z.array(z.string()),
  judge_lane: z.string(),
  default_autonomy: z.string(),
  parallelism: z.string(),
});

export const modelCandidateSummarySchema = z.object({
  role_id: z.string(),
  label: z.string(),
  plane: z.string(),
  status: z.string(),
  champion: z.string(),
  challenger_count: z.number().int().nonnegative(),
  workload_count: z.number().int().nonnegative(),
});

export const provingGroundCorpusSchema = z.object({
  id: z.string(),
  sensitivity: z.string(),
  allowed_lanes: z.array(z.string()),
  purpose: z.string(),
});

export const promotionCandidateQueueSchema = z.object({
  role_id: z.string(),
  label: z.string(),
  champion: z.string(),
  challengers: z.array(z.string()),
  plane: z.string(),
});

export const promotionRecordSchema = z.object({
  id: z.string(),
  asset_class: z.string(),
  role_id: z.string(),
  role_label: z.string(),
  plane: z.string(),
  candidate: z.string(),
  champion: z.string(),
  current_tier: z.string(),
  target_tier: z.string(),
  status: z.string(),
  reason: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  updated_by: z.string(),
  source: z.string(),
  rollout_steps: z.array(z.string()),
  next_tier: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional(),
  rollback_target: z.string().nullable().optional(),
  notes: z.array(z.string()),
});

export const promotionControlsSchema = z.object({
  generated_at: z.string(),
  status: z.string(),
  tiers: z.array(z.string()),
  ritual: z.array(z.string()),
  counts: z.record(z.string(), z.number().int().nonnegative()),
  active_promotions: z.array(promotionRecordSchema),
  recent_promotions: z.array(promotionRecordSchema),
  recent_events: z.array(
    z.object({
      event: z.string(),
      promotion_id: z.string(),
      role_id: z.string().nullable().optional(),
      candidate: z.string().nullable().optional(),
      target_tier: z.string().nullable().optional(),
      tier: z.string().nullable().optional(),
      status: z.string().nullable().optional(),
      timestamp: z.string(),
      actor: z.string(),
    })
  ),
  candidate_queue: z.array(promotionCandidateQueueSchema),
  next_actions: z.array(z.string()),
});

export const retirementCandidateQueueSchema = z.object({
  asset_class: z.string(),
  asset_id: z.string(),
  label: z.string(),
  role_id: z.string().optional(),
  plane: z.string().optional(),
  current_stage: z.string(),
});

export const retirementRecordSchema = z.object({
  id: z.string(),
  asset_class: z.string(),
  asset_id: z.string(),
  label: z.string(),
  current_stage: z.string(),
  target_stage: z.string(),
  status: z.string(),
  reason: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  updated_by: z.string(),
  source: z.string(),
  next_stage: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional(),
  rollback_target: z.string().nullable().optional(),
  notes: z.array(z.string()).optional(),
});

export const retirementControlsSchema = z.object({
  generated_at: z.string(),
  status: z.string(),
  asset_classes: z.array(z.string()),
  stages: z.array(z.string()),
  rule: z.string(),
  counts: z.record(z.string(), z.number().int().nonnegative()),
  active_retirements: z.array(retirementRecordSchema),
  recent_retirements: z.array(retirementRecordSchema),
  recent_events: z.array(
    z.object({
      event: z.string(),
      retirement_id: z.string(),
      asset_class: z.string().nullable().optional(),
      asset_id: z.string().nullable().optional(),
      target_stage: z.string().nullable().optional(),
      stage: z.string().nullable().optional(),
      status: z.string().nullable().optional(),
      timestamp: z.string(),
      actor: z.string(),
    })
  ),
  candidate_queue: z.array(retirementCandidateQueueSchema),
  next_actions: z.array(z.string()),
});

export const provingGroundSnapshotSchema = z.object({
  version: z.string(),
  updated_at: z.string().optional(),
  generated_at: z.string().optional(),
  status: z.string(),
  purpose: z.string(),
  evaluation_dimensions: z.array(z.string()),
  corpora: z.array(provingGroundCorpusSchema),
  pipeline_phases: z.array(z.string()),
  promotion_path: z.array(z.string()),
  rollback_rule: z.string(),
  latest_run: z
    .object({
      timestamp: z.string().nullable().optional(),
      passed: z.number().int().nonnegative(),
      total: z.number().int().nonnegative(),
      pass_rate: z.number(),
      patterns_consumed: z.number().int().nonnegative().optional(),
      proposals_generated: z.number().int().nonnegative().optional(),
      errors: z.array(z.string()).optional(),
      source: z.string().optional(),
    })
    .nullable()
    .optional(),
  recent_results: z.array(z.record(z.string(), z.unknown())).optional(),
  corpus_registry_version: z.string().optional(),
  governed_corpora: z.array(z.record(z.string(), z.unknown())).optional(),
  experiment_ledger: z
    .object({
      version: z.string(),
      status: z.string(),
      required_fields: z.array(z.string()),
      retention: z.string(),
      promotion_linkage: z.string(),
      evidence_count: z.number().int().nonnegative(),
    })
    .optional(),
  recent_experiments: z.array(z.record(z.string(), z.unknown())).optional(),
  improvement_summary: z.record(z.string(), z.unknown()).optional(),
  lane_coverage: z.array(modelCandidateSummarySchema).optional(),
  latest_benchmark_run: z.record(z.string(), z.unknown()).optional(),
  promotion_controls: promotionControlsSchema.optional(),
});

export const modelIntelligenceLaneSchema = z.object({
  version: z.string(),
  updated_at: z.string(),
  status: z.string(),
  generated_at: z.string().optional(),
  operational_state: z.string().optional(),
  cadence: z.object({
    weekly_horizon_scan: z.string(),
    weekly_candidate_triage: z.string(),
    monthly_rebaseline: z.string(),
    urgent_scan: z.string(),
  }),
  sources: z.array(z.string()),
  outputs: z.array(z.string()),
  guardrails: z.array(z.string()),
  benchmark_results: z.number().int().nonnegative().optional(),
  pending_proposals: z.number().int().nonnegative().optional(),
  validated_proposals: z.number().int().nonnegative().optional(),
  deployed_proposals: z.number().int().nonnegative().optional(),
  candidate_queue: z
    .array(
      z.object({
        role_id: z.string(),
        label: z.string(),
        plane: z.string(),
        champion: z.string(),
        challengers: z.array(z.string()),
      })
    )
    .optional(),
  last_cycle: z
    .object({
      timestamp: z.string(),
      patterns_consumed: z.number().int().nonnegative(),
      proposals_generated: z.number().int().nonnegative(),
      benchmarks: z
        .object({
          passed: z.number().int().nonnegative(),
          total: z.number().int().nonnegative(),
          pass_rate: z.number(),
        })
        .nullable(),
      errors: z.array(z.string()).optional(),
    })
    .nullable()
    .optional(),
  cadence_jobs: z
    .array(
      z.object({
        id: z.string(),
        title: z.string(),
        cadence: z.string(),
        current_state: z.string(),
        last_run: z.string().nullable(),
        next_run: z.string().nullable(),
        last_outcome: z.string(),
        paused: z.boolean().optional(),
        governor_reason: z.string().nullable().optional(),
      })
    )
    .optional(),
  next_actions: z.array(z.string()).optional(),
});

export const governanceContractSummarySchema = z.object({
  id: z.string(),
  label: z.string(),
  owner: z.string(),
  purpose: z.string(),
  status: z.string(),
});

export const governedEvalCorpusSchema = z.object({
  id: z.string(),
  label: z.string(),
  workload_classes: z.array(z.string()),
  sensitivity: z.string(),
  allowed_lanes: z.array(z.string()),
  refresh_cadence: z.string(),
  baseline_version: z.string(),
});

export const experimentEvidenceSchema = z.object({
  id: z.string(),
  name: z.string(),
  category: z.string(),
  passed: z.boolean(),
  score: z.number(),
  max_score: z.number(),
  timestamp: z.string().nullable().optional(),
});

export const governanceLayersSchema = z.object({
  contract_registry: z.object({
    version: z.string(),
    status: z.string(),
    count: z.number().int().nonnegative(),
    contracts: z.array(governanceContractSummarySchema),
    status_counts: z.record(z.string(), z.number().int().nonnegative()),
    provenance_contract: governanceContractSummarySchema.nullable(),
  }),
  eval_corpora: z.object({
    version: z.string(),
    status: z.string(),
    count: z.number().int().nonnegative(),
    corpora: z.array(governedEvalCorpusSchema),
    sensitivity_counts: z.record(z.string(), z.number().int().nonnegative()),
    runtime_result_count: z.number().int().nonnegative(),
    latest_result_at: z.string().nullable(),
  }),
  release_ritual: z.object({
    version: z.string(),
    tier_count: z.number().int().nonnegative(),
    status: z.string(),
  }),
  experiment_ledger: z.object({
    version: z.string(),
    status: z.string(),
    required_field_count: z.number().int().nonnegative(),
    required_fields: z.array(z.string()),
    retention: z.string(),
    promotion_linkage: z.string(),
    evidence_count: z.number().int().nonnegative(),
    recent_experiments: z.array(experimentEvidenceSchema),
    recent_promotion_events: z.array(
      z.object({
        event: z.string(),
        promotion_id: z.string(),
        role_id: z.string().nullable().optional(),
        candidate: z.string().nullable().optional(),
        target_tier: z.string().nullable().optional(),
        tier: z.string().nullable().optional(),
        status: z.string().nullable().optional(),
        timestamp: z.string(),
        actor: z.string(),
      })
    ),
  }),
  deprecation_retirement: z.object({
    version: z.string(),
    status: z.string(),
    asset_class_count: z.number().int().nonnegative(),
    asset_classes: z.array(z.string()),
    stages: z.array(z.string()),
    rule: z.string(),
  }),
  operator_runbooks: z.object({
    version: z.string(),
    runbook_count: z.number().int().nonnegative(),
    status: z.string(),
  }),
});

export const modelGovernanceSnapshotSchema = z.object({
  generated_at: z.string(),
  role_registry_version: z.string(),
  workload_registry_version: z.string(),
  rights_registry_version: z.string(),
  policy_registry_version: z.string(),
  role_count: z.number().int().nonnegative(),
  workload_count: z.number().int().nonnegative(),
  champion_summary: z.array(modelCandidateSummarySchema),
  role_registry: z.array(modelRoleProfileSchema),
  workload_registry: z.array(workloadClassProfileSchema),
  proving_ground: provingGroundSnapshotSchema,
  promotion_controls: promotionControlsSchema.optional(),
  retirement_controls: retirementControlsSchema.optional(),
  model_intelligence: modelIntelligenceLaneSchema,
  governance_layers: governanceLayersSchema,
});

export const commandDecisionRecordSchema = z.object({
  id: z.string(),
  decided_by: z.string(),
  authority_layer: z.string(),
  workload_class: z.string(),
  policy_class: z.string(),
  meta_lane: z.string(),
  policy_version: z.string().optional(),
  rights_version: z.string().optional(),
  workload_registry_version: z.string().optional(),
  prompt_version: z.string().optional(),
  corpus_version: z.string().nullable().optional(),
  reason: z.string(),
  approved: z.boolean(),
  created_at: z.string(),
});

export const planPacketSchema = z.object({
  id: z.string(),
  summary: z.string(),
  workload_class: z.string(),
  policy_class: z.string(),
  meta_lane: z.string(),
  supervisor_lane: z.string(),
  worker_lane: z.string(),
  judge_lane: z.string().optional(),
  fallback_worker_lanes: z.array(z.string()).optional(),
  approval_mode: z.string(),
  policy_version: z.string().optional(),
  workload_registry_version: z.string().optional(),
  prompt_version: z.string().optional(),
  corpus_version: z.string().nullable().optional(),
  notes: z.array(z.string()),
});

export const runLineageRecordSchema = z.object({
  run_id: z.string(),
  parent_run_id: z.string().nullable(),
  supervisor_run_id: z.string().nullable(),
  worker_run_id: z.string().nullable(),
  judge_run_id: z.string().nullable(),
  provider: z.string().nullable(),
  lane: z.string(),
});

export const artifactProvenanceRecordSchema = z.object({
  run_id: z.string(),
  status: z.string(),
  deciding_layer: z.string(),
  policy_class: z.string().nullable().optional(),
  meta_lane: z.string().nullable().optional(),
  supervisor_lane: z.string().nullable().optional(),
  worker_lane: z.string().nullable().optional(),
  judge_lane: z.string().nullable().optional(),
  provider: z.string(),
  artifact_ref_count: z.number().int().nonnegative(),
  prompt_version: z.string().nullable().optional(),
  policy_version: z.string().nullable().optional(),
  corpus_version: z.string().nullable().optional(),
  contract_registry_version: z.string().nullable().optional(),
  experiment_ledger_version: z.string().nullable().optional(),
});

export const executionRunRecordSchema = z.object({
  id: z.string(),
  source_lane: z.string(),
  run_type: z.string(),
  task_id: z.string().nullable(),
  job_id: z.string().nullable().optional(),
  agent: z.string(),
  provider: z.string(),
  lease_id: z.string().nullable(),
  status: z.string(),
  created_at: z.string().nullable(),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  policy_class: z.string().nullable().optional(),
  approval_mode: z.string().nullable().optional(),
  command_decision_id: z.string().nullable().optional(),
  supervisor_lane: z.string().nullable().optional(),
  worker_lane: z.string().nullable().optional(),
  judge_lane: z.string().nullable().optional(),
  prompt_version: z.string().nullable().optional(),
  policy_version: z.string().nullable().optional(),
  corpus_version: z.string().nullable().optional(),
  lineage: runLineageRecordSchema.optional(),
  artifact_provenance: artifactProvenanceRecordSchema.optional(),
  artifact_refs: z.array(
    z.object({
      label: z.string(),
      href: z.string(),
    })
  ),
  failure_reason: z.string().nullable(),
  summary: z.string(),
});

export const scheduledJobRecordSchema = z.object({
  id: z.string(),
  job_family: z.string(),
  title: z.string(),
  cadence: z.string(),
  trigger_mode: z.string(),
  last_run: z.string().nullable(),
  next_run: z.string().nullable(),
  current_state: z.string(),
  last_outcome: z.string(),
  owner_agent: z.string(),
  deep_link: z.string(),
  control_scope: z.string().nullable().optional(),
  paused: z.boolean().optional(),
  can_run_now: z.boolean().optional(),
  can_override_now: z.boolean().optional(),
  governor_reason: z.string().nullable().optional(),
  presence_state: z.string().nullable().optional(),
  release_tier: z.string().nullable().optional(),
  capacity_posture: z.string().nullable().optional(),
  queue_posture: z.string().nullable().optional(),
  provider_posture: z.string().nullable().optional(),
  active_window_ids: z.array(z.string()).optional(),
  priority_band: z.string().nullable().optional(),
  deferred_by: z.string().nullable().optional(),
  next_action: z.string().nullable().optional(),
  last_summary: z.string().optional(),
  last_error: z.string().nullable().optional(),
  last_actor: z.string().nullable().optional(),
  last_force_override: z.boolean().optional(),
  last_task_id: z.string().nullable().optional(),
  last_plan_id: z.string().nullable().optional(),
});

export const operatorStreamEventSchema = z.object({
  id: z.string(),
  timestamp: z.string().nullable(),
  severity: z.enum(["info", "warning", "error", "success"]),
  subsystem: z.string(),
  event_type: z.string(),
  subject: z.string(),
  summary: z.string(),
  deep_link: z.string(),
  related_run_id: z.string().nullable(),
});

export const quotaLeaseProviderSchema = z.object({
  provider: z.string(),
  lane: z.string(),
  availability: z.string(),
  provider_state: z.string().optional(),
  state_reasons: z.array(z.string()).optional(),
  reserve_state: z.string(),
  privacy: z.string().optional(),
  limit: z.number().int().nonnegative(),
  remaining: z.number().int().nonnegative(),
  throttle_events: z.number().int().nonnegative(),
  recent_outcomes: z.array(
    z.object({
      outcome: z.string(),
      count: z.number().int().nonnegative(),
    })
  ),
  last_issued_at: z.string().nullable(),
  last_outcome_at: z.string().nullable(),
  direct_execution_ready: z.boolean().optional(),
  governed_handoff_ready: z.boolean().optional(),
  execution_mode: z.string().optional(),
  bridge_status: z.string().optional(),
  recent_execution_state: z.string().optional(),
  recent_execution_detail: z.string().optional(),
  next_action: z.string().optional(),
  pending_handoffs: z.number().int().nonnegative().optional(),
  completed_handoffs: z.number().int().nonnegative().optional(),
  failed_handoffs: z.number().int().nonnegative().optional(),
  fallback_handoffs: z.number().int().nonnegative().optional(),
  direct_execution_count: z.number().int().nonnegative().optional(),
  handoff_bundle_count: z.number().int().nonnegative().optional(),
});

export const quotaLeaseSummarySchema = z.object({
  policy_source: z.string(),
  provider_summaries: z.array(quotaLeaseProviderSchema),
  recent_leases: z.array(executionRunRecordSchema),
  count: z.number().int().nonnegative(),
});

export const governorLaneSchema = z.object({
  id: z.string(),
  label: z.string(),
  description: z.string(),
  paused: z.boolean(),
  status: z.string(),
});

export const capacityNodeSchema = z.object({
  id: z.string(),
  alive: z.boolean(),
  stale: z.boolean(),
  max_gpu_util_pct: z.number(),
  healthy_models: z.number().int().nonnegative(),
  total_models: z.number().int().nonnegative(),
  load_1m: z.number(),
  ram_available_mb: z.number().int().nonnegative(),
});

export const capacitySnapshotSchema = z.object({
  generated_at: z.string(),
  posture: z.string(),
  queue: z.object({
    posture: z.string(),
    pending: z.number().int().nonnegative(),
    running: z.number().int().nonnegative(),
    max_concurrent: z.number().int().nonnegative(),
    failed: z.number().int().nonnegative(),
  }),
  workspace: z.object({
    broadcast_items: z.number().int().nonnegative(),
    capacity: z.number().int().nonnegative(),
    utilization: z.number(),
  }),
  scheduler: z.object({
    running: z.boolean(),
    enabled_count: z.number().int().nonnegative(),
  }),
  provider_reserve: z.object({
    posture: z.string(),
    constrained_count: z.number().int().nonnegative(),
  }),
  active_time_windows: z.array(
    z.object({
      id: z.string(),
      window: z.string(),
      protects: z.array(z.string()),
      status: z.string(),
    })
  ),
  nodes: z.array(capacityNodeSchema),
  recommendations: z.array(z.string()),
});

export const governorPresenceSchema = z.object({
  state: z.string(),
  label: z.string(),
  automation_posture: z.string(),
  notification_posture: z.string(),
  approval_posture: z.string(),
  updated_at: z.string().nullable(),
  updated_by: z.string(),
  mode: z.enum(["auto", "manual"]),
  configured_state: z.string(),
  configured_label: z.string(),
  signal_state: z.string().nullable(),
  signal_source: z.string().nullable(),
  signal_updated_at: z.string().nullable(),
  signal_updated_by: z.string(),
  signal_fresh: z.boolean(),
  signal_age_seconds: z.number().nullable(),
  effective_reason: z.string(),
});

export const governorReleaseTierSchema = z.object({
  state: z.string(),
  available_tiers: z.array(z.string()),
  status: z.string(),
  updated_at: z.string().nullable(),
  updated_by: z.string(),
});

export const governorSnapshotSchema = z.object({
  generated_at: z.string(),
  status: z.string(),
  global_mode: z.string(),
  degraded_mode: z.string(),
  reason: z.string(),
  updated_at: z.string().nullable(),
  updated_by: z.string(),
  lanes: z.array(governorLaneSchema),
  capacity: capacitySnapshotSchema,
  presence: governorPresenceSchema,
  release_tier: governorReleaseTierSchema,
  command_rights_version: z.string(),
  control_stack: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      status: z.string(),
    })
  ),
});

export const judgeVerdictSchema = z.object({
  run_id: z.string(),
  agent: z.string().nullable().optional(),
  provider: z.string(),
  policy_class: z.string().nullable().optional(),
  score: z.number(),
  verdict: z.string(),
  rationale: z.string(),
  deep_link: z.string(),
});

export const judgePlaneSnapshotSchema = z.object({
  generated_at: z.string(),
  status: z.string(),
  role_id: z.string(),
  label: z.string(),
  champion: z.string(),
  challengers: z.array(z.string()),
  workload_classes: z.array(z.string()),
  summary: z.object({
    recent_verdicts: z.number().int().nonnegative(),
    accept_count: z.number().int().nonnegative(),
    reject_count: z.number().int().nonnegative(),
    review_required: z.number().int().nonnegative(),
    acceptance_rate: z.number(),
    pending_review_queue: z.number().int().nonnegative(),
  }),
  guardrails: z.array(z.string()),
  recent_verdicts: z.array(judgeVerdictSchema),
});

export const executionRunsResponseSchema = z.object({
  runs: z.array(executionRunRecordSchema),
});

export const scheduledJobsResponseSchema = z.object({
  jobs: z.array(scheduledJobRecordSchema),
});

export const operatorStreamResponseSchema = z.object({
  events: z.array(operatorStreamEventSchema),
});

export const subscriptionSummaryResponseSchema = quotaLeaseSummarySchema;
export const governorResponseSchema = governorSnapshotSchema;
export const judgePlaneResponseSchema = judgePlaneSnapshotSchema;

export const syntheticOperatorTestFlowSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string().optional(),
  status: z.string(),
  last_outcome: z.string().nullable().optional(),
  last_run_at: z.string().nullable().optional(),
  last_duration_ms: z.number().int().nonnegative().nullable().optional(),
  checks_passed: z.number().int().nonnegative().optional(),
  checks_total: z.number().int().nonnegative().optional(),
  evidence: z.array(z.string()),
  notes: z.array(z.string()).optional(),
  details: z.record(z.string(), z.unknown()).optional(),
});

export const operatorTestsSnapshotSchema = z.object({
  generated_at: z.string(),
  status: z.string(),
  last_outcome: z.string(),
  last_run_at: z.string().nullable(),
  flow_count: z.number().int().nonnegative(),
  flows: z.array(syntheticOperatorTestFlowSchema),
});

export const operationsRunbookSchema = z
  .object({
    id: z.string(),
    label: z.string(),
    description: z.string().optional(),
    cadence: z.string().nullable().optional(),
    related_surface: z.string().nullable().optional(),
    support_status: z.string().optional(),
    evidence_flow_ids: z.array(z.string()).optional(),
  })
  .passthrough();

export const restoreReadinessStoreSchema = z
  .object({
    id: z.string(),
    label: z.string().optional(),
    drill_status: z.string().optional(),
    cadence: z.string().nullable().optional(),
    restore_order: z.number().nullable().optional(),
    verified: z.boolean().optional(),
    probe_status: z.string().nullable().optional(),
    probe_summary: z.string().nullable().optional(),
    last_drill_at: z.string().nullable().optional(),
    last_outcome: z.string().nullable().optional(),
    artifacts: z.array(z.string()).optional(),
  })
  .passthrough();

export const lifecycleClassSchema = z
  .object({
    id: z.string(),
    label: z.string().optional(),
    sovereign_only: z.boolean().optional(),
    cloud_allowed: z.boolean().optional(),
    retention: z.string().nullable().optional(),
  })
  .passthrough();

export const toolPermissionSubjectSchema = z
  .object({
    subject: z.string(),
    label: z.string().optional(),
    mode: z.string().optional(),
    allow: z.array(z.string()).optional(),
    deny: z.array(z.string()).optional(),
    allow_count: z.number().int().nonnegative().optional(),
    deny_count: z.number().int().nonnegative().optional(),
    direct_execution: z.boolean().optional(),
  })
  .passthrough();

export const operationsReadinessSnapshotSchema = z.object({
  generated_at: z.string(),
  status: z.string(),
  runbooks: z.object({
    status: z.string(),
    items: z.array(operationsRunbookSchema),
  }),
  backup_restore: z.object({
    status: z.string(),
    drill_mode: z.string().optional(),
    last_drill_at: z.string().nullable().optional(),
    last_outcome: z.string().nullable().optional(),
    verified_store_count: z.number().int().nonnegative().optional(),
    store_count: z.number().int().nonnegative().optional(),
    critical_stores: z.array(restoreReadinessStoreSchema),
  }),
  release_ritual: z.object({
    status: z.string(),
    tiers: z.array(z.string()),
    ritual: z.array(z.string()),
    last_rehearsal_at: z.string().nullable().optional(),
    last_outcome: z.string().nullable().optional(),
    rehearsal_status: z.string().optional(),
    active_promotion_count: z.number().int().nonnegative().optional(),
  }),
  deprecation_retirement: z.object({
    status: z.string(),
    asset_classes: z.array(z.string()),
    stages: z.array(z.string()),
    rule: z.string(),
    recent_retirement_count: z.number().int().nonnegative().optional(),
    active_retirement_count: z.number().int().nonnegative().optional(),
    last_rehearsal_at: z.string().nullable().optional(),
    last_outcome: z.string().nullable().optional(),
    recent_retirements: z.array(retirementRecordSchema).optional(),
  }),
  economic_governance: z.object({
    status: z.string(),
    premium_reserve_lanes: z.array(z.string()),
    automatic_spend_lanes: z.array(z.string()),
    approval_required_lanes: z.array(z.string()),
    downgrade_order: z.array(z.string()),
    provider_count: z.number().int().nonnegative().optional(),
    recent_lease_count: z.number().int().nonnegative().optional(),
    constrained_count: z.number().int().nonnegative().optional(),
    last_verified_at: z.string().nullable().optional(),
    last_outcome: z.string().nullable().optional(),
  }),
  data_lifecycle: z.object({
    status: z.string(),
    classes: z.array(lifecycleClassSchema),
    class_count: z.number().int().nonnegative().optional(),
    run_count: z.number().int().nonnegative().optional(),
    eval_artifact_count: z.number().int().nonnegative().optional(),
    last_verified_at: z.string().nullable().optional(),
    last_outcome: z.string().nullable().optional(),
  }),
  tool_permissions: z.object({
    status: z.string(),
    default_mode: z.string(),
    subject_count: z.number().int().nonnegative().optional(),
    enforced_subject_count: z.number().int().nonnegative().optional(),
    denied_action_count: z.number().int().nonnegative().optional(),
    last_verified_at: z.string().nullable().optional(),
    last_outcome: z.string().nullable().optional(),
    subjects: z.array(toolPermissionSubjectSchema),
  }),
  synthetic_operator_tests: z.object({
    status: z.string(),
    last_outcome: z.string(),
    last_run_at: z.string().nullable(),
    flow_count: z.number().int().nonnegative(),
    flows: z.array(syntheticOperatorTestFlowSchema),
  }),
});

export const systemMapSnapshotSchema = z.object({
  generated_at: z.string(),
  owner: z.object({
    id: z.string(),
    label: z.string(),
    role: z.string(),
  }),
  constitution: z.object({
    label: z.string(),
    source: z.string(),
    enforcement: z.string(),
    version: z.string().optional(),
    core_rules: z.array(z.string()).optional(),
    local_only_domains: z.array(z.string()).optional(),
  }),
  governor: z.object({
    label: z.string(),
    role: z.string(),
    status: z.string(),
    rights: z.array(z.string()),
  }),
  authority_order: z.array(commandHierarchyLayerSchema),
  meta_lanes: z.array(metaLaneSelectionRecordSchema),
  control_stack: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      role: z.string(),
      entrypoints: z.array(z.string()),
      status: z.string(),
    })
  ),
  specialists: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      role: z.string(),
      authority: z.string(),
      tool_count: z.number().int().nonnegative(),
      mode: z.string(),
      status: z.string(),
    })
  ),
  model_planes: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      role: z.string(),
      status: z.string(),
    })
  ),
  command_rights: z.array(commandRightsProfileSchema),
  policy_classes: z.array(policyClassRecordSchema),
  operational_governance: z
    .object({
      capacity_governor: z.object({
        status: z.string(),
        arbitration_order: z.array(z.string()),
        time_window_count: z.number().int().nonnegative(),
      }),
      economic_governance: z.object({
        status: z.string(),
        reserve_lanes: z.array(z.string()),
        downgrade_order: z.array(z.string()),
      }),
      presence_model: z.object({
        status: z.string(),
        default_state: z.string(),
        states: z.array(
          z.object({
            id: z.string(),
            label: z.string(),
            automation_posture: z.string(),
            notification_posture: z.string(),
            approval_posture: z.string(),
          })
        ),
      }),
      data_lifecycle: z.object({
        status: z.string(),
        class_count: z.number().int().nonnegative(),
        sovereign_only_classes: z.array(z.string()),
      }),
      backup_restore: z.object({
        status: z.string(),
        critical_store_count: z.number().int().nonnegative(),
        drill_status: z.string(),
      }),
      tool_permissions: z.object({
        status: z.string(),
        subject_count: z.number().int().nonnegative(),
        default_mode: z.string(),
      }),
      release_ritual: z.object({
        status: z.string(),
        tiers: z.array(z.string()),
      }),
    })
    .optional(),
  registry_versions: z.object({
    command_rights: z.string(),
    policy_classes: z.string(),
    constitution: z.string().optional(),
    capacity_governor: z.string().optional(),
    economic_governance: z.string().optional(),
    data_lifecycle: z.string().optional(),
    presence_model: z.string().optional(),
    tool_permissions: z.string().optional(),
    backup_restore: z.string().optional(),
    release_ritual: z.string().optional(),
  }),
  workload_guidance: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      strategy: z.string(),
      supervisor_lane: z.string(),
      worker_lane: z.string(),
      judge_lane: z.string(),
    })
  ),
  policy_source: z.string(),
});

export const projectSnapshotSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  headline: z.string(),
  status: z.string(),
  kind: z.enum(["core", "tenant", "domain", "scaffold"]),
  firstClass: z.boolean(),
  lens: z.string(),
  primaryRoute: z.string(),
  externalUrl: z.string().url().nullable(),
  agents: z.array(z.string()),
  needsCount: z.number().int().nonnegative(),
  constraints: z.array(z.string()),
  operatorChain: z.array(z.string()),
});

export const workforceTaskSchema = z.object({
  id: z.string(),
  agentId: z.string(),
  prompt: z.string(),
  priority: taskPrioritySchema,
  status: taskStatusSchema,
  createdAt: z.string(),
  startedAt: z.string().nullable(),
  completedAt: z.string().nullable(),
  durationMs: z.number().int().nullable(),
  requiresApproval: z.boolean(),
  source: z.string().nullable(),
  projectId: z.string().nullable(),
  planId: z.string().nullable(),
  rationale: z.string().nullable(),
  parentTaskId: z.string().nullable(),
  result: z.string().nullable(),
  error: z.string().nullable(),
  stepCount: z.number().int().nonnegative(),
});

export const workplanTaskSchema = z.object({
  taskId: z.string().nullable(),
  agentId: z.string(),
  projectId: z.string().nullable(),
  prompt: z.string(),
  priority: taskPrioritySchema,
  rationale: z.string().nullable(),
  requiresApproval: z.boolean(),
});

export const workplanSnapshotSchema = z.object({
  planId: z.string(),
  generatedAt: z.string(),
  timeContext: z.string().nullable(),
  focus: z.string(),
  taskCount: z.number().int().nonnegative(),
  tasks: z.array(workplanTaskSchema),
  error: z.string().nullable().optional(),
});

export const workforceGoalSchema = z.object({
  id: z.string(),
  text: z.string(),
  agentId: z.string(),
  priority: z.enum(["low", "normal", "high"]),
  createdAt: z.string(),
  active: z.boolean(),
});

export const workforceNotificationSchema = z.object({
  id: z.string(),
  agentId: z.string(),
  action: z.string(),
  category: z.string(),
  confidence: z.number().min(0).max(1),
  description: z.string(),
  tier: z.enum(["act", "notify", "ask"]),
  createdAt: z.string(),
  resolved: z.boolean(),
  resolution: z.string().nullable(),
});

export const workforceTrustEntrySchema = z.object({
  agentId: z.string(),
  trustScore: z.number(),
  trustGrade: z.string().nullable(),
  positiveFeedback: z.number().int().nonnegative(),
  negativeFeedback: z.number().int().nonnegative(),
  totalFeedback: z.number().int().nonnegative(),
  escalationCount: z.number().int().nonnegative(),
});

export const workspaceItemSnapshotSchema = z.object({
  id: z.string(),
  sourceAgent: z.string(),
  content: z.string(),
  priority: taskPrioritySchema,
  salience: z.number(),
  createdAt: z.string(),
  ttlSeconds: z.number().int().positive(),
  coalition: z.array(z.string()),
  projectId: z.string().nullable(),
});

export const workspaceSnapshotSchema = z.object({
  totalItems: z.number().int().nonnegative(),
  broadcastItems: z.number().int().nonnegative(),
  capacity: z.number().int().positive(),
  utilization: z.number().min(0).nullable(),
  competitionRunning: z.boolean(),
  agentsActive: z.array(
    z.object({
      agentId: z.string(),
      count: z.number().int().nonnegative(),
    })
  ),
  topItem: workspaceItemSnapshotSchema.nullable(),
  broadcast: z.array(workspaceItemSnapshotSchema),
});

export const workspaceSubscriptionSchema = z.object({
  agentId: z.string(),
  keywords: z.array(z.string()),
  sourceFilters: z.array(z.string()),
  threshold: z.number(),
  reactPromptTemplate: z.string(),
});

export const workforceAgentSnapshotSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  icon: z.string(),
  type: z.string(),
  status: z.enum(["ready", "unavailable"]),
  tools: z.array(z.string()),
  totalTasks: z.number().int().nonnegative(),
  runningTasks: z.number().int().nonnegative(),
  pendingTasks: z.number().int().nonnegative(),
  trustScore: z.number().nullable(),
  trustGrade: z.string().nullable(),
});

export const workplanScheduleSchema = z.object({
  morningRunHourLocal: z.number().int().nonnegative(),
  morningRunMinuteLocal: z.number().int().nonnegative(),
  refillIntervalHours: z.number().positive(),
  minPendingTasks: z.number().int().nonnegative(),
  nextRunAt: z.string(),
});

export const workforceScheduleEntrySchema = z.object({
  agentId: z.string(),
  intervalSeconds: z.number().int().nonnegative(),
  intervalHuman: z.string(),
  enabled: z.boolean(),
  lastRunAt: z.string().nullable(),
  nextRunInSeconds: z.number().int().nonnegative(),
  priority: z.string(),
});

export const projectPostureSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.string(),
  firstClass: z.boolean(),
  lens: z.string(),
  primaryRoute: z.string(),
  externalUrl: z.string().url().nullable(),
  needsCount: z.number().int().nonnegative(),
  mappedAgents: z.number().int().nonnegative(),
  totalTasks: z.number().int().nonnegative(),
  pendingTasks: z.number().int().nonnegative(),
  pendingApprovals: z.number().int().nonnegative(),
  runningTasks: z.number().int().nonnegative(),
  completedTasks: z.number().int().nonnegative(),
  failedTasks: z.number().int().nonnegative(),
  plannedTasks: z.number().int().nonnegative(),
  operatorChain: z.array(z.string()),
  topAgents: z.array(z.string()),
});

export const workforceConventionSchema = z.object({
  id: z.string(),
  type: z.string(),
  agentId: z.string(),
  description: z.string(),
  rule: z.string(),
  source: z.string(),
  occurrences: z.number().int().nonnegative(),
  status: z.string(),
  createdAt: z.string(),
  confirmedAt: z.string().nullable(),
});

export const workforceImprovementSummarySchema = z.object({
  totalProposals: z.number().int().nonnegative(),
  pending: z.number().int().nonnegative(),
  validated: z.number().int().nonnegative(),
  deployed: z.number().int().nonnegative(),
  failed: z.number().int().nonnegative(),
  benchmarkResults: z.number().int().nonnegative(),
  lastCycle: z
    .object({
      timestamp: z.string(),
      patternsConsumed: z.number().int().nonnegative(),
      proposalsGenerated: z.number().int().nonnegative(),
      benchmarks: z
        .object({
          passed: z.number().int().nonnegative(),
          total: z.number().int().nonnegative(),
          passRate: z.number(),
        })
        .nullable(),
    })
    .nullable(),
});

export const workforceSnapshotSchema = z.object({
  generatedAt: z.string(),
  summary: z.object({
    totalTasks: z.number().int().nonnegative(),
    pendingTasks: z.number().int().nonnegative(),
    pendingApprovals: z.number().int().nonnegative(),
    runningTasks: z.number().int().nonnegative(),
    completedTasks: z.number().int().nonnegative(),
    failedTasks: z.number().int().nonnegative(),
    activeGoals: z.number().int().nonnegative(),
    unreadNotifications: z.number().int().nonnegative(),
    avgTrustScore: z.number().nullable(),
    workspaceUtilization: z.number().nullable(),
    activeProjects: z.number().int().nonnegative(),
    queuedProjects: z.number().int().nonnegative(),
  }),
  workplan: z.object({
    current: workplanSnapshotSchema.nullable(),
    history: z.array(workplanSnapshotSchema),
    needsRefill: z.boolean(),
    schedule: workplanScheduleSchema,
  }),
  tasks: z.array(workforceTaskSchema),
  goals: z.array(workforceGoalSchema),
  trust: z.array(workforceTrustEntrySchema),
  notifications: z.array(workforceNotificationSchema),
  workspace: workspaceSnapshotSchema,
  subscriptions: z.array(workspaceSubscriptionSchema),
  conventions: z.object({
    proposed: z.array(workforceConventionSchema),
    confirmed: z.array(workforceConventionSchema),
  }),
  improvement: workforceImprovementSummarySchema.nullable(),
  agents: z.array(workforceAgentSnapshotSchema),
  projects: z.array(projectPostureSchema),
  schedules: z.array(workforceScheduleEntrySchema),
});

export const overviewSnapshotSchema = z.object({
  generatedAt: z.string(),
  summary: z.object({
    totalServices: z.number().int().nonnegative(),
    healthyServices: z.number().int().nonnegative(),
    degradedServices: z.number().int().nonnegative(),
    averageLatencyMs: z.number().nullable(),
    averageGpuUtilization: z.number().nullable(),
    readyAgents: z.number().int().nonnegative(),
    totalAgents: z.number().int().nonnegative(),
    reachableBackends: z.number().int().nonnegative(),
    totalBackends: z.number().int().nonnegative(),
    activeProjects: z.number().int().nonnegative(),
    firstClassProjects: z.number().int().nonnegative(),
  }),
  nodes: z.array(clusterNodeSchema),
  services: z.array(serviceSnapshotSchema),
  serviceTrend: z.array(chartPointSchema),
  gpuTrend: z.array(chartPointSchema),
  backends: z.array(backendSnapshotSchema),
  agents: z.array(agentInfoSchema),
  projects: z.array(projectSnapshotSchema),
  alerts: z.array(alertSchema),
  hotspots: z.array(gpuSnapshotSchema),
  externalTools: z.array(externalToolSchema),
  navAttention: z.array(navAttentionSignalSchema).default([]),
  workforce: workforceSnapshotSchema,
});

export const servicesSnapshotSchema = z.object({
  generatedAt: z.string(),
  summary: z.object({
    total: z.number().int().nonnegative(),
    healthy: z.number().int().nonnegative(),
    degraded: z.number().int().nonnegative(),
    averageLatencyMs: z.number().nullable(),
    slowestServiceId: z.string().nullable(),
    slowestServiceName: z.string().nullable(),
  }),
  nodes: z.array(clusterNodeSchema),
  services: z.array(serviceSnapshotSchema),
});

export const servicesHistorySnapshotSchema = z.object({
  generatedAt: z.string(),
  window: z.string(),
  aggregate: z.array(chartPointSchema),
  series: z.array(serviceHistorySeriesSchema),
});

export const gpuHistorySeriesSchema = z.object({
  id: z.string(),
  label: z.string(),
  nodeId: z.string(),
  points: z.array(
    z.object({
      timestamp: z.string(),
      utilization: z.number().nullable(),
      temperatureC: z.number().nullable(),
      powerW: z.number().nullable(),
      memoryRatio: z.number().nullable(),
    })
  ),
});

export const gpuSnapshotResponseSchema = z.object({
  generatedAt: z.string(),
  summary: z.object({
    gpuCount: z.number().int().nonnegative(),
    averageUtilization: z.number().nullable(),
    averageTemperature: z.number().nullable(),
    totalPowerW: z.number().nullable(),
    totalMemoryUsedMiB: z.number().nullable(),
    totalMemoryMiB: z.number().nullable(),
  }),
  nodes: z.array(gpuNodeSummarySchema),
  gpus: z.array(gpuSnapshotSchema),
});

export const gpuHistoryResponseSchema = z.object({
  generatedAt: z.string(),
  window: z.string(),
  nodes: z.array(metricSeriesSchema),
  gpus: z.array(gpuHistorySeriesSchema),
});

export const modelsSnapshotSchema = z.object({
  generatedAt: z.string(),
  backends: z.array(backendSnapshotSchema),
  models: z.array(modelInventoryEntrySchema),
});

export const agentsSnapshotSchema = z.object({
  generatedAt: z.string(),
  agents: z.array(agentInfoSchema),
});

export const projectsSnapshotSchema = z.object({
  generatedAt: z.string(),
  projects: z.array(projectSnapshotSchema),
});

export const workforceSnapshotResponseSchema = workforceSnapshotSchema;

export const chatStreamEventSchema = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("assistant_delta"),
    timestamp: z.string(),
    content: z.string(),
  }),
  z.object({
    type: z.literal("tool_start"),
    timestamp: z.string(),
    toolCallId: z.string(),
    name: z.string(),
    args: z.record(z.string(), z.unknown()).optional(),
  }),
  z.object({
    type: z.literal("tool_end"),
    timestamp: z.string(),
    toolCallId: z.string(),
    name: z.string(),
    output: z.string().optional(),
    durationMs: z.number().optional(),
    error: z.string().optional(),
  }),
  z.object({
    type: z.literal("done"),
    timestamp: z.string(),
    finishReason: z.string().optional(),
  }),
  z.object({
    type: z.literal("error"),
    timestamp: z.string(),
    message: z.string(),
  }),
]);

export const transcriptMessageSchema = z.object({
  id: z.string(),
  role: z.enum(["user", "assistant"]),
  content: z.string(),
  createdAt: z.string(),
  toolCalls: z
    .array(
      z.object({
        id: z.string(),
        name: z.string(),
        args: z.record(z.string(), z.unknown()).optional(),
        output: z.string().optional(),
        durationMs: z.number().optional(),
        status: z.enum(["running", "done", "error"]),
      })
    )
    .optional(),
});

export const directChatSessionSchema = z.object({
  id: z.string(),
  title: z.string(),
  modelId: z.string(),
  target: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
  messages: z.array(transcriptMessageSchema),
});

export const agentThreadSchema = z.object({
  id: z.string(),
  agentId: z.string(),
  title: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
  messages: z.array(transcriptMessageSchema),
});

export const uiPreferencesSchema = z.object({
  density: z.enum(["comfortable", "compact"]).default("comfortable"),
  lastSelectedAgentId: z.string().nullable().default(null),
  lastSelectedModelKey: z.string().nullable().default(null),
  dismissedHints: z.array(z.string()).default([]),
});

export const historyActivityItemSchema = z.object({
  id: z.string(),
  agentId: z.string(),
  projectId: z.string().nullable(),
  actionType: z.string(),
  inputSummary: z.string(),
  outputSummary: z.string().nullable(),
  toolsUsed: z.array(z.string()),
  durationMs: z.number().nullable(),
  timestamp: z.string(),
  relatedTaskId: z.string().nullable(),
  relatedThreadId: z.string().nullable(),
  reviewTaskId: z.string().nullable(),
  status: taskStatusSchema.nullable(),
  href: z.string(),
});

export const historyConversationItemSchema = z.object({
  id: z.string(),
  threadId: z.string(),
  agentId: z.string(),
  projectId: z.string().nullable(),
  userMessage: z.string(),
  assistantResponse: z.string().nullable(),
  toolsUsed: z.array(z.string()),
  durationMs: z.number().nullable(),
  timestamp: z.string(),
  relatedTaskId: z.string().nullable(),
  href: z.string(),
});

export const historyOutputItemSchema = z.object({
  id: z.string(),
  path: z.string(),
  fileName: z.string(),
  category: z.string(),
  sizeBytes: z.number().int().nonnegative(),
  modifiedAt: z.string(),
  projectId: z.string().nullable(),
  relatedTaskId: z.string().nullable(),
  previewAvailable: z.boolean(),
  href: z.string(),
});

export const historySnapshotSchema = z.object({
  generatedAt: z.string(),
  summary: z.object({
    activityCount: z.number().int().nonnegative(),
    conversationCount: z.number().int().nonnegative(),
    outputCount: z.number().int().nonnegative(),
    reviewCount: z.number().int().nonnegative(),
  }),
  projects: z.array(projectSnapshotSchema),
  agents: z.array(workforceAgentSnapshotSchema),
  tasks: z.array(workforceTaskSchema),
  activity: z.array(historyActivityItemSchema),
  conversations: z.array(historyConversationItemSchema),
  outputs: z.array(historyOutputItemSchema),
});

export const intelligencePatternSchema = z.object({
  type: z.string(),
  severity: z.enum(["high", "medium", "low"]).catch("low"),
  agentId: z.string().nullable().optional(),
  count: z.number().nullable().optional(),
  sampleErrors: z.array(z.string()).default([]),
  thumbsUp: z.number().nullable().optional(),
  thumbsDown: z.number().nullable().optional(),
  topics: z.record(z.string(), z.number()).default({}),
  dominantType: z.string().nullable().optional(),
  actions: z.record(z.string(), z.number()).default({}),
});

export const intelligenceAutonomyAdjustmentSchema = z.object({
  agentId: z.string(),
  category: z.string(),
  previous: z.number(),
  delta: z.number(),
  next: z.number(),
});

export const intelligenceAgentBehaviorSchema = z.object({
  agentId: z.string(),
  dominantTopic: z.string().nullable(),
  dominantType: z.string().nullable(),
  entityCount: z.number().nullable(),
  actions: z.record(z.string(), z.number()).default({}),
});

export const intelligenceReportSchema = z.object({
  timestamp: z.string(),
  periodHours: z.number().int().nonnegative(),
  eventCount: z.number().int().nonnegative(),
  activityCount: z.number().int().nonnegative(),
  patterns: z.array(intelligencePatternSchema),
  recommendations: z.array(z.string()),
  autonomyAdjustments: z.array(intelligenceAutonomyAdjustmentSchema),
  agentBehavior: z.array(intelligenceAgentBehaviorSchema),
});

export const learningSectionSchema = z.object({
  cache: z
    .object({
      totalEntries: z.number().nullable().optional(),
      hitRate: z.number().nullable().optional(),
      tokensSaved: z.number().nullable().optional(),
      avgSimilarity: z.number().nullable().optional(),
    })
    .nullable(),
  circuits: z
    .object({
      services: z.number().nullable().optional(),
      open: z.number().nullable().optional(),
      halfOpen: z.number().nullable().optional(),
      closed: z.number().nullable().optional(),
      totalFailures: z.number().nullable().optional(),
    })
    .nullable(),
  preferences: z
    .object({
      modelTaskPairs: z.number().nullable().optional(),
      totalSamples: z.number().nullable().optional(),
      avgCompositeScore: z.number().nullable().optional(),
      converged: z.number().nullable().optional(),
    })
    .nullable(),
  trust: z
    .object({
      agentsTracked: z.number().nullable().optional(),
      avgTrustScore: z.number().nullable().optional(),
      highTrust: z.number().nullable().optional(),
      lowTrust: z.number().nullable().optional(),
    })
    .nullable(),
  diagnosis: z
    .object({
      recentFailures: z.number().nullable().optional(),
      patternsDetected: z.number().nullable().optional(),
      autoRemediations: z.number().nullable().optional(),
    })
    .nullable(),
  memory: z
    .object({
      collections: z.number().nullable().optional(),
      totalPoints: z.number().nullable().optional(),
    })
    .nullable(),
  tasks: z
    .object({
      total: z.number().nullable().optional(),
      completed: z.number().nullable().optional(),
      failed: z.number().nullable().optional(),
      successRate: z.number().nullable().optional(),
    })
    .nullable(),
});

export const learningSnapshotSchema = z.object({
  timestamp: z.string(),
  metrics: learningSectionSchema,
  summary: z.object({
    overallHealth: z.number().nullable().optional(),
    dataPoints: z.number().nullable().optional(),
    positiveSignals: z.array(z.string()).default([]),
    assessment: z.string().nullable().optional(),
  }),
});

export const intelligenceSnapshotSchema = z.object({
  generatedAt: z.string(),
  projects: z.array(projectSnapshotSchema),
  agents: z.array(workforceAgentSnapshotSchema),
  report: intelligenceReportSchema.nullable(),
  learning: learningSnapshotSchema.nullable(),
  improvement: workforceImprovementSummarySchema.nullable(),
  reviewTasks: z.array(workforceTaskSchema),
});

export const memoryPreferenceSchema = z.object({
  score: z.number(),
  content: z.string(),
  signalType: z.string(),
  agentId: z.string(),
  category: z.string().nullable(),
  timestamp: z.string(),
});

export const memoryRecentItemSchema = z.object({
  id: z.union([z.string(), z.number()]),
  title: z.string(),
  url: z.string().nullable(),
  source: z.string().nullable(),
  category: z.string().nullable(),
  subcategory: z.string().nullable(),
  description: z.string().nullable(),
  indexedAt: z.string().nullable(),
});

export const memoryCategorySchema = z.object({
  name: z.string(),
  count: z.number().int().nonnegative(),
});

export const memoryTopicSchema = z.object({
  name: z.string(),
  connections: z.number().int().nonnegative(),
});

export const memorySnapshotSchema = z.object({
  generatedAt: z.string(),
  projects: z.array(projectSnapshotSchema),
  summary: z.object({
    qdrantOnline: z.boolean(),
    neo4jOnline: z.boolean(),
    points: z.number().int().nonnegative(),
    vectors: z.number().int().nonnegative(),
    graphNodes: z.number().int().nonnegative(),
    graphRelationships: z.number().int().nonnegative(),
  }),
  preferences: z.array(memoryPreferenceSchema),
  recentItems: z.array(memoryRecentItemSchema),
  categories: z.array(memoryCategorySchema),
  topTopics: z.array(memoryTopicSchema),
  graphLabels: z.array(z.string()),
});

export const monitoringNodeSnapshotSchema = z.object({
  id: z.string(),
  name: z.string(),
  ip: z.string(),
  role: z.string(),
  cpuUsage: z.number().nullable(),
  memUsed: z.number().nullable(),
  memTotal: z.number().nullable(),
  diskUsed: z.number().nullable(),
  diskTotal: z.number().nullable(),
  networkRxRate: z.number().nullable(),
  networkTxRate: z.number().nullable(),
  uptime: z.number().nullable(),
  load1: z.number().nullable(),
  cpuHistory: z.array(z.number()),
  memHistory: z.array(z.number()),
});

export const monitoringSnapshotSchema = z.object({
  generatedAt: z.string(),
  summary: z.object({
    reachableNodes: z.number().int().nonnegative(),
    totalNodes: z.number().int().nonnegative(),
    averageCpu: z.number().nullable(),
    totalMemUsed: z.number().nullable(),
    totalMemTotal: z.number().nullable(),
    networkRxRate: z.number().nullable(),
    networkTxRate: z.number().nullable(),
  }),
  nodes: z.array(monitoringNodeSnapshotSchema),
  dashboards: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      description: z.string(),
      url: z.string().url(),
    })
  ),
});

export const mediaSessionSchema = z.object({
  friendlyName: z.string().nullable(),
  title: z.string().nullable(),
  state: z.string().nullable(),
  progressPercent: z.number().nullable(),
  transcodeDecision: z.string().nullable(),
  mediaType: z.string().nullable(),
  year: z.string().nullable(),
  thumb: z.string().nullable(),
});

export const mediaQueueItemSchema = z.object({
  id: z.string(),
  title: z.string().nullable(),
  source: z.string(),
  progressPercent: z.number().nullable(),
  status: z.string().nullable(),
  timeLeft: z.string().nullable(),
});

export const mediaCalendarItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  seriesTitle: z.string().nullable(),
  seasonNumber: z.number().nullable(),
  episodeNumber: z.number().nullable(),
  airDateUtc: z.string().nullable(),
  hasFile: z.boolean().nullable(),
});

export const mediaWatchItemSchema = z.object({
  id: z.string(),
  friendlyName: z.string().nullable(),
  title: z.string().nullable(),
  date: z.string().nullable(),
  duration: z.string().nullable(),
  watchedStatus: z.number().nullable(),
});

export const mediaLibrarySchema = z.object({
  total: z.number().nullable(),
  monitored: z.number().nullable(),
  episodes: z.number().nullable(),
  sizeGb: z.number().nullable(),
  hasFile: z.number().nullable().optional(),
});

export const mediaSnapshotSchema = z.object({
  generatedAt: z.string(),
  streamCount: z.number().int().nonnegative(),
  sessions: z.array(mediaSessionSchema),
  downloads: z.array(mediaQueueItemSchema),
  tvUpcoming: z.array(mediaCalendarItemSchema),
  movieUpcoming: z.array(mediaCalendarItemSchema),
  watchHistory: z.array(mediaWatchItemSchema),
  tvLibrary: mediaLibrarySchema.nullable(),
  movieLibrary: mediaLibrarySchema.nullable(),
  stash: z
    .object({
      sceneCount: z.number().nullable(),
      imageCount: z.number().nullable(),
      performerCount: z.number().nullable(),
      studioCount: z.number().nullable(),
      tagCount: z.number().nullable(),
      scenesSize: z.number().nullable(),
      scenesDuration: z.number().nullable(),
    })
    .nullable(),
  launchLinks: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      url: z.string().url(),
    })
  ),
});

export const galleryImageSchema = z.object({
  filename: z.string(),
  subfolder: z.string(),
  type: z.string(),
});

export const galleryHistoryItemSchema = z.object({
  id: z.string(),
  prompt: z.string(),
  outputPrefix: z.string(),
  timestamp: z.number(),
  outputImages: z.array(galleryImageSchema),
});

export const gallerySnapshotSchema = z.object({
  generatedAt: z.string(),
  queueRunning: z.number().int().nonnegative(),
  queuePending: z.number().int().nonnegative(),
  deviceName: z.string().nullable(),
  vramUsedGiB: z.number().nullable(),
  vramTotalGiB: z.number().nullable(),
  items: z.array(galleryHistoryItemSchema),
});

export const homeSetupStepSchema = z.object({
  id: z.string(),
  label: z.string(),
  status: z.enum(["complete", "pending", "blocked"]),
  note: z.string().nullable(),
});

export const homeSnapshotSchema = z.object({
  generatedAt: z.string(),
  online: z.boolean(),
  configured: z.boolean(),
  title: z.string(),
  summary: z.string(),
  setupSteps: z.array(homeSetupStepSchema),
  panels: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      description: z.string(),
      href: z.string(),
    })
  ),
});

export type ServiceSnapshot = z.infer<typeof serviceSnapshotSchema>;
export type ServiceHistorySeries = z.infer<typeof serviceHistorySeriesSchema>;
export type ChartPoint = z.infer<typeof chartPointSchema>;
export type GpuSnapshot = z.infer<typeof gpuSnapshotSchema>;
export type GpuNodeSummary = z.infer<typeof gpuNodeSummarySchema>;
export type OverviewSnapshot = z.infer<typeof overviewSnapshotSchema>;
export type ServicesSnapshot = z.infer<typeof servicesSnapshotSchema>;
export type ServicesHistorySnapshot = z.infer<typeof servicesHistorySnapshotSchema>;
export type GpuSnapshotResponse = z.infer<typeof gpuSnapshotResponseSchema>;
export type GpuHistoryResponse = z.infer<typeof gpuHistoryResponseSchema>;
export type BackendSnapshot = z.infer<typeof backendSnapshotSchema>;
export type ModelInventoryEntry = z.infer<typeof modelInventoryEntrySchema>;
export type ModelsSnapshot = z.infer<typeof modelsSnapshotSchema>;
export type AgentInfo = z.infer<typeof agentInfoSchema>;
export type CommandRightsProfile = z.infer<typeof commandRightsProfileSchema>;
export type CommandHierarchyLayer = z.infer<typeof commandHierarchyLayerSchema>;
export type MetaLaneSelectionRecord = z.infer<typeof metaLaneSelectionRecordSchema>;
export type PolicyClassRecord = z.infer<typeof policyClassRecordSchema>;
export type NavAttentionTier = z.infer<typeof navAttentionTierSchema>;
export type NavAttentionSource = z.infer<typeof navAttentionSourceSchema>;
export type NavAttentionSignal = z.infer<typeof navAttentionSignalSchema>;
export type ModelRoleProfile = z.infer<typeof modelRoleProfileSchema>;
export type WorkloadClassProfile = z.infer<typeof workloadClassProfileSchema>;
export type ModelCandidateSummary = z.infer<typeof modelCandidateSummarySchema>;
export type PromotionCandidateQueue = z.infer<typeof promotionCandidateQueueSchema>;
export type PromotionRecord = z.infer<typeof promotionRecordSchema>;
export type PromotionControls = z.infer<typeof promotionControlsSchema>;
export type RetirementCandidateQueue = z.infer<typeof retirementCandidateQueueSchema>;
export type RetirementRecord = z.infer<typeof retirementRecordSchema>;
export type RetirementControls = z.infer<typeof retirementControlsSchema>;
export type GovernanceContractSummary = z.infer<typeof governanceContractSummarySchema>;
export type GovernedEvalCorpus = z.infer<typeof governedEvalCorpusSchema>;
export type ExperimentEvidence = z.infer<typeof experimentEvidenceSchema>;
export type GovernanceLayers = z.infer<typeof governanceLayersSchema>;
export type CommandDecisionRecord = z.infer<typeof commandDecisionRecordSchema>;
export type PlanPacket = z.infer<typeof planPacketSchema>;
export type RunLineageRecord = z.infer<typeof runLineageRecordSchema>;
export type ArtifactProvenanceRecord = z.infer<typeof artifactProvenanceRecordSchema>;
export type ExecutionRunRecord = z.infer<typeof executionRunRecordSchema>;
export type ScheduledJobRecord = z.infer<typeof scheduledJobRecordSchema>;
export type OperatorStreamEvent = z.infer<typeof operatorStreamEventSchema>;
export type QuotaLeaseProvider = z.infer<typeof quotaLeaseProviderSchema>;
export type QuotaLeaseSummary = z.infer<typeof quotaLeaseSummarySchema>;
export type GovernorLane = z.infer<typeof governorLaneSchema>;
export type CapacityNode = z.infer<typeof capacityNodeSchema>;
export type CapacitySnapshot = z.infer<typeof capacitySnapshotSchema>;
export type GovernorSnapshot = z.infer<typeof governorSnapshotSchema>;
export type SyntheticOperatorTestFlow = z.infer<typeof syntheticOperatorTestFlowSchema>;
export type OperatorTestsSnapshot = z.infer<typeof operatorTestsSnapshotSchema>;
export type OperationsRunbook = z.infer<typeof operationsRunbookSchema>;
export type RestoreReadinessStore = z.infer<typeof restoreReadinessStoreSchema>;
export type LifecycleClass = z.infer<typeof lifecycleClassSchema>;
export type ToolPermissionSubject = z.infer<typeof toolPermissionSubjectSchema>;
export type OperationsReadinessSnapshot = z.infer<typeof operationsReadinessSnapshotSchema>;
export type JudgeVerdict = z.infer<typeof judgeVerdictSchema>;
export type JudgePlaneSnapshot = z.infer<typeof judgePlaneSnapshotSchema>;
export type ExecutionRunsResponse = z.infer<typeof executionRunsResponseSchema>;
export type ScheduledJobsResponse = z.infer<typeof scheduledJobsResponseSchema>;
export type OperatorStreamResponse = z.infer<typeof operatorStreamResponseSchema>;
export type SubscriptionSummaryResponse = z.infer<typeof subscriptionSummaryResponseSchema>;
export type SystemMapSnapshot = z.infer<typeof systemMapSnapshotSchema>;
export type ProvingGroundSnapshot = z.infer<typeof provingGroundSnapshotSchema>;
export type ModelIntelligenceLane = z.infer<typeof modelIntelligenceLaneSchema>;
export type ModelGovernanceSnapshot = z.infer<typeof modelGovernanceSnapshotSchema>;
export type AgentsSnapshot = z.infer<typeof agentsSnapshotSchema>;
export type ProjectSnapshot = z.infer<typeof projectSnapshotSchema>;
export type ProjectsSnapshot = z.infer<typeof projectsSnapshotSchema>;
export type WorkforceTask = z.infer<typeof workforceTaskSchema>;
export type WorkplanTask = z.infer<typeof workplanTaskSchema>;
export type WorkplanSnapshot = z.infer<typeof workplanSnapshotSchema>;
export type WorkforceGoal = z.infer<typeof workforceGoalSchema>;
export type WorkforceNotification = z.infer<typeof workforceNotificationSchema>;
export type WorkforceTrustEntry = z.infer<typeof workforceTrustEntrySchema>;
export type WorkspaceItemSnapshot = z.infer<typeof workspaceItemSnapshotSchema>;
export type WorkspaceSnapshot = z.infer<typeof workspaceSnapshotSchema>;
export type WorkspaceSubscription = z.infer<typeof workspaceSubscriptionSchema>;
export type WorkforceAgentSnapshot = z.infer<typeof workforceAgentSnapshotSchema>;
export type WorkforceScheduleEntry = z.infer<typeof workforceScheduleEntrySchema>;
export type ProjectPosture = z.infer<typeof projectPostureSchema>;
export type WorkforceConvention = z.infer<typeof workforceConventionSchema>;
export type WorkforceImprovementSummary = z.infer<typeof workforceImprovementSummarySchema>;
export type WorkforceSnapshot = z.infer<typeof workforceSnapshotSchema>;
export type ChatStreamEvent = z.infer<typeof chatStreamEventSchema>;
export type TranscriptMessage = z.infer<typeof transcriptMessageSchema>;
export type DirectChatSession = z.infer<typeof directChatSessionSchema>;
export type AgentThread = z.infer<typeof agentThreadSchema>;
export type UiPreferences = z.infer<typeof uiPreferencesSchema>;
export type HistoryActivityItem = z.infer<typeof historyActivityItemSchema>;
export type HistoryConversationItem = z.infer<typeof historyConversationItemSchema>;
export type HistoryOutputItem = z.infer<typeof historyOutputItemSchema>;
export type HistorySnapshot = z.infer<typeof historySnapshotSchema>;
export type IntelligencePattern = z.infer<typeof intelligencePatternSchema>;
export type IntelligenceReport = z.infer<typeof intelligenceReportSchema>;
export type LearningSnapshot = z.infer<typeof learningSnapshotSchema>;
export type IntelligenceSnapshot = z.infer<typeof intelligenceSnapshotSchema>;
export type MemoryPreference = z.infer<typeof memoryPreferenceSchema>;
export type MemoryRecentItem = z.infer<typeof memoryRecentItemSchema>;
export type MemorySnapshot = z.infer<typeof memorySnapshotSchema>;
export type MonitoringNodeSnapshot = z.infer<typeof monitoringNodeSnapshotSchema>;
export type MonitoringSnapshot = z.infer<typeof monitoringSnapshotSchema>;
export type MediaSnapshot = z.infer<typeof mediaSnapshotSchema>;
export type GallerySnapshot = z.infer<typeof gallerySnapshotSchema>;
export type HomeSnapshot = z.infer<typeof homeSnapshotSchema>;
