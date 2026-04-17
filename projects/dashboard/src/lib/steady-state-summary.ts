import type { SteadyStateReadStatus, SteadyStateSnapshot } from "@/lib/contracts";

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

export interface SteadyStateDigestSnapshot {
  comparisonKey: string;
  degraded: boolean;
  needsYou: boolean;
  attentionLabel: string;
  attentionTone: SteadyStateTone;
  changeHeadline: string;
  currentWorkTitle: string;
  nextUpTitle: string;
  queuePosture: string;
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

export function buildSteadyStateDigestSnapshot(
  steadyState: SteadyStateSnapshot | null | undefined,
  readStatus: SteadyStateReadStatus | null | undefined,
  fallback: SteadyStateDecisionFallback = {},
): SteadyStateDigestSnapshot {
  const summary = buildSteadyStateDecisionSummary(steadyState, fallback);
  const degraded = Boolean(readStatus?.degraded);
  const changeHeadline = degraded
    ? readStatus?.detail ?? "Steady-state front door degraded."
    : summary.attentionSummary;

  return {
    comparisonKey: [
      degraded ? "degraded" : "healthy",
      summary.attentionLabel,
      summary.currentWorkTitle,
      summary.nextUpTitle,
      summary.queuePosture,
    ].join("|"),
    degraded,
    needsYou: summary.needsYou,
    attentionLabel: summary.attentionLabel,
    attentionTone: summary.attentionTone,
    changeHeadline,
    currentWorkTitle: summary.currentWorkTitle,
    nextUpTitle: summary.nextUpTitle,
    queuePosture: summary.queuePosture,
    sourceLabel: degraded ? `degraded ${readStatus?.sourceKind ?? "front door"}` : summary.sourceLabel,
  };
}

export function describeSteadyStateDigestChange(
  previous: SteadyStateDigestSnapshot | null | undefined,
  current: SteadyStateDigestSnapshot,
): string {
  if (!previous) {
    return current.degraded
      ? "Front door needs attention on this device."
      : "Front door synced on this device."
  }

  if (previous.degraded !== current.degraded) {
    return current.degraded ? "Front door degraded since the last refresh." : "Front door restored since the last refresh.";
  }

  if (previous.needsYou !== current.needsYou) {
    return current.needsYou ? "Shaun attention is now required." : "Operator attention cleared.";
  }

  if (previous.currentWorkTitle !== current.currentWorkTitle) {
    return `Current work changed to ${current.currentWorkTitle}.`;
  }

  if (previous.nextUpTitle !== current.nextUpTitle) {
    return `Next up changed to ${current.nextUpTitle}.`;
  }

  if (previous.attentionLabel !== current.attentionLabel) {
    return `Attention changed to ${current.attentionLabel}.`;
  }

  return "No material front-door change since the last refresh.";
}
