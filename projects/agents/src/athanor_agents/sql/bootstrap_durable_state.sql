CREATE SCHEMA IF NOT EXISTS control;

CREATE SCHEMA IF NOT EXISTS work;

CREATE SCHEMA IF NOT EXISTS runs;

CREATE SCHEMA IF NOT EXISTS audit;

CREATE SCHEMA IF NOT EXISTS foundry;

CREATE TABLE IF NOT EXISTS control.schema_versions (
    component text PRIMARY KEY,
    version text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS control.system_mode_history (
    mode_entry_id text PRIMARY KEY,
    mode text NOT NULL,
    entered_at timestamptz NOT NULL,
    entered_by text NOT NULL DEFAULT 'operator',
    trigger text NOT NULL DEFAULT '',
    exit_conditions text NOT NULL DEFAULT '',
    notes text NOT NULL DEFAULT '',
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_control_system_mode_history_entered
    ON control.system_mode_history (entered_at DESC);

CREATE INDEX IF NOT EXISTS idx_control_system_mode_history_mode_entered
    ON control.system_mode_history (mode, entered_at DESC);

CREATE TABLE IF NOT EXISTS control.attention_budgets (
    budget_id text PRIMARY KEY,
    scope_type text NOT NULL,
    scope_id text NOT NULL,
    daily_limit integer NOT NULL DEFAULT 0,
    urgent_bypass_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    used_today integer NOT NULL DEFAULT 0,
    status text NOT NULL DEFAULT 'active',
    last_reset_at timestamptz NULL,
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_control_attention_budgets_scope_status
    ON control.attention_budgets (scope_type, scope_id, status);

CREATE INDEX IF NOT EXISTS idx_control_attention_budgets_updated
    ON control.attention_budgets (updated_at DESC);

CREATE TABLE IF NOT EXISTS control.core_change_windows (
    window_id text PRIMARY KEY,
    label text NOT NULL,
    schedule text NOT NULL,
    start_local text NOT NULL DEFAULT '',
    end_local text NOT NULL DEFAULT '',
    allowed_change_classes_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    status text NOT NULL DEFAULT 'live',
    notes text NOT NULL DEFAULT '',
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_control_core_change_windows_status_updated
    ON control.core_change_windows (status, updated_at DESC);

CREATE TABLE IF NOT EXISTS control.agent_value_scores (
    score_id text PRIMARY KEY,
    agent_id text NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    output_value double precision NOT NULL DEFAULT 0,
    approval_efficiency double precision NOT NULL DEFAULT 0,
    success_rate double precision NOT NULL DEFAULT 0,
    attention_penalty double precision NOT NULL DEFAULT 0,
    failure_penalty double precision NOT NULL DEFAULT 0,
    maintenance_penalty double precision NOT NULL DEFAULT 0,
    final_score double precision NOT NULL DEFAULT 0,
    recommended_action text NOT NULL DEFAULT '',
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_control_agent_value_scores_agent_period
    ON control.agent_value_scores (agent_id, period_end DESC);

CREATE TABLE IF NOT EXISTS control.domain_value_scores (
    score_id text PRIMARY KEY,
    domain_id text NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    utility_score double precision NOT NULL DEFAULT 0,
    operator_load double precision NOT NULL DEFAULT 0,
    failure_cost double precision NOT NULL DEFAULT 0,
    maintenance_cost double precision NOT NULL DEFAULT 0,
    final_score double precision NOT NULL DEFAULT 0,
    recommended_action text NOT NULL DEFAULT '',
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_control_domain_value_scores_domain_period
    ON control.domain_value_scores (domain_id, period_end DESC);

CREATE TABLE IF NOT EXISTS work.goals (
    goal_id text PRIMARY KEY,
    goal_text text NOT NULL,
    agent text NOT NULL,
    priority text NOT NULL,
    created_at timestamptz NOT NULL,
    active boolean NOT NULL DEFAULT true,
    deleted_at timestamptz NULL
);

CREATE INDEX IF NOT EXISTS idx_work_goals_active_created_at
    ON work.goals (active, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_work_goals_agent_active
    ON work.goals (agent, active, created_at DESC);

CREATE TABLE IF NOT EXISTS work.operator_todos (
    todo_id text PRIMARY KEY,
    title text NOT NULL,
    description text NOT NULL DEFAULT '',
    category text NOT NULL,
    scope_type text NOT NULL,
    scope_id text NOT NULL,
    priority integer NOT NULL DEFAULT 3,
    status text NOT NULL,
    energy_class text NOT NULL DEFAULT 'focused',
    origin text NOT NULL DEFAULT 'operator',
    created_by text NOT NULL DEFAULT 'operator',
    due_at timestamptz NULL,
    linked_goal_ids_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    linked_inbox_ids_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    completed_at timestamptz NULL
);

CREATE INDEX IF NOT EXISTS idx_work_operator_todos_status_updated
    ON work.operator_todos (status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_work_operator_todos_scope_status
    ON work.operator_todos (scope_type, scope_id, status, updated_at DESC);

CREATE TABLE IF NOT EXISTS work.operator_inbox (
    inbox_id text PRIMARY KEY,
    kind text NOT NULL,
    severity integer NOT NULL DEFAULT 1,
    status text NOT NULL,
    source text NOT NULL,
    title text NOT NULL,
    description text NOT NULL DEFAULT '',
    requires_decision boolean NOT NULL DEFAULT false,
    decision_type text NOT NULL DEFAULT '',
    related_run_id text NOT NULL DEFAULT '',
    related_task_id text NOT NULL DEFAULT '',
    related_project_id text NOT NULL DEFAULT '',
    related_domain_id text NOT NULL DEFAULT '',
    snooze_until timestamptz NULL,
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    resolved_at timestamptz NULL
);

CREATE INDEX IF NOT EXISTS idx_work_operator_inbox_status_created
    ON work.operator_inbox (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_work_operator_inbox_severity_created
    ON work.operator_inbox (severity DESC, created_at DESC);

CREATE TABLE IF NOT EXISTS work.workplan_snapshots (
    plan_id text PRIMARY KEY,
    focus text NOT NULL DEFAULT '',
    generated_at timestamptz NOT NULL,
    task_count integer NOT NULL DEFAULT 0,
    plan_json jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_work_workplan_snapshots_generated
    ON work.workplan_snapshots (generated_at DESC);

CREATE TABLE IF NOT EXISTS work.idea_garden_items (
    idea_id text PRIMARY KEY,
    title text NOT NULL,
    note text NOT NULL DEFAULT '',
    tags_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    source text NOT NULL DEFAULT 'operator',
    confidence double precision NOT NULL DEFAULT 0.5,
    energy_class text NOT NULL DEFAULT 'focused',
    scope_guess text NOT NULL DEFAULT 'global',
    status text NOT NULL DEFAULT 'seed',
    next_review_at timestamptz NULL,
    promoted_project_id text NOT NULL DEFAULT '',
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_work_idea_garden_items_status_updated
    ON work.idea_garden_items (status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_work_idea_garden_items_next_review
    ON work.idea_garden_items (next_review_at ASC NULLS LAST, updated_at DESC);

CREATE TABLE IF NOT EXISTS work.agent_backlog (
    backlog_id text PRIMARY KEY,
    title text NOT NULL,
    prompt text NOT NULL,
    owner_agent text NOT NULL,
    support_agents_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    scope_type text NOT NULL DEFAULT 'global',
    scope_id text NOT NULL DEFAULT 'athanor',
    work_class text NOT NULL DEFAULT 'project_build',
    priority integer NOT NULL DEFAULT 3,
    status text NOT NULL DEFAULT 'captured',
    approval_mode text NOT NULL DEFAULT 'none',
    dispatch_policy text NOT NULL DEFAULT 'planner_eligible',
    preconditions_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    blocking_reason text NOT NULL DEFAULT '',
    linked_goal_ids_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    linked_todo_ids_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    linked_idea_id text NOT NULL DEFAULT '',
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_by text NOT NULL DEFAULT 'operator',
    origin text NOT NULL DEFAULT 'operator',
    ready_at timestamptz NULL,
    scheduled_for timestamptz NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    completed_at timestamptz NULL
);

CREATE INDEX IF NOT EXISTS idx_work_agent_backlog_status_updated
    ON work.agent_backlog (status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_work_agent_backlog_owner_status
    ON work.agent_backlog (owner_agent, status, updated_at DESC);

CREATE TABLE IF NOT EXISTS runs.task_snapshots (
    task_id text PRIMARY KEY,
    agent text NOT NULL,
    prompt text NOT NULL,
    priority text NOT NULL,
    status text NOT NULL,
    source text NOT NULL,
    lane text NOT NULL,
    result text NOT NULL DEFAULT '',
    error text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL,
    started_at timestamptz NULL,
    completed_at timestamptz NULL,
    updated_at timestamptz NOT NULL,
    last_heartbeat timestamptz NULL,
    lease_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    retry_lineage_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    assigned_runtime text NOT NULL DEFAULT '',
    session_id text NOT NULL DEFAULT '',
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    parent_task_id text NOT NULL DEFAULT '',
    retry_count integer NOT NULL DEFAULT 0,
    previous_error text NOT NULL DEFAULT '',
    steps_json jsonb NOT NULL DEFAULT '[]'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_runs_task_snapshots_status_updated
    ON runs.task_snapshots (status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_runs_task_snapshots_agent_status_updated
    ON runs.task_snapshots (agent, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_runs_task_snapshots_lane_updated
    ON runs.task_snapshots (lane, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_runs_task_snapshots_updated
    ON runs.task_snapshots (updated_at DESC);

CREATE TABLE IF NOT EXISTS runs.execution_runs (
    run_id text PRIMARY KEY,
    task_id text NOT NULL DEFAULT '',
    backlog_id text NOT NULL DEFAULT '',
    request_fingerprint text NOT NULL DEFAULT '',
    parent_run_id text NOT NULL DEFAULT '',
    agent_id text NOT NULL,
    workload_class text NOT NULL DEFAULT '',
    provider_lane text NOT NULL DEFAULT '',
    runtime_lane text NOT NULL DEFAULT '',
    policy_class text NOT NULL DEFAULT '',
    status text NOT NULL,
    summary text NOT NULL DEFAULT '',
    artifact_refs_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    completed_at timestamptz NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_execution_runs_status_updated
    ON runs.execution_runs (status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_runs_execution_runs_agent_status_updated
    ON runs.execution_runs (agent_id, status, updated_at DESC);

CREATE TABLE IF NOT EXISTS runs.run_attempts (
    attempt_id text PRIMARY KEY,
    run_id text NOT NULL REFERENCES runs.execution_runs(run_id) ON DELETE CASCADE,
    retry_of_attempt_id text NOT NULL DEFAULT '',
    replay_of_attempt_id text NOT NULL DEFAULT '',
    lease_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    worker_id text NOT NULL DEFAULT '',
    runtime_host text NOT NULL DEFAULT '',
    started_at timestamptz NULL,
    heartbeat_at timestamptz NULL,
    completed_at timestamptz NULL,
    status text NOT NULL,
    error text NOT NULL DEFAULT '',
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_run_attempts_run_created
    ON runs.run_attempts (run_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_runs_run_attempts_status_heartbeat
    ON runs.run_attempts (status, heartbeat_at DESC NULLS LAST);

CREATE TABLE IF NOT EXISTS runs.run_steps (
    step_id text PRIMARY KEY,
    attempt_id text NOT NULL REFERENCES runs.run_attempts(attempt_id) ON DELETE CASCADE,
    run_id text NOT NULL REFERENCES runs.execution_runs(run_id) ON DELETE CASCADE,
    step_key text NOT NULL,
    kind text NOT NULL,
    seq integer NOT NULL DEFAULT 0,
    status text NOT NULL DEFAULT 'completed',
    input_ref text NOT NULL DEFAULT '',
    output_ref text NOT NULL DEFAULT '',
    checkpoint_ref text NOT NULL DEFAULT '',
    detail_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    started_at timestamptz NULL,
    completed_at timestamptz NULL,
    created_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_run_steps_attempt_seq
    ON runs.run_steps (attempt_id, seq ASC);

CREATE INDEX IF NOT EXISTS idx_runs_run_steps_run_created
    ON runs.run_steps (run_id, created_at DESC);

CREATE TABLE IF NOT EXISTS audit.approval_requests (
    approval_id text PRIMARY KEY,
    related_run_id text NOT NULL DEFAULT '',
    related_attempt_id text NOT NULL DEFAULT '',
    related_task_id text NOT NULL DEFAULT '',
    requested_action text NOT NULL,
    privilege_class text NOT NULL,
    reason text NOT NULL DEFAULT '',
    status text NOT NULL,
    requested_at timestamptz NOT NULL,
    decided_at timestamptz NULL,
    decided_by text NOT NULL DEFAULT '',
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_audit_approval_requests_status_requested
    ON audit.approval_requests (status, requested_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_approval_requests_run_status
    ON audit.approval_requests (related_run_id, status, requested_at DESC);

CREATE TABLE IF NOT EXISTS foundry.project_packets (
    project_id text PRIMARY KEY,
    name text NOT NULL,
    stage text NOT NULL,
    template text NOT NULL,
    project_class text NOT NULL,
    visibility text NOT NULL,
    sensitivity text NOT NULL,
    runtime_target text NOT NULL,
    deploy_target text NOT NULL,
    workspace_root text NOT NULL,
    primary_route text NOT NULL DEFAULT '/projects',
    owner_domain text NOT NULL DEFAULT 'product_foundry',
    operators_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    agents_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    acceptance_bundle_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    rollback_contract text NOT NULL DEFAULT '',
    maintenance_cadence text NOT NULL DEFAULT '',
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_foundry_project_packets_stage_updated
    ON foundry.project_packets (stage, updated_at DESC);

CREATE TABLE IF NOT EXISTS foundry.architecture_packets (
    project_id text PRIMARY KEY REFERENCES foundry.project_packets(project_id) ON DELETE CASCADE,
    service_shape_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    data_contracts_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    auth_boundary_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    deploy_shape_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    risk_notes_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    test_plan_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    rollback_notes_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    approved_at timestamptz NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS foundry.execution_slices (
    slice_id text PRIMARY KEY,
    project_id text NOT NULL REFERENCES foundry.project_packets(project_id) ON DELETE CASCADE,
    owner_agent text NOT NULL,
    lane text NOT NULL,
    base_sha text NOT NULL DEFAULT '',
    worktree_path text NOT NULL DEFAULT '',
    acceptance_target text NOT NULL DEFAULT '',
    status text NOT NULL DEFAULT 'planned',
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_foundry_execution_slices_project_updated
    ON foundry.execution_slices (project_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS foundry.foundry_runs (
    foundry_run_id text PRIMARY KEY,
    project_id text NOT NULL REFERENCES foundry.project_packets(project_id) ON DELETE CASCADE,
    slice_id text NOT NULL DEFAULT '',
    execution_run_id text NOT NULL DEFAULT '',
    status text NOT NULL DEFAULT 'queued',
    summary text NOT NULL DEFAULT '',
    artifact_refs_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    review_refs_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    completed_at timestamptz NULL
);

CREATE INDEX IF NOT EXISTS idx_foundry_runs_project_updated
    ON foundry.foundry_runs (project_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS foundry.deploy_candidates (
    candidate_id text PRIMARY KEY,
    project_id text NOT NULL REFERENCES foundry.project_packets(project_id) ON DELETE CASCADE,
    channel text NOT NULL,
    artifact_refs_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    env_contract_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    smoke_results_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    rollback_target_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    promotion_status text NOT NULL DEFAULT 'pending',
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    promoted_at timestamptz NULL
);

CREATE INDEX IF NOT EXISTS idx_foundry_deploy_candidates_project_updated
    ON foundry.deploy_candidates (project_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS foundry.maintenance_runs (
    maintenance_id text PRIMARY KEY,
    project_id text NOT NULL REFERENCES foundry.project_packets(project_id) ON DELETE CASCADE,
    kind text NOT NULL,
    trigger text NOT NULL,
    status text NOT NULL DEFAULT 'queued',
    evidence_ref text NOT NULL DEFAULT '',
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    completed_at timestamptz NULL
);

CREATE INDEX IF NOT EXISTS idx_foundry_maintenance_runs_project_updated
    ON foundry.maintenance_runs (project_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS foundry.rollback_events (
    rollback_event_id text PRIMARY KEY,
    project_id text NOT NULL REFERENCES foundry.project_packets(project_id) ON DELETE CASCADE,
    candidate_id text NOT NULL DEFAULT '',
    reason text NOT NULL DEFAULT '',
    rollback_target_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    status text NOT NULL DEFAULT 'recorded',
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_foundry_rollback_events_project_created
    ON foundry.rollback_events (project_id, created_at DESC);

CREATE TABLE IF NOT EXISTS control.bootstrap_programs (
    program_id text PRIMARY KEY,
    label text NOT NULL,
    family_order_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    objective text NOT NULL DEFAULT '',
    phase_scope text NOT NULL DEFAULT '',
    status text NOT NULL DEFAULT 'active',
    validator_bundle_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    max_parallel_slices integer NOT NULL DEFAULT 1,
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS control.bootstrap_slices (
    slice_id text PRIMARY KEY,
    program_id text NOT NULL REFERENCES control.bootstrap_programs(program_id) ON DELETE CASCADE,
    family text NOT NULL,
    objective text NOT NULL DEFAULT '',
    status text NOT NULL DEFAULT 'queued',
    host_id text NOT NULL DEFAULT '',
    current_ref text NOT NULL DEFAULT '',
    worktree_path text NOT NULL DEFAULT '',
    files_touched_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    validation_status text NOT NULL DEFAULT 'pending',
    open_risks_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    next_step text NOT NULL DEFAULT '',
    stop_reason text NOT NULL DEFAULT '',
    resume_instructions text NOT NULL DEFAULT '',
    depth_level integer NOT NULL DEFAULT 1,
    priority integer NOT NULL DEFAULT 3,
    phase_scope text NOT NULL DEFAULT '',
    continuation_mode text NOT NULL DEFAULT 'external_bootstrap',
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    claimed_at timestamptz NULL,
    completed_at timestamptz NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_control_bootstrap_slices_program_status
    ON control.bootstrap_slices (program_id, status, priority, created_at);

CREATE TABLE IF NOT EXISTS control.bootstrap_handoffs (
    handoff_id text PRIMARY KEY,
    program_id text NOT NULL DEFAULT '',
    slice_id text NOT NULL DEFAULT '',
    family text NOT NULL DEFAULT '',
    from_host text NOT NULL DEFAULT '',
    to_host text NOT NULL DEFAULT '',
    objective text NOT NULL DEFAULT '',
    current_ref text NOT NULL DEFAULT '',
    worktree_path text NOT NULL DEFAULT '',
    files_touched_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    validation_status text NOT NULL DEFAULT 'pending',
    open_risks_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    next_step text NOT NULL DEFAULT '',
    stop_reason text NOT NULL DEFAULT '',
    resume_instructions text NOT NULL DEFAULT '',
    status text NOT NULL DEFAULT 'recorded',
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    completed_at timestamptz NULL
);

CREATE INDEX IF NOT EXISTS idx_control_bootstrap_handoffs_slice_created
    ON control.bootstrap_handoffs (slice_id, created_at DESC);

CREATE TABLE IF NOT EXISTS control.bootstrap_integrations (
    integration_id text PRIMARY KEY,
    program_id text NOT NULL DEFAULT '',
    slice_id text NOT NULL DEFAULT '',
    family text NOT NULL DEFAULT '',
    method text NOT NULL DEFAULT 'squash_commit',
    source_ref text NOT NULL DEFAULT '',
    target_ref text NOT NULL DEFAULT 'main',
    patch_path text NOT NULL DEFAULT '',
    queue_path text NOT NULL DEFAULT '',
    status text NOT NULL DEFAULT 'queued',
    priority integer NOT NULL DEFAULT 3,
    validation_summary_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    blocker_id text NOT NULL DEFAULT '',
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    completed_at timestamptz NULL
);

CREATE INDEX IF NOT EXISTS idx_control_bootstrap_integrations_status_created
    ON control.bootstrap_integrations (status, priority, created_at);

CREATE TABLE IF NOT EXISTS control.bootstrap_blockers (
    blocker_id text PRIMARY KEY,
    program_id text NOT NULL DEFAULT '',
    slice_id text NOT NULL DEFAULT '',
    family text NOT NULL DEFAULT '',
    blocker_class text NOT NULL DEFAULT 'implementation_failure',
    reason text NOT NULL DEFAULT '',
    approval_required boolean NOT NULL DEFAULT false,
    inbox_id text NOT NULL DEFAULT '',
    retry_at timestamptz NULL,
    status text NOT NULL DEFAULT 'open',
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    resolved_at timestamptz NULL
);

CREATE INDEX IF NOT EXISTS idx_control_bootstrap_blockers_status_retry
    ON control.bootstrap_blockers (status, retry_at, created_at);

CREATE TABLE IF NOT EXISTS control.bootstrap_host_state (
    host_id text PRIMARY KEY,
    status text NOT NULL DEFAULT 'available',
    cooldown_until timestamptz NULL,
    last_heartbeat timestamptz NULL,
    active_slice_id text NOT NULL DEFAULT '',
    last_reason text NOT NULL DEFAULT '',
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamptz NOT NULL
);

INSERT INTO control.schema_versions (component, version)
VALUES ('agents_durable_state', '2026-03-31.6')
ON CONFLICT (component) DO UPDATE
SET
    version = EXCLUDED.version,
    applied_at = now();
