"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowUpCircle,
  Ban,
  CheckCircle2,
  CircleDot,
  Compass,
  Eye,
  Heart,
  Loader2,
  Play,
  RefreshCcw,
  Target,
  ThumbsDown,
  ThumbsUp,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { requestJson, postJson, postWithoutBody } from "@/features/workforce/helpers";
import {
  normalizePipelineOutcomes,
  normalizePipelinePlans,
  normalizePipelineProposals,
  normalizePipelineStatus,
  type PipelineStatus,
} from "@/features/pipeline/pipeline-normalization";

const pipelineKeys = {
  status: ["pipeline", "status"] as const,
  outcomes: ["pipeline", "outcomes"] as const,
  plans: ["pipeline", "plans"] as const,
  preview: ["pipeline", "preview"] as const,
};

function qualityTone(score: number): "success" | "warning" | "danger" {
  if (score > 0.7) return "success";
  if (score >= 0.4) return "warning";
  return "danger";
}

function qualityBadgeClass(score: number) {
  if (score > 0.7) return "border-emerald-500/40 bg-emerald-500/10 text-emerald-300";
  if (score >= 0.4) return "border-amber-500/40 bg-amber-500/10 text-amber-300";
  return "border-red-500/40 bg-red-500/10 text-red-300";
}

function riskBadgeVariant(risk: string) {
  switch (risk) {
    case "high":
      return "destructive" as const;
    case "medium":
      return "secondary" as const;
    default:
      return "outline" as const;
  }
}

function truncate(text: string, max: number) {
  if (text.length <= max) return text;
  return text.slice(0, max) + "...";
}

