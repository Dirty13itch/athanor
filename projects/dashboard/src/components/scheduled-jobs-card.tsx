"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeftRight, CalendarClock, RefreshCcw, Rocket, ShieldAlert } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getBootstrapProgramsData, getOperatorSummaryData } from "@/lib/api";
import { formatRelativeTime } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";

interface BootstrapProgram {
  id: string;
  label: string;
  objective: string;
  phase_scope: string;
  status: string;
  current_family: string;
  next_slice_id: string;
  recommended_host_id: string;
  pending_integrations: number;
  slice_counts: {
    total: number;
    queued: number;
    active: number;
    blocked: number;
    completed: number;
  };
  updated_at?: string;
}

interface BootstrapProgramsResponse {
  programs: BootstrapProgram[];
  count: number;
  status?: {
    open_blockers?: number;
    pending_integrations?: number;
    active_family?: string;
    recommended_host_id?: string;
    takeover?: { ready?: boolean };
  };
}

function formatLabel(value: string) {
  return value.replace(/_/g, " ");
}

function toneForStatus(value: string) {
  if (value === "blocked") {
    return "destructive" as const;
  }
  if (value === "ready_for_takeover_check" || value === "active") {
    return "secondary" as const;
  }
  return "outline" as const;
}

export function ScheduledJobsCard({
  title = "Bootstrap loops",
  description = "Recursive builder families, serial integration posture, and manual supervisor nudges for the external bootstrap stack.",
}: {
  title?: string;
  description?: string;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const programsQuery = useQuery({
    queryKey: queryKeys.bootstrapPrograms,
    queryFn: async () => (await getBootstrapProgramsData()) as unknown as BootstrapProgramsResponse,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const summaryQuery = useQuery({
    queryKey: queryKeys.operatorSummary,
    queryFn: getOperatorSummaryData,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  async function runSupervisor(programId: string, execute = true) {
    setBusy(programId);
    setFeedback(null);
    try {
      const response = await fetch(`/api/bootstrap/programs/${encodeURIComponent(programId)}/nudge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          execute,
          reason: "Triggered from bootstrap loops card",
        }),
      });
      if (!response.ok) {
        throw new Error(`Bootstrap nudge failed (${response.status})`);
      }
      const payload = (await response.json()) as {
        active_family?: string;
        recommendation?: { slice_id?: string; host_id?: string };
        actions?: Array<{ kind?: string }>;
      };
      const actionCount = Array.isArray(payload.actions) ? payload.actions.length : 0;
      setFeedback(
        payload.recommendation?.slice_id
          ? `Cycle ran for ${programId}. Next slice ${payload.recommendation.slice_id} on ${payload.recommendation.host_id || "unassigned"} (${actionCount} actions).`
          : `Cycle ran for ${programId}${payload.active_family ? ` in ${formatLabel(payload.active_family)}` : ""}.`
      );
      await Promise.all([programsQuery.refetch(), summaryQuery.refetch()]);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Failed to nudge bootstrap supervisor.");
    } finally {
      setBusy(null);
    }
  }

  if (programsQuery.isError && !programsQuery.data) {
    return (
      <ErrorPanel
        title={title}
        description={
          programsQuery.error instanceof Error
            ? programsQuery.error.message
            : "Failed to load bootstrap-loop records."
        }
      />
    );
  }

  const programs = programsQuery.data?.programs ?? [];
  const status = programsQuery.data?.status;
  const governance = (summaryQuery.data?.governance as Record<string, unknown> | undefined) ?? {};
  const bootstrap = (summaryQuery.data?.bootstrap as Record<string, unknown> | undefined) ?? {};

  return (
    <Card className="border-border/70 bg-card/70">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <CalendarClock className="h-5 w-5 text-primary" />
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {feedback ? (
          <div className="rounded-xl border border-border/60 bg-background/30 px-3 py-2 text-sm">
            {feedback}
          </div>
        ) : null}

        <div className="grid gap-3 sm:grid-cols-4">
          <Metric label="Programs" value={`${programs.length}`} />
          <Metric label="Blockers" value={`${status?.open_blockers ?? 0}`} />
          <Metric label="Pending replay" value={`${status?.pending_integrations ?? 0}`} />
          <Metric label="Takeover" value={status?.takeover?.ready ? "Ready" : "Blocked"} />
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={() => void Promise.all([programsQuery.refetch(), summaryQuery.refetch()])}
            disabled={programsQuery.isFetching || summaryQuery.isFetching}
          >
            <RefreshCcw className={`mr-2 h-4 w-4 ${(programsQuery.isFetching || summaryQuery.isFetching) ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Badge variant="outline">
            active family {formatLabel(String(status?.active_family || bootstrap.active_family || "unknown"))}
          </Badge>
          {governance && Object.keys(governance).length > 0 ? (
            <Badge variant="outline">
              mode {formatLabel(String((governance.current_mode as string | undefined) || (governance.mode as string | undefined) || "unknown"))}
            </Badge>
          ) : null}
        </div>

        {programs.length > 0 ? (
          <div className="space-y-3">
            {programs.map((program) => (
              <div
                key={program.id}
                className="block rounded-2xl border border-border/70 bg-background/20 p-4"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={toneForStatus(program.status)}>{formatLabel(program.status)}</Badge>
                  <Badge variant="secondary">{formatLabel(program.current_family || "queued")}</Badge>
                  <Badge variant="outline">{program.phase_scope}</Badge>
                  {program.recommended_host_id ? (
                    <Badge variant="outline">
                      <ArrowLeftRight className="mr-1 h-3 w-3" />
                      {program.recommended_host_id}
                    </Badge>
                  ) : null}
                  {program.slice_counts.blocked > 0 ? (
                    <Badge variant="destructive">
                      <ShieldAlert className="mr-1 h-3 w-3" />
                      {program.slice_counts.blocked} blocked
                    </Badge>
                  ) : null}
                </div>
                <p className="mt-3 text-sm font-medium">{program.label}</p>
                <p className="mt-2 text-xs text-muted-foreground">{program.objective}</p>
                <div className="mt-3 grid gap-2 text-xs text-muted-foreground md:grid-cols-3">
                  <span>next slice: {program.next_slice_id || "none"}</span>
                  <span>pending replay: {program.pending_integrations}</span>
                  <span data-volatile="true">
                    updated {program.updated_at ? formatRelativeTime(program.updated_at) : "unknown"}
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                  <Badge variant="outline">queued {program.slice_counts.queued}</Badge>
                  <Badge variant="outline">active {program.slice_counts.active}</Badge>
                  <Badge variant="outline">completed {program.slice_counts.completed}</Badge>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => void runSupervisor(program.id, true)}
                    disabled={busy !== null}
                  >
                    <Rocket className="mr-2 h-4 w-4" />
                    Run cycle
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No bootstrap loops yet"
            description="Bootstrap programs will appear here once the recursive builder registry is active."
            className="py-8"
          />
        )}
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/30 px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}
