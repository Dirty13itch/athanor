import type { SteadyStateSnapshot } from "@/lib/contracts";

export type SteadyStateTone = "healthy" | "warning" | "danger";

export interface SteadyStateDecisionFallback {
  attentionLabel?: string;
  attentionSummary?: string;
  currentWorkTitle?: string;
  currentWorkDetail?: string;
  nextUpTitle?: string;
  nextUpDetail?: string;
  queuePosture?: string;
  needsYou?: boolean;
}

export interface SteadyStateDecisionSummary {
  attentionLabel: string;
  attentionSummary: string;
  attentionTone: SteadyStateTone;
  currentWorkTitle: string;
  currentWorkDetail: string;
  nextUpTitle: string;
  nextUpDetail: string;
  queuePosture: string;
  needsYou: boolean;
  sourceLabel: string;
}

function joinDetail(parts: Array<string | null | undefined>, fallback: string): string {
  const detail = parts.filter((value): value is string => typeof value === "string" && value.length > 0).join(" · ");
  return detail || fallback;
}

export function getSteadyStateAttentionTone(
  steadyState: SteadyStateSnapshot | null | undefined,
  needsYouFallback = false,
): SteadyStateTone {
  if (!steadyState) {
    return needsYouFallback ? "danger" : "warning";
  }
  if (steadyState.needsYou) return "danger";
  if (steadyState.runtimePacketCount > 0) return "danger";
  if (steadyState.queueDispatchable > 0) return "warning";
  return "healthy";
}

export function getSteadyStateSourceLabel(steadyState: SteadyStateSnapshot | null | undefined): string {
  if (!steadyState) return "steady-state feed unavailable";
  if (steadyState.sourceKind === "repo_root_fallback") return "repo-root fallback";
  if (steadyState.sourceKind === "workspace_report") return "workspace report";
  return "steady-state feed attached";
}

export function buildSteadyStateDecisionSummary(
  steadyState: SteadyStateSnapshot | null | undefined,
  fallback: SteadyStateDecisionFallback = {},
): SteadyStateDecisionSummary {
  const needsYou = steadyState?.needsYou ?? fallback.needsYou ?? false;
  const attentionTone = getSteadyStateAttentionTone(steadyState, needsYou);

  return {
    attentionLabel:
      steadyState?.interventionLabel ?? fallback.attentionLabel ?? (needsYou ? "Review recommended" : "No action needed"),
    attentionSummary:
      steadyState?.interventionSummary ??
      fallback.attentionSummary ??
      "Use the operator desk for approvals, overrides, and governed blockers.",
    attentionTone,
    currentWorkTitle:
      steadyState?.currentWork?.taskTitle ?? fallback.currentWorkTitle ?? "No governed work published.",
    currentWorkDetail: joinDetail(
      [steadyState?.currentWork?.providerLabel, steadyState?.currentWork?.laneFamily],
      fallback.currentWorkDetail ?? "No current provider or lane published.",
    ),
    nextUpTitle:
      steadyState?.nextUp?.taskTitle ?? fallback.nextUpTitle ?? "No follow-on handoff published.",
    nextUpDetail:
      steadyState?.nextOperatorAction ?? fallback.nextUpDetail ?? "No next operator action published.",
    queuePosture:
      steadyState
        ? `${steadyState.queueDispatchable} dispatchable / ${steadyState.suppressedTaskCount} suppressed / ${steadyState.runtimePacketCount} runtime packets`
        : fallback.queuePosture ?? "No queue posture published.",
    needsYou,
    sourceLabel: getSteadyStateSourceLabel(steadyState),
  };
}
