import {
  type GovernanceSnapshot,
  OperatorConsole,
  type OperatorConsoleInitialData,
  type OperatorSummaryPayload,
  type PendingApprovalsPayload,
} from "@/features/operator/operator-console";
import { loadExecutionReviews } from "@/lib/executive-kernel";
import {
  buildFallbackMasterAtlasRelationshipMap,
  pickMasterAtlasRelationshipMap,
  readGeneratedMasterAtlas,
} from "@/lib/master-atlas";
import { loadProjectFactorySnapshot } from "@/lib/project-factory";
import { loadOperatorSummaryPayload } from "@/lib/operator-summary";
import { proxyAgentJson } from "@/lib/server-agent";

export const revalidate = 15;

async function loadPendingApprovals(): Promise<PendingApprovalsPayload> {
  const reviews = await loadExecutionReviews({ status: "pending", limit: 500 });
  return {
    available: true,
    degraded: false,
    source: "execution-review-feed",
    reviews,
    count: reviews.length,
  };
}

async function loadGovernance(): Promise<GovernanceSnapshot> {
  const fallback: GovernanceSnapshot = {
    available: false,
    degraded: true,
    source: "agent-server",
    detail: "Failed to fetch operator governance",
    current_mode: {
      mode: "feed_unavailable",
    },
    launch_blockers: ["operator_upstream_unavailable"],
    launch_ready: false,
    attention_posture: {
      recommended_mode: "manual_review",
      breaches: ["Operator governance feed is temporarily unavailable from the dashboard runtime."],
    },
  };
  const response = await proxyAgentJson("/v1/operator/governance", undefined, "Failed to fetch operator governance");
  if (response.status >= 500) {
    return fallback;
  }
  try {
    return (await response.json()) as GovernanceSnapshot;
  } catch {
    return fallback;
  }
}

async function loadMasterAtlas() {
  try {
    const bundle = await readGeneratedMasterAtlas();
    return pickMasterAtlasRelationshipMap(bundle);
  } catch {
    return buildFallbackMasterAtlasRelationshipMap(
      "The dashboard runtime failed to load the compiled master atlas feed.",
      "Failed to load master atlas feed",
    );
  }
}

export default async function OperatorPage() {
  const [pendingApprovals, governance, operatorSummary, masterAtlas, projectFactory] = await Promise.all([
    loadPendingApprovals(),
    loadGovernance(),
    loadOperatorSummaryPayload() as Promise<OperatorSummaryPayload>,
    loadMasterAtlas(),
    loadProjectFactorySnapshot(),
  ]);

  const initialData: OperatorConsoleInitialData = {
    pendingApprovals,
    governance,
    operatorSummary,
    masterAtlas,
    projectFactory,
  };

  return <OperatorConsole initialData={initialData} />;
}
