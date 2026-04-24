import { NextRequest, NextResponse } from "next/server";
import { agentServerHeaders, config, joinUrl } from "@/lib/config";
import { readGeneratedMasterAtlas } from "@/lib/master-atlas";
import { proxyAgentOperatorJson } from "@/lib/operator-actions";
import { requireSameOriginOperatorSessionAccess } from "@/lib/operator-auth";

type GovernedDispatchState = Record<string, unknown>;
type OperatorBacklogItem = Record<string, unknown>;

function coerceString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function backlogMetadata(item: OperatorBacklogItem): Record<string, unknown> {
  const metadata = item.metadata;
  return metadata && typeof metadata === "object" && !Array.isArray(metadata)
    ? (metadata as Record<string, unknown>)
    : {};
}

function matchesExistingMaterialization(
  item: OperatorBacklogItem,
  claimId: string,
  taskId: string,
  title: string
) {
  const metadata = backlogMetadata(item);
  const metadataClaimId = coerceString(metadata.claim_id);
  const metadataTaskId = coerceString(metadata.current_task_id);
  const metadataSource = coerceString(metadata.materialization_source);
  const itemTitle = coerceString(item.title);
  const prompt = coerceString(item.prompt);

  if (metadataSource === "governed_dispatch_state" && metadataClaimId && metadataClaimId === claimId) {
    return true;
  }
  if (metadataSource === "governed_dispatch_state" && metadataTaskId && metadataTaskId === taskId) {
    return true;
  }
  return (
    itemTitle.length > 0 &&
    itemTitle === title &&
    prompt.startsWith('Advance the governed dispatch claim for "')
  );
}

async function fetchExistingBacklogItem(
  claimId: string,
  taskId: string,
  title: string
): Promise<OperatorBacklogItem | null> {
  try {
    const response = await fetch(joinUrl(config.agentServer.url, "/v1/operator/backlog?limit=120"), {
      method: "GET",
      headers: agentServerHeaders(),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    if (!response.ok) {
      return null;
    }
    const payload = (await response.json().catch(() => null)) as { backlog?: unknown[] } | null;
    const rows = Array.isArray(payload?.backlog)
      ? payload.backlog.filter((item): item is OperatorBacklogItem => typeof item === "object" && item !== null)
      : [];
    return rows.find((item) => matchesExistingMaterialization(item, claimId, taskId, title)) ?? null;
  } catch {
    return null;
  }
}

function buildGovernedDispatchPrompt(state: GovernedDispatchState): string {
  const currentTaskTitle = coerceString(state.current_task_title) || "Governed dispatch follow-through";
  const currentTaskId = coerceString(state.current_task_id);
  const laneFamily = coerceString(state.preferred_lane_family) || "unknown_lane_family";
  const mutationLabel = coerceString(state.approved_mutation_label) || "Unknown mutation class";
  const proofSurface = coerceString(state.proof_command_or_eval_surface);
  const claimId = coerceString(state.claim_id);
  const reportPath = coerceString(state.report_path);
  const providerGateState = coerceString(state.provider_gate_state) || "unknown";
  const workEconomyStatus = coerceString(state.work_economy_status) || "unknown";

  const lines = [
    `Advance the governed dispatch claim for "${currentTaskTitle}".`,
    currentTaskId ? `Current task id: ${currentTaskId}` : null,
    claimId ? `Claim id: ${claimId}` : null,
    `Preferred lane family: ${laneFamily}`,
    `Approved mutation class: ${mutationLabel}`,
    `Provider gate: ${providerGateState}`,
    `Work economy: ${workEconomyStatus}`,
    proofSurface ? `Proof surface: ${proofSurface}` : null,
    reportPath ? `Dispatch artifact: ${reportPath}` : null,
    "Stay within repo-safe, non-runtime work unless a governed approval surface explicitly widens scope.",
  ].filter((line): line is string => Boolean(line));

  return lines.join("\n");
}

export async function POST(request: NextRequest) {
  const gate = requireSameOriginOperatorSessionAccess(request);
  if (gate) {
    return gate;
  }

  const bundle = await readGeneratedMasterAtlas();
  const state =
    bundle?.governed_dispatch_state &&
    typeof bundle.governed_dispatch_state === "object" &&
    !Array.isArray(bundle.governed_dispatch_state)
      ? (bundle.governed_dispatch_state as GovernedDispatchState)
      : null;

  const currentTaskId = coerceString(state?.current_task_id);
  const currentTaskTitle = coerceString(state?.current_task_title);
  const claimId = coerceString(state?.claim_id);

  if (!state || !currentTaskId || !currentTaskTitle || !claimId) {
    return NextResponse.json(
      {
        error: "No governed dispatch claim is ready to materialize.",
        gate: "governed-dispatch-unavailable",
      },
      { status: 409 }
    );
  }

  const existing = await fetchExistingBacklogItem(claimId, currentTaskId, currentTaskTitle);
  if (existing) {
    return NextResponse.json(
      {
        ok: true,
        already_materialized: true,
        backlog_id: coerceString(existing.id) || null,
        title: coerceString(existing.title) || currentTaskTitle,
      },
      { status: 200 }
    );
  }

  const body = (await request.json().catch(() => ({}))) as Record<string, unknown>;
  const ownerAgent = coerceString(body.owner_agent) || "coding-agent";
  const reason =
    coerceString(body.reason) || `Materialized governed dispatch claim ${claimId} from routing console`;

  return proxyAgentOperatorJson(
    request,
    "/v1/operator/backlog",
    "Failed to materialize governed dispatch backlog item",
    {
      privilegeClass: "operator",
      defaultReason: reason,
      bodyOverride: {
        actor: "routing-console",
        reason,
        title: currentTaskTitle,
        prompt: buildGovernedDispatchPrompt(state),
        owner_agent: ownerAgent,
        support_agents: [],
        scope_type: "global",
        scope_id: "athanor",
        work_class: "system_improvement",
        priority: 1,
        approval_mode: "none",
        dispatch_policy: "planner_eligible",
        family: "maintenance",
        project_id: "athanor",
        source_type: "operator_request",
        source_ref: claimId,
        routing_class: "private_but_cloud_allowed",
        verification_contract: "maintenance_proof",
        closure_rule: "proof_or_review_required",
        materialization_source: "governed_dispatch_state",
        materialization_reason: reason,
        recurrence_program_id: "",
        result_id: "",
        review_id: "",
        preconditions: ["governed_dispatch_state_present"],
        metadata: {
          materialization_source: "governed_dispatch_state",
          claim_id: claimId,
          current_task_id: currentTaskId,
          current_task_title: currentTaskTitle,
          preferred_lane_family: coerceString(state.preferred_lane_family),
          approved_mutation_class: coerceString(state.approved_mutation_class),
          approved_mutation_label: coerceString(state.approved_mutation_label),
          provider_gate_state: coerceString(state.provider_gate_state),
          work_economy_status: coerceString(state.work_economy_status),
          report_path: coerceString(state.report_path),
        },
      },
    }
  );
}