function formatTime(ts: string | null) {
  if (!ts) return "Never";
  const d = new Date(ts);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function PipelineConsole() {
  const queryClient = useQueryClient();
  const [cycling, setCycling] = useState(false);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const statusQuery = useQuery({
    queryKey: pipelineKeys.status,
    queryFn: async () => normalizePipelineStatus(await requestJson("/api/pipeline/status")),
    refetchInterval: 20_000,
  });

  const outcomesQuery = useQuery({
    queryKey: pipelineKeys.outcomes,
    queryFn: async () => normalizePipelineOutcomes(await requestJson("/api/pipeline/outcomes?limit=20")),
    refetchInterval: 30_000,
  });

  const plansQuery = useQuery({
    queryKey: pipelineKeys.plans,
    queryFn: async () => normalizePipelinePlans(await requestJson("/api/pipeline/plans?status=pending")),
    refetchInterval: 20_000,
  });

  const previewQuery = useQuery({
    queryKey: pipelineKeys.preview,
    queryFn: async () => normalizePipelineProposals(await requestJson("/api/pipeline/preview")),
    enabled: false, // Only fetch on demand
  });

  const status = statusQuery.data;
  const outcomes = outcomesQuery.data ?? [];
  const plans = plansQuery.data ?? [];
  const proposals = previewQuery.data ?? [];

  async function loadPreview() {
    setActionBusy("preview");
    setFeedback(null);
    try {
      await previewQuery.refetch();
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : "Preview failed.");
    } finally {
      setActionBusy(null);
    }
  }

  async function reactToProposal(index: number, reaction: "more" | "less" | "love" | "wrong") {
    const proposal = proposals[index];
    if (!proposal) return;
    setActionBusy(`react:${index}`);
    try {
      await postJson("/api/pipeline/react", {
        intent_id: `preview-${index}`,
        reaction,
        intent_metadata: {
          twelve_word: proposal.twelve_word,
          project: proposal.project,
          domain: proposal.project,
        },
      });
      setFeedback(`Reacted "${reaction}" to: ${proposal.text.slice(0, 60)}...`);
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : "Reaction failed.");
    } finally {
      setActionBusy(null);
    }
  }

  async function boostDomain(domain: string) {
    setActionBusy(`boost:${domain}`);
    try {
      await postJson("/api/pipeline/boost", { domain, amount: 0.15 });
      setFeedback(`Boosted "${domain}" for next cycle.`);
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : "Boost failed.");
    } finally {
      setActionBusy(null);
    }
  }

  async function suppressDomain(domain: string) {
    setActionBusy(`suppress:${domain}`);
    try {
      await postJson("/api/pipeline/suppress", { domain, duration_hours: 24 });
      setFeedback(`Suppressed "${domain}" for 24h.`);
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : "Suppress failed.");
    } finally {
      setActionBusy(null);
    }
  }

  async function triggerCycle() {
    setCycling(true);
    setFeedback(null);
    try {
      await postWithoutBody("/api/pipeline/cycle");
      await queryClient.invalidateQueries({ queryKey: ["pipeline"] });
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : "Cycle trigger failed.");
    } finally {
      setCycling(false);
    }
  }

  async function handlePlanAction(planId: string, action: "approve" | "reject") {
    const key = `${action}:${planId}`;
    setActionBusy(key);
    setFeedback(null);
    try {
      await postWithoutBody(`/api/pipeline/plans/${planId}/${action}`);
      await plansQuery.refetch();
      await statusQuery.refetch();
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : `Failed to ${action} plan.`);
    } finally {
      setActionBusy(null);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Workforce"
        title="Work Pipeline"
        description="Watch intent become action — from mining to plans to execution."
        attentionHref="/pipeline"
        actions={
          <>
            <Button
              variant="outline"
              onClick={() => void queryClient.invalidateQueries({ queryKey: ["pipeline"] })}
              disabled={statusQuery.isFetching}
            >
              <RefreshCcw className={`mr-2 h-4 w-4 ${statusQuery.isFetching ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button onClick={() => void triggerCycle()} disabled={cycling}>
              {cycling ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              Trigger Cycle
            </Button>
          </>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Recent Cycles"
            value={status ? `${status.recent_cycles}` : "--"}
            detail={status?.last_cycle ? `Last: ${formatTime(status.last_cycle)}` : "No cycles yet"}
            icon={<Activity className="h-5 w-5" />}
            valueVolatile
          />
          <StatCard
            label="Pending Plans"
            value={status ? `${status.pending_plans}` : "--"}
            detail={status && status.pending_plans > 0 ? "Awaiting operator review" : "All clear"}
            tone={status && status.pending_plans > 0 ? "warning" : "success"}
            icon={<Target className="h-5 w-5" />}
            valueVolatile
          />
          <StatCard
            label="Recent Outcomes"
            value={status ? `${status.recent_outcomes_count}` : "--"}
            detail="Tasks completed this window"
            icon={<CircleDot className="h-5 w-5" />}
            valueVolatile
          />
          <StatCard
            label="Avg Quality"
            value={status ? status.avg_quality.toFixed(2) : "--"}
            tone={status ? qualityTone(status.avg_quality) : "default"}
            detail="Across recent outcomes"
            valueVolatile
          />
        </div>
      </PageHeader>

      {feedback && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          {feedback}
        </div>
      )}

      {/* Synthesis Preview & Steering */}
      <Card className="surface-panel">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-lg">Intent Synthesis</CardTitle>
              <CardDescription>
                Preview what the synthesizer would generate. React to steer future cycles.
              </CardDescription>
            </div>
            <Button
              variant="outline"
              onClick={() => void loadPreview()}
              disabled={actionBusy === "preview" || previewQuery.isFetching}
            >
              {previewQuery.isFetching ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Eye className="mr-2 h-4 w-4" />
              )}
              Preview Next Cycle
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {proposals.length > 0 ? (
            proposals.map((proposal, i) => (
              <div
                key={`${proposal.agent}-${i}`}
                className="rounded-2xl border border-border/70 bg-background/20 p-4 space-y-3"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">{proposal.agent}</Badge>
                  <Badge variant="outline">{proposal.project}</Badge>
                  <Badge
                    variant="outline"
                    className={
                      proposal.priority >= 0.7
                        ? "border-emerald-500/40 text-emerald-300"
                        : proposal.priority >= 0.4
                        ? "border-amber-500/40 text-amber-300"
                        : "border-zinc-500/40 text-zinc-400"
                    }
                  >
                    {proposal.priority.toFixed(1)}
                  </Badge>
                  {proposal.twelve_word && (
                    <Badge variant="outline" className="border-purple-500/30 text-purple-300">
                      {proposal.twelve_word}
                    </Badge>
                  )}
                  {proposal.explore && (
                    <Badge variant="outline" className="border-cyan-500/40 text-cyan-300">
                      <Compass className="mr-1 h-3 w-3" />
                      explore
                    </Badge>
                  )}
                </div>
                <p className="text-sm">{proposal.text}</p>
                {proposal.reasoning && (
                  <p className="text-xs text-muted-foreground">{proposal.reasoning}</p>
                )}
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs"
                    onClick={() => void reactToProposal(i, "love")}
                    disabled={actionBusy === `react:${i}`}
                  >
                    <Heart className="mr-1 h-3 w-3 text-pink-400" /> Love
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs"
                    onClick={() => void reactToProposal(i, "more")}
                    disabled={actionBusy === `react:${i}`}
                  >
                    <ThumbsUp className="mr-1 h-3 w-3 text-emerald-400" /> More
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs"
                    onClick={() => void reactToProposal(i, "less")}
                    disabled={actionBusy === `react:${i}`}
                  >
                    <ThumbsDown className="mr-1 h-3 w-3 text-amber-400" /> Less
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs"
                    onClick={() => void reactToProposal(i, "wrong")}
                    disabled={actionBusy === `react:${i}`}
                  >
                    <XCircle className="mr-1 h-3 w-3 text-red-400" /> Wrong
                  </Button>
                  <span className="mx-1 self-center text-xs text-muted-foreground/50">|</span>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs"
                    onClick={() => void boostDomain(proposal.project)}
                    disabled={!!actionBusy?.startsWith("boost:")}
                  >
                    <ArrowUpCircle className="mr-1 h-3 w-3 text-blue-400" /> Boost domain
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs"
                    onClick={() => void suppressDomain(proposal.project)}
                    disabled={!!actionBusy?.startsWith("suppress:")}
                  >
                    <Ban className="mr-1 h-3 w-3 text-zinc-400" /> Suppress 24h
                  </Button>
                </div>
              </div>
            ))
          ) : (
            <EmptyState
              title="No preview loaded"
              description="Click 'Preview Next Cycle' to see what the synthesizer would generate."
            />
          )}
        </CardContent>
      </Card>

      {/* Pending Plans */}
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Pending Plans</CardTitle>
          <CardDescription>
            Plans awaiting operator approval before execution.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {plans.length > 0 ? (
            plans.map((plan) => (
              <div
                key={plan.id}
                className="surface-hero rounded-2xl border p-4 space-y-3"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{plan.title}</span>
                  <Badge variant="outline">{plan.intent_source}</Badge>
                  <Badge variant={riskBadgeVariant(plan.risk_level)}>
                    {plan.risk_level} risk
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  {truncate(plan.approach, 200)}
                </p>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => void handlePlanAction(plan.id, "approve")}
                    disabled={actionBusy === `approve:${plan.id}`}
                  >
                    {actionBusy === `approve:${plan.id}` ? (
                      <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                    ) : (
                      <CheckCircle2 className="mr-1 h-3 w-3" />
                    )}
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => void handlePlanAction(plan.id, "reject")}
                    disabled={actionBusy === `reject:${plan.id}`}
                  >
                    {actionBusy === `reject:${plan.id}` ? (
                      <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                    ) : (
                      <XCircle className="mr-1 h-3 w-3" />
                    )}
                    Reject
                  </Button>
                </div>
              </div>
            ))
          ) : (
            <EmptyState
              title="No pending plans"
              description="All plans have been reviewed or the pipeline hasn't generated new ones yet."
            />
          )}
        </CardContent>
      </Card>

      {/* Recent Outcomes */}
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Recent Outcomes</CardTitle>
          <CardDescription>
            Task results from recent pipeline cycles.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {outcomes.length > 0 ? (
            outcomes.map((outcome) => (
              <div
                key={outcome.task_id}
                className="surface-tile flex flex-wrap items-start justify-between gap-3 rounded-2xl border p-4"
              >
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">{outcome.agent}</Badge>
                    <Badge
                      variant="outline"
                      className={qualityBadgeClass(outcome.quality_score)}
                    >
                      {outcome.quality_score.toFixed(2)}
                    </Badge>
                    {outcome.success ? (
                      <Badge variant="outline" className="border-emerald-500/40 text-emerald-300">
                        Success
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="border-red-500/40 text-red-300">
                        Failed
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm">{truncate(outcome.prompt, 140)}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatTime(outcome.ts)}
                  </p>
                </div>
              </div>
            ))
          ) : (
            <EmptyState
              title="No outcomes yet"
              description="Pipeline hasn't produced any task outcomes in the current window."
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
