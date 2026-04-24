import os from "node:os";
import path from "node:path";
import { mkdtemp, rm } from "node:fs/promises";
import { afterEach, describe, expect, it, vi } from "vitest";
import { __resetBuilderStoreForTests, createBuilderSession } from "./builder-store";
import {
  buildExecutionJobProjections,
  buildExecutionProgramProjections,
  buildExecutionResultProjections,
  buildExecutionReviewProjections,
  buildExecutionSessionProjections,
  buildExecutiveKernelSummary,
  loadExecutionJobs,
  loadExecutionResults,
  loadExecutionSession,
  loadExecutionPrograms,
  loadExecutionSessions,
} from "./executive-kernel";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("executive kernel summary", () => {
  it("projects the builder family, recurring programs, and reserve posture into one front-door summary", () => {
    const summary = buildExecutiveKernelSummary({
      builderFrontDoor: {
        available: true,
        degraded: false,
        detail: null,
        updated_at: "2026-04-17T23:10:00.000Z",
        session_count: 2,
        active_count: 1,
        pending_approval_count: 1,
        recent_artifact_count: 3,
        shared_pressure: {
          pending_review_count: 1,
          actionable_result_count: 0,
          current_session_pending_review_count: 1,
          current_session_actionable_result_count: 0,
          current_session_status: "review_required",
          current_session_needs_sync: false,
        },
        current_session: {
          id: "builder-1",
          title: "Implement the bounded Codex route",
          status: "waiting_approval",
          primary_adapter: "codex",
          current_route: "Codex direct implementation",
          verification_status: "planned",
          pending_approval_count: 1,
          artifact_count: 3,
          resumable_handle: null,
          shadow_mode: false,
          fallback_state: null,
          updated_at: "2026-04-17T23:10:00.000Z",
        },
        sessions: [],
      },
      steadyState: {
        generatedAt: "2026-04-17T23:10:00.000Z",
        closureState: "repo_safe_complete",
        operatorMode: "steady_state_monitoring",
        interventionLabel: "No action needed",
        interventionLevel: "no_action_needed",
        interventionSummary: "Steady-state governance is clean.",
        needsYou: false,
        nextOperatorAction: "Keep the review surface open for approvals only.",
        queueDispatchable: 3,
        queueTotal: 5,
        suppressedTaskCount: 1,
        runtimePacketCount: 0,
        currentWork: {
          taskId: "builder:codex:direct_cli",
          taskTitle: "Implement the bounded Codex route",
          providerLabel: "OpenAI Codex",
          laneFamily: "builder",
        },
        nextUp: {
          taskId: "workstream:dispatch-and-work-economy-closure",
          taskTitle: "Dispatch and Work-Economy Closure",
          providerLabel: "Athanor Local",
          laneFamily: "maintenance",
        },
        sourceKind: "workspace_report",
        sourcePath: "/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json",
      },
      governor: {
        generated_at: "2026-04-17T23:10:00.000Z",
        status: "healthy",
        global_mode: "steady_state",
        degraded_mode: "off",
        reason: "Nominal",
        updated_at: "2026-04-17T23:10:00.000Z",
        updated_by: "tests",
        lanes: [],
        capacity: {
          generated_at: "2026-04-17T23:10:00.000Z",
          posture: "open_harvest_window",
          queue: {
            posture: "open_harvest_window",
            pending: 0,
            running: 1,
            max_concurrent: 4,
            failed: 0,
          },
          workspace: {
            broadcast_items: 0,
            capacity: 7,
            utilization: 0.2,
          },
          scheduler: {
            running: true,
            enabled_count: 5,
          },
          local_compute: {
            sample_posture: "scheduler_projection_backed",
            scheduler_slot_count: 5,
            harvestable_scheduler_slot_count: 2,
            idle_harvest_slots_open: true,
            open_harvest_slots: [
              {
                id: "F:TP4",
                zone_id: "F",
                harvest_intent: "primary_sovereign_bulk",
                harvestable_gpu_count: 4,
                node_ids: ["foundry"],
              },
            ],
            scheduler_queue_depth: 0,
            scheduler_source: "reports/truth-inventory/gpu-scheduler-baseline-eval.json",
            scheduler_observed_at: "2026-04-17T23:10:00.000Z",
          },
          provider_reserve: {
            posture: "balanced",
            constrained_count: 1,
          },
          active_time_windows: [],
          nodes: [],
          recommendations: [],
        },
        presence: {
          state: "at_desk",
          label: "At desk",
          automation_posture: "normal",
          notification_posture: "normal",
          approval_posture: "operator_gated",
          updated_at: "2026-04-17T23:10:00.000Z",
          updated_by: "tests",
          mode: "auto",
          configured_state: "at_desk",
          configured_label: "At desk",
          signal_state: "present",
          signal_source: "tests",
          signal_updated_at: "2026-04-17T23:10:00.000Z",
          signal_updated_by: "tests",
          signal_fresh: true,
          signal_age_seconds: 0,
          effective_reason: "fixture",
        },
        release_tier: {
          state: "shadow",
          available_tiers: ["shadow", "canary"],
          status: "healthy",
          updated_at: "2026-04-17T23:10:00.000Z",
          updated_by: "tests",
        },
        command_rights_version: "tests",
        control_stack: [],
      },
      scheduledJobs: [
        {
          id: "daily-digest",
          job_family: "maintenance",
          title: "Daily Digest",
          cadence: "daily",
          trigger_mode: "scheduler",
          last_run: "2026-04-17T10:00:00.000Z",
          next_run: "2026-04-18T10:00:00.000Z",
          current_state: "running",
          last_outcome: "success",
          owner_agent: "scheduler",
          deep_link: "/runs?job=daily-digest",
        },
        {
          id: "workplan-refill",
          job_family: "maintenance",
          title: "Workplan Refill",
          cadence: "hourly",
          trigger_mode: "scheduler",
          last_run: "2026-04-17T21:00:00.000Z",
          next_run: "2026-04-17T22:00:00.000Z",
          current_state: "scheduled",
          last_outcome: "success",
          owner_agent: "scheduler",
          deep_link: "/runs?job=workplan-refill",
        },
        {
          id: "creative-cascade",
          job_family: "creative",
          title: "Creative Cascade",
          cadence: "nightly",
          trigger_mode: "scheduler",
          last_run: "2026-04-16T04:00:00.000Z",
          next_run: "2026-04-18T04:00:00.000Z",
          current_state: "paused",
          last_outcome: "success",
          owner_agent: "creative-agent",
          deep_link: "/runs?job=creative-cascade",
          paused: true,
        },
      ],
      bootstrapPrograms: [
        {
          id: "launch-readiness-bootstrap",
          label: "Launch readiness bootstrap",
          objective: "Drive the external bootstrap lane to takeover readiness.",
          phase_scope: "software_core_phase_1",
          status: "waiting_approval",
          current_family: "durable_persistence_activation",
          next_slice_id: "persist-04-activation-cutover",
          recommended_host_id: "",
          waiting_on_approval_family: "durable_persistence_activation",
          waiting_on_approval_slice_id: "persist-04-activation-cutover",
          pending_integrations: 0,
          slice_counts: {
            total: 30,
            queued: 2,
            active: 0,
            blocked: 0,
            completed: 28,
          },
          created_at: "2026-04-16T20:00:00.000Z",
          updated_at: "2026-04-17T23:15:00.000Z",
        },
      ],
      registry: {
        version: "2026-04-17.1",
        kernel_mode: "hybrid_sessions_plus_programs",
        first_live_family: "builder",
        dispatch_order: [
          "privacy_gate",
          "execution_family",
          "reserve_class",
          "adapter",
          "verification_and_recovery",
        ],
        dispatch_defaults: {
          implementation_lane: "codex_cloudsafe",
          audit_lane: "gemini_audit_cloudsafe",
          mechanic_lane: "aider_repo_mechanic",
          github_lane: "github_async_delegate",
          bulk_lane: "sovereign_bulk",
        },
      },
      capacityTelemetry: {
        capacity_summary: {
          harvestable_scheduler_slot_count: 2,
        },
        gpu_samples: [
          { gpu_id: "foundry-rtx4090", protected_reserve: true },
          { gpu_id: "workshop-rtx5090", protected_reserve: true },
          { gpu_id: "foundry-rtx5070ti-a", protected_reserve: false },
        ],
      },
      capabilitySnapshot: {
        version: "2026-04-17.1",
        generated_at: "2026-04-17T23:10:00.000Z",
        source_of_truth: "reports/truth-inventory/capability-intelligence.json",
        providers: [
          {
            subject_id: "openai_codex",
            subject_kind: "provider",
            task_class: "multi_file_implementation",
            reserve_class: "premium_async",
            capability_score: 91,
            demotion_state: "healthy",
          },
          {
            subject_id: "google_gemini",
            subject_kind: "provider",
            task_class: "repo_wide_audit",
            reserve_class: "burn_early_audit",
            capability_score: 89,
            demotion_state: "healthy",
          },
          {
            subject_id: "moonshot_kimi",
            subject_kind: "provider",
            task_class: "search_heavy_planning",
            reserve_class: "targeted_alt_reasoning",
            capability_score: 71,
            demotion_state: "degraded",
          },
        ],
        local_endpoints: [
          {
            subject_id: "foundry-coder-lane",
            subject_kind: "local_endpoint",
            task_class: "multi_file_implementation",
            reserve_class: "interactive_local_reserve",
            capability_score: 95,
            demotion_state: "healthy",
          },
        ],
        degraded_subjects: [
          {
            subject_id: "moonshot_kimi",
            subject_kind: "provider",
            task_class: "search_heavy_planning",
            demotion_state: "degraded",
          },
        ],
      },
      frontDoorUrl: "https://athanor.local/",
      updatedAt: "2026-04-17T23:10:00.000Z",
    });

    expect(summary.kernel_mode).toBe("hybrid_sessions_plus_programs");
    expect(summary.first_live_family).toBe("builder");
    expect(summary.active_family).toBe("builder");
    expect(summary.active_session_count).toBe(1);
    expect(summary.active_program_count).toBe(3);
    expect(summary.running_program_count).toBe(1);
    expect(summary.local_protected_reserve_count).toBe(2);
    expect(summary.local_harvestable_slot_count).toBe(2);
    expect(summary.open_harvest_slot_count).toBe(1);
    expect(summary.provider_reserve_posture).toBe("balanced");
    expect(summary.constrained_provider_count).toBe(1);
    expect(summary.dispatch.implementation_lane).toBe("codex_cloudsafe");
    expect(summary.dispatch.bulk_lane).toBe("sovereign_bulk");
    expect(summary.current_session?.family).toBe("builder");
    expect(summary.capability_posture.implementation?.subject_id).toBe("openai_codex");
    expect(summary.capability_posture.audit?.subject_id).toBe("google_gemini");
    expect(summary.capability_posture.local_endpoint?.subject_id).toBe("foundry-coder-lane");
    expect(summary.capability_posture.degraded_subject_count).toBe(1);
    expect(summary.current_programs.map((program) => program.id)).toEqual([
      "launch-readiness-bootstrap",
      "daily-digest",
      "workplan-refill",
    ]);
  });

  it("builds shared execution session and program projections from builder and scheduler state", () => {
    const sessions = buildExecutionSessionProjections(
      {
        available: true,
        degraded: false,
        detail: null,
        updated_at: "2026-04-17T23:10:00.000Z",
        session_count: 2,
        active_count: 1,
        pending_approval_count: 1,
        recent_artifact_count: 3,
        shared_pressure: {
          pending_review_count: 1,
          actionable_result_count: 0,
          current_session_pending_review_count: 1,
          current_session_actionable_result_count: 0,
          current_session_status: "review_required",
          current_session_needs_sync: false,
        },
        current_session: {
          id: "builder-1",
          title: "Implement the bounded Codex route",
          status: "waiting_approval",
          primary_adapter: "codex",
          current_route: "Codex direct implementation",
          verification_status: "planned",
          pending_approval_count: 1,
          artifact_count: 3,
          resumable_handle: null,
          shadow_mode: false,
          fallback_state: "approval_pending",
          updated_at: "2026-04-17T23:10:00.000Z",
        },
        sessions: [
          {
            id: "builder-1",
            title: "Implement the bounded Codex route",
            status: "waiting_approval",
            primary_adapter: "codex",
            current_route: "Codex direct implementation",
            verification_status: "planned",
            pending_approval_count: 1,
            artifact_count: 3,
            resumable_handle: null,
            shadow_mode: false,
            fallback_state: "approval_pending",
            updated_at: "2026-04-17T23:10:00.000Z",
          },
          {
            id: "builder-2",
            title: "Repair verification fallback",
            status: "failed",
            primary_adapter: "claude_code",
            current_route: "Claude Code escalator",
            verification_status: "failed",
            pending_approval_count: 0,
            artifact_count: 1,
            resumable_handle: "resume-2",
            shadow_mode: false,
            fallback_state: "resume_required",
            updated_at: "2026-04-17T21:00:00.000Z",
          },
        ],
      },
      [
        {
          id: "persist-04-activation-cutover",
          program_id: "launch-readiness-bootstrap",
          family: "durable_persistence_activation",
          objective: "Cut configured Postgres runtimes over from fallback memory to durable persistence.",
          status: "waiting_approval",
          host_id: "",
          current_ref: "",
          worktree_path: "",
          files_touched: [],
          validation_status: "pending",
          open_risks: [],
          next_step: "Await DB schema/runtime approval packet execution.",
          stop_reason: "",
          resume_instructions: "",
          depth_level: 2,
          priority: 2,
          phase_scope: "software_core_phase_1",
          continuation_mode: "external_bootstrap",
          metadata: { blocking_packet_id: "db_schema_change" },
          catalog_slice_id: "persist-04",
          family_seed_slice_id: "persist-seed",
          execution_mode: "repo_worktree",
          completion_evidence_paths: [],
          blocking_packet_id: "db_schema_change",
          claimed_at: "",
          completed_at: "",
          created_at: "2026-04-16T20:00:00.000Z",
          updated_at: "2026-04-17T23:15:00.000Z",
        },
      ],
    );

    const programs = buildExecutionProgramProjections(
      [
        {
          id: "daily-digest",
          job_family: "maintenance",
          title: "Daily Digest",
          cadence: "daily",
          trigger_mode: "scheduler",
          last_run: "2026-04-17T10:00:00.000Z",
          next_run: "2026-04-18T10:00:00.000Z",
          current_state: "running",
          last_outcome: "success",
          owner_agent: "scheduler",
          deep_link: "/runs?job=daily-digest",
        },
        {
          id: "creative-cascade",
          job_family: "creative",
          title: "Creative Cascade",
          cadence: "nightly",
          trigger_mode: "scheduler",
          last_run: "2026-04-16T04:00:00.000Z",
          next_run: "2026-04-18T04:00:00.000Z",
          current_state: "paused",
          last_outcome: "success",
          owner_agent: "creative-agent",
          deep_link: "/runs?job=creative-cascade",
          paused: true,
        },
      ],
      [
        {
          id: "launch-readiness-bootstrap",
          label: "Launch readiness bootstrap",
          objective: "Drive the external bootstrap lane to takeover readiness.",
          phase_scope: "software_core_phase_1",
          status: "waiting_approval",
          current_family: "durable_persistence_activation",
          next_slice_id: "persist-04-activation-cutover",
          recommended_host_id: "",
          waiting_on_approval_family: "durable_persistence_activation",
          waiting_on_approval_slice_id: "persist-04-activation-cutover",
          next_action: {
            kind: "approval_required",
            family: "durable_persistence_activation",
            slice_id: "persist-04-activation-cutover",
          },
          pending_integrations: 0,
          slice_counts: {
            total: 30,
            queued: 2,
            active: 0,
            blocked: 0,
            completed: 28,
          },
          created_at: "2026-04-16T20:00:00.000Z",
          updated_at: "2026-04-17T23:15:00.000Z",
        },
      ],
    );

    expect(sessions).toHaveLength(3);
    expect(sessions[0]).toMatchObject({
      id: "persist-04-activation-cutover",
      family: "bootstrap_takeover",
      source: "bootstrap_slice",
      status: "waiting_approval",
      primary_adapter: "repo_worktree",
      current_route: "durable_persistence_activation",
    });
    expect(sessions[1]).toMatchObject({
      id: "builder-1",
      family: "builder",
      source: "builder_front_door",
      status: "waiting_approval",
      primary_adapter: "codex",
    });
    expect(programs).toHaveLength(3);
    expect(programs[0]).toMatchObject({
      id: "launch-readiness-bootstrap",
      family: "bootstrap_takeover",
      source: "bootstrap_program",
      current_state: "waiting_approval",
      owner_agent: "bootstrap_supervisor",
      deep_link: "/bootstrap?program=launch-readiness-bootstrap",
    });
    expect(programs[1]).toMatchObject({
      id: "daily-digest",
      family: "maintenance",
      source: "scheduled_job",
      current_state: "running",
    });
  });

  it("loads bootstrap programs into the shared execution program feed", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);

      if (url.includes("/v1/tasks/scheduled?limit=48")) {
        return new Response(
          JSON.stringify({
            jobs: [
              {
                id: "daily-digest",
                job_family: "maintenance",
                title: "Daily Digest",
                cadence: "daily",
                trigger_mode: "scheduler",
                last_run: "2026-04-17T10:00:00.000Z",
                next_run: "2026-04-18T10:00:00.000Z",
                current_state: "running",
                last_outcome: "success",
                owner_agent: "scheduler",
                deep_link: "/runs?job=daily-digest",
              },
            ],
          }),
          { status: 200 },
        );
      }

      if (url.includes("/v1/bootstrap/programs")) {
        return new Response(
          JSON.stringify({
            programs: [
              {
                id: "launch-readiness-bootstrap",
                label: "Launch readiness bootstrap",
                objective: "Drive the external bootstrap lane to takeover readiness.",
                phase_scope: "software_core_phase_1",
                status: "waiting_approval",
                current_family: "durable_persistence_activation",
                next_slice_id: "persist-04-activation-cutover",
                recommended_host_id: "",
                waiting_on_approval_family: "durable_persistence_activation",
                waiting_on_approval_slice_id: "persist-04-activation-cutover",
                next_action: {
                  kind: "approval_required",
                  family: "durable_persistence_activation",
                  slice_id: "persist-04-activation-cutover",
                },
                pending_integrations: 0,
                slice_counts: {
                  total: 30,
                  queued: 2,
                  active: 0,
                  blocked: 0,
                  completed: 28,
                },
                created_at: "2026-04-16T20:00:00.000Z",
                updated_at: "2026-04-17T23:15:00.000Z",
              },
            ],
            count: 1,
            status: {},
            takeover: {},
          }),
          { status: 200 },
        );
      }

      return new Response("not found", { status: 404 });
    });

    const programs = await loadExecutionPrograms({});
    const bootstrapPrograms = await loadExecutionPrograms({ family: "bootstrap_takeover" });

    expect(programs.map((program) => program.id)).toEqual([
      "launch-readiness-bootstrap",
      "daily-digest",
    ]);
    expect(programs[0]).toMatchObject({
      family: "bootstrap_takeover",
      source: "bootstrap_program",
      current_state: "waiting_approval",
    });
    expect(bootstrapPrograms.map((program) => program.id)).toEqual(["launch-readiness-bootstrap"]);
  });

  it("loads bootstrap slices into the shared execution session feed and detail lookup", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);

      if (url.includes("/v1/bootstrap/slices?limit=500")) {
        return new Response(
          JSON.stringify({
            slices: [
              {
                id: "persist-04-activation-cutover",
                program_id: "launch-readiness-bootstrap",
                family: "durable_persistence_activation",
                objective: "Cut configured Postgres runtimes over from fallback memory to durable persistence.",
                status: "waiting_approval",
                host_id: "",
                current_ref: "",
                worktree_path: "",
                files_touched: [],
                validation_status: "pending",
                open_risks: [],
                next_step: "Await DB schema/runtime approval packet execution.",
                stop_reason: "",
                resume_instructions: "",
                depth_level: 2,
                priority: 2,
                phase_scope: "software_core_phase_1",
                continuation_mode: "external_bootstrap",
                metadata: { blocking_packet_id: "db_schema_change" },
                catalog_slice_id: "persist-04",
                family_seed_slice_id: "persist-seed",
                execution_mode: "repo_worktree",
                completion_evidence_paths: [],
                blocking_packet_id: "db_schema_change",
                claimed_at: "",
                completed_at: "",
                created_at: "2026-04-16T20:00:00.000Z",
                updated_at: "2026-04-17T23:15:00.000Z",
              },
            ],
            count: 1,
          }),
          { status: 200 },
        );
      }

      return new Response("not found", { status: 404 });
    });

    const sessions = await loadExecutionSessions({ family: "bootstrap_takeover" });
    const session = await loadExecutionSession("persist-04-activation-cutover");

    expect(sessions).toHaveLength(1);
    expect(sessions[0]).toMatchObject({
      id: "persist-04-activation-cutover",
      family: "bootstrap_takeover",
      source: "bootstrap_slice",
      status: "waiting_approval",
      current_route: "durable_persistence_activation",
    });
    expect(session).toMatchObject({
      id: "persist-04-activation-cutover",
      family: "bootstrap_takeover",
      source: "bootstrap_slice",
      pending_approval_count: 1,
    });
  });

  it("builds shared execution job projections from builder attempts", () => {
    const jobs = buildExecutionJobProjections(
      [
        {
          id: "builder-run-builder-1",
          task_id: "builder-1",
          backlog_id: "",
          agent_id: "codex",
          workload_class: "multi_file_implementation",
          provider_lane: "codex",
          runtime_lane: "direct_cli",
          policy_class: "private_but_cloud_allowed",
          status: "waiting_approval",
          summary: "Queued for the first live route.",
          created_at: 100,
          updated_at: 120,
          completed_at: 0,
          step_count: 4,
          approval_pending: true,
          latest_attempt: {
            id: "builder-attempt-builder-1",
            runtime_host: "builder-front-door",
            status: "waiting_approval",
            heartbeat_at: 120,
          },
          approvals: [{ id: "approval-1", status: "pending", privilege_class: "operator" }],
          metadata: {
            builder_session_id: "builder-1",
          },
        },
      ],
      [
        {
          id: "persist-04-activation-cutover",
          program_id: "launch-readiness-bootstrap",
          family: "durable_persistence_activation",
          objective: "Cut configured Postgres runtimes over from fallback memory to durable persistence.",
          status: "waiting_approval",
          host_id: "",
          current_ref: "",
          worktree_path: "C:\\Athanor_worktrees\\durable_persistence_activation\\persist-04-activation-cutover",
          files_touched: [],
          validation_status: "pending",
          open_risks: [],
          next_step: "Await DB schema/runtime approval packet execution.",
          stop_reason: "",
          resume_instructions: "",
          depth_level: 2,
          priority: 2,
          phase_scope: "software_core_phase_1",
          continuation_mode: "external_bootstrap",
          metadata: { blocking_packet_id: "db_schema_change" },
          catalog_slice_id: "persist-04",
          family_seed_slice_id: "persist-seed",
          execution_mode: "repo_worktree",
          completion_evidence_paths: [],
          blocking_packet_id: "db_schema_change",
          claimed_at: "",
          completed_at: "",
          created_at: "2026-04-16T20:00:00.000Z",
          updated_at: "2026-04-17T23:15:00.000Z",
        },
      ],
    );

    expect(jobs).toHaveLength(2);
    expect(jobs[0]).toMatchObject({
      id: "persist-04-activation-cutover",
      family: "bootstrap_takeover",
      source: "bootstrap_slice",
      owner_kind: "program",
      owner_id: "launch-readiness-bootstrap",
      run_id: "persist-04-activation-cutover",
      status: "waiting_approval",
      adapter_id: "repo_worktree",
      approval_pending: true,
    });
    expect(jobs[1]).toMatchObject({
      id: "builder-attempt-builder-1",
      family: "builder",
      source: "builder_front_door",
      owner_kind: "session",
      owner_id: "builder-1",
      run_id: "builder-run-builder-1",
      status: "waiting_approval",
      adapter_id: "codex",
      runtime_host: "builder-front-door",
      approval_pending: true,
    });
  });

  it("builds shared execution review projections from builder and bootstrap approvals", () => {
    const reviews = buildExecutionReviewProjections(
      [
        {
          id: "builder-approval-1",
          related_run_id: "builder-run-builder-1",
          related_task_id: "builder-1",
          requested_action: "start_builder_execution",
          privilege_class: "admin",
          reason: "Approve the builder session.",
          status: "pending",
          requested_at: 120,
          task_prompt: "Implement the bounded Codex route.",
          task_agent_id: "codex",
          task_priority: "normal",
          task_status: "waiting_approval",
          metadata: {
            builder_session_id: "builder-1",
          },
        },
      ],
      {
        programs: [
          {
            id: "launch-readiness-bootstrap",
            objective: "Drive the external builder lane to takeover readiness.",
            current_family: "durable_persistence_activation",
            waiting_on_approval_family: "durable_persistence_activation",
            waiting_on_approval_slice_id: "persist-04-activation-cutover",
            updated_at: "2026-04-17T23:15:00.000Z",
          },
        ],
        status: {
          active_program_id: "launch-readiness-bootstrap",
          approval_context: {
            kind: "approval_required",
            family: "durable_persistence_activation",
            slice_id: "persist-04-activation-cutover",
            packet_id: "db_schema_change",
            packet_label: "DB schema change",
            approval_authority: "operator",
            summary: "Authorize the durable persistence schema and runtime cutover maintenance window.",
          },
        },
      },
      [
        {
          id: "approval:task-home-1",
          related_run_id: "",
          related_task_id: "task-home-1",
          requested_action: "approve",
          privilege_class: "admin",
          reason: "Approve the home automation adjustment.",
          status: "pending",
          requested_at: 1_800_000_000,
          decided_at: 0,
          decided_by: "",
          task_prompt: "Adjust the evening lighting automation after the recent occupancy drift report.",
          task_agent_id: "home-agent",
          task_priority: "high",
          task_status: "pending_approval",
          task_created_at: 0,
          metadata: {},
        },
      ],
    );

    expect(reviews).toHaveLength(3);
    expect(reviews[0]).toMatchObject({
      id: "approval:task-home-1",
      family: "home_ops",
      source: "operator_approval",
      owner_kind: "task",
      owner_id: "task-home-1",
      related_task_id: "task-home-1",
      requested_action: "approve",
      status: "pending",
      deep_link: "/review?selection=approval%3Atask-home-1",
    });
    expect(reviews[1]).toMatchObject({
      id: "bootstrap-approval:launch-readiness-bootstrap:persist-04-activation-cutover:db_schema_change",
      family: "bootstrap_takeover",
      source: "bootstrap_program",
      owner_kind: "program",
      owner_id: "launch-readiness-bootstrap",
      related_task_id: "persist-04-activation-cutover",
      requested_action: "approve",
      status: "pending",
    });
    expect(reviews[2]).toMatchObject({
      id: "builder-approval-1",
      family: "builder",
      source: "builder_front_door",
      owner_kind: "session",
      owner_id: "builder-1",
      requested_action: "start_builder_execution",
      status: "pending",
    });
  });

  it("builds shared execution result projections from builder result packets", () => {
    const results = buildExecutionResultProjections([
      {
        id: "builder-1",
        title: "Implement the bounded Codex route",
        status: "completed",
        created_at: "2026-04-17T23:00:00.000Z",
        updated_at: "2026-04-17T23:15:00.000Z",
        task_envelope: {
          goal: "Implement the bounded Codex route.",
          task_class: "multi_file_implementation",
          sensitivity_class: "private_but_cloud_allowed",
          workspace_mode: "repo_worktree",
          needs_background: false,
          needs_github: false,
          acceptance_criteria: ["Ship the bounded route"],
        },
        route_decision: {
          route_id: "builder.codex.direct",
          route_label: "Codex direct implementation",
          primary_adapter: "codex",
          execution_mode: "direct_cli",
          fallback_chain: ["claude_code", "terminal_fallback"],
          workspace_plan: "Open a repo worktree and execute the task directly.",
          verification_profile: "targeted_tests_then_diff_review",
          policy_basis: ["private_but_cloud_allowed"],
          activation_state: "live_ready",
        },
        verification_contract: {
          required_checks: ["targeted_tests", "diff_review"],
          blocking_failures: [],
          non_blocking_failures: [],
          fallback_behavior: "resume_terminal",
        },
        verification_state: {
          status: "passed",
          summary: "Targeted tests passed and the diff is clean.",
          completed_checks: ["targeted_tests", "diff_review"],
          failed_checks: [],
          last_updated_at: "2026-04-17T23:14:00.000Z",
        },
        latest_result_packet: {
          outcome: "succeeded",
          summary: "Completed the bounded Codex route and verified the edit.",
          artifacts: [
            {
              id: "workspace-diff",
              label: "Workspace diff",
              kind: "git_diff",
              href: "/builder/artifacts/workspace-diff",
              local_path: null,
            },
          ],
          files_changed: ["src/lib/executive-kernel.ts"],
          validation: [
            {
              id: "targeted_tests",
              label: "targeted tests",
              status: "passed",
              detail: "Focused execution-kernel tests passed.",
            },
          ],
          remaining_risks: [],
          resumable_handle: "codex-session-123",
          recovery_gate: null,
        },
        approvals: [],
        current_worker: "codex",
        current_route: "Codex direct implementation",
        shadow_mode: false,
        fallback_state: null,
        linked_surfaces: {
          runs_href: "/runs?session=builder-1",
          review_href: "/review?selection=builder-1",
          terminal_href: "/terminal?session=builder-1",
        },
      },
    ]);

    expect(results).toHaveLength(1);
    expect(results[0]).toMatchObject({
      id: "builder-result:builder-1",
      family: "builder",
      source: "builder_front_door",
      owner_kind: "session",
      owner_id: "builder-1",
      related_run_id: "builder-run-builder-1",
      status: "completed",
      outcome: "succeeded",
      artifact_count: 1,
      verification_status: "passed",
      files_changed: ["src/lib/executive-kernel.ts"],
      resumable_handle: "codex-session-123",
      deep_link: "/builder?session=builder-1",
    });
  });

  it("loads bootstrap slices into the shared execution job feed", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);

      if (url.includes("/v1/bootstrap/slices?limit=500")) {
        return new Response(
          JSON.stringify({
            slices: [
              {
                id: "persist-04-activation-cutover",
                program_id: "launch-readiness-bootstrap",
                family: "durable_persistence_activation",
                objective: "Cut configured Postgres runtimes over from fallback memory to durable persistence.",
                status: "waiting_approval",
                host_id: "",
                current_ref: "",
                worktree_path: "C:\\Athanor_worktrees\\durable_persistence_activation\\persist-04-activation-cutover",
                files_touched: [],
                validation_status: "pending",
                open_risks: [],
                next_step: "Await DB schema/runtime approval packet execution.",
                stop_reason: "",
                resume_instructions: "",
                depth_level: 2,
                priority: 2,
                phase_scope: "software_core_phase_1",
                continuation_mode: "external_bootstrap",
                metadata: { blocking_packet_id: "db_schema_change" },
                catalog_slice_id: "persist-04",
                family_seed_slice_id: "persist-seed",
                execution_mode: "repo_worktree",
                completion_evidence_paths: [],
                blocking_packet_id: "db_schema_change",
                claimed_at: "",
                completed_at: "",
                created_at: "2026-04-16T20:00:00.000Z",
                updated_at: "2026-04-17T23:15:00.000Z",
              },
            ],
            count: 1,
          }),
          { status: 200 },
        );
      }

      return new Response("not found", { status: 404 });
    });

    const jobs = await loadExecutionJobs({ family: "bootstrap_takeover" });

    expect(jobs).toHaveLength(1);
    expect(jobs[0]).toMatchObject({
      id: "persist-04-activation-cutover",
      family: "bootstrap_takeover",
      source: "bootstrap_slice",
      owner_kind: "program",
      owner_id: "launch-readiness-bootstrap",
    });
  });

  it("loads builder sessions into the shared execution result feed", async () => {
    const env = process.env as Record<string, string | undefined>;
    const originalPath = env.DASHBOARD_BUILDER_STORE_PATH;
    const tempDir = await mkdtemp(path.join(os.tmpdir(), "athanor-execution-results-kernel-"));
    env.DASHBOARD_BUILDER_STORE_PATH = path.join(tempDir, "builder-sessions.json");
    await __resetBuilderStoreForTests();

    const session = await createBuilderSession({
      goal: "Project the builder result packet into generic execution results.",
      task_class: "multi_file_implementation",
      sensitivity_class: "private_but_cloud_allowed",
      workspace_mode: "repo_worktree",
      needs_background: false,
      needs_github: false,
      acceptance_criteria: ["Expose shared execution results"],
    });

    const results = await loadExecutionResults({ family: "builder", outcome: "planned" });

    try {
      expect(results).toHaveLength(1);
      expect(results[0]).toMatchObject({
        id: `builder-result:${session.id}`,
        family: "builder",
        owner_kind: "session",
        owner_id: session.id,
        status: "waiting_approval",
        outcome: "planned",
      });
    } finally {
      if (originalPath === undefined) {
        delete env.DASHBOARD_BUILDER_STORE_PATH;
      } else {
        env.DASHBOARD_BUILDER_STORE_PATH = originalPath;
      }
      await rm(tempDir, { recursive: true, force: true });
    }
  });
});
