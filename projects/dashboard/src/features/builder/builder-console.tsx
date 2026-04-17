"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  Hammer,
  PauseCircle,
  PlayCircle,
  RefreshCcw,
  ShieldCheck,
  TerminalSquare,
  Workflow,
  XCircle,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import {
  controlBuilderSession,
  createBuilderSession,
  getBuilderSession,
  getBuilderSessionEvents,
  getBuilderSummary,
} from "@/lib/api";
import {
  type BuilderControlAction,
  type BuilderExecutionSession,
  type BuilderTaskClass,
  type BuilderWorkspaceMode,
  type BuilderSensitivityClass,
} from "@/lib/contracts";
import { formatRelativeTime } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import { useUrlState } from "@/lib/url-state";

const TASK_CLASS_OPTIONS: Array<{ value: BuilderTaskClass; label: string }> = [
  { value: "multi_file_implementation", label: "Multi-file implementation" },
  { value: "deterministic_refactor", label: "Deterministic refactor" },
  { value: "architecture_review", label: "Architecture review" },
  { value: "repo_wide_audit", label: "Repo-wide audit" },
  { value: "sovereign_private_coding", label: "Sovereign private coding" },
  { value: "creative_batch", label: "Creative batch" },
];

const SENSITIVITY_OPTIONS: Array<{ value: BuilderSensitivityClass; label: string }> = [
  { value: "private_but_cloud_allowed", label: "Private but cloud allowed" },
  { value: "cloud_safe", label: "Cloud safe" },
  { value: "sovereign_only", label: "Sovereign only" },
];

const WORKSPACE_OPTIONS: Array<{ value: BuilderWorkspaceMode; label: string }> = [
  { value: "repo_worktree", label: "Repo worktree" },
  { value: "same_repo", label: "Same repo" },
  { value: "docs_only", label: "Docs only" },
];

function badgeVariant(status: string): "default" | "secondary" | "outline" | "destructive" {
  if (status === "completed" || status === "passed" || status === "approved") {
    return "secondary";
  }
  if (status === "failed" || status === "cancelled" || status === "rejected" || status === "blocked") {
    return "destructive";
  }
  if (status === "waiting_approval" || status === "planned" || status === "queued") {
    return "outline";
  }
  return "default";
}

function formatLabel(value: string | null | undefined): string {
  return value ? value.replaceAll("_", " ") : "n/a";
}

function buildAcceptanceCriteria(input: string, goal: string): string[] {
  const parsed = input
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  return parsed.length > 0 ? parsed : [goal.trim()];
}

function SessionCard({ session, selected, onSelect }: { session: any; selected: boolean; onSelect: () => void }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-2xl border p-4 text-left transition ${
        selected ? "border-primary bg-primary/5" : "border-border/70 bg-background/20 hover:bg-accent/30"
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={badgeVariant(session.status)}>{formatLabel(session.status)}</Badge>
        <Badge variant="outline">{session.primary_adapter}</Badge>
        {session.shadow_mode ? <Badge variant="outline">shadow</Badge> : null}
      </div>
      <p className="mt-3 text-sm font-medium text-foreground">{session.title}</p>
      <p className="mt-1 text-xs text-muted-foreground">{session.current_route}</p>
      <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
        <span>{session.pending_approval_count} approvals</span>
        <span>{session.artifact_count} artifacts</span>
        <span>{formatRelativeTime(session.updated_at)}</span>
      </div>
    </button>
  );
}

function SessionSurface({
  session,
  events,
  busyAction,
  onControl,
}: {
  session: BuilderExecutionSession;
  events: Array<{ id: string; event_type: string; label: string; detail: string; tone: string; timestamp: string }>;
  busyAction: BuilderControlAction | null;
  onControl: (action: BuilderControlAction, approvalId?: string | null) => void;
}) {
  return (
    <div className="space-y-4">
      <Card className="surface-panel border">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle className="text-xl">{session.title}</CardTitle>
              <CardDescription className="mt-1">
                {session.route_decision.route_label} on {session.route_decision.primary_adapter}
              </CardDescription>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant={badgeVariant(session.status)}>{formatLabel(session.status)}</Badge>
              <Badge variant="outline">{session.route_decision.execution_mode}</Badge>
              {session.shadow_mode ? <Badge variant="outline">shadow mode</Badge> : null}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm leading-6 text-muted-foreground">{session.task_envelope.goal}</p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Task class" value={formatLabel(session.task_envelope.task_class)} detail={formatLabel(session.task_envelope.sensitivity_class)} icon={<Workflow className="h-5 w-5" />} />
            <StatCard label="Workspace" value={formatLabel(session.task_envelope.workspace_mode)} detail={session.task_envelope.needs_github ? "GitHub flow" : "Local flow"} />
            <StatCard label="Approvals" value={`${session.approvals.filter((entry) => entry.status === "pending").length}`} detail="Pending builder approval holds." icon={<ShieldCheck className="h-5 w-5" />} />
            <StatCard label="Verification" value={formatLabel(session.verification_state.status)} detail={session.route_decision.verification_profile} icon={<CheckCircle2 className="h-5 w-5" />} />
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onControl("resume")}
              disabled={busyAction !== null}
            >
              <PlayCircle className="mr-2 h-4 w-4" />
              Resume
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onControl("cancel")}
              disabled={busyAction !== null}
            >
              <PauseCircle className="mr-2 h-4 w-4" />
              Cancel
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onControl("open_terminal")}
              disabled={busyAction !== null}
            >
              <TerminalSquare className="mr-2 h-4 w-4" />
              Open terminal
            </Button>
            <Button asChild variant="outline" size="sm">
              <Link href={session.linked_surfaces.runs_href}>Open runs</Link>
            </Button>
            <Button asChild variant="outline" size="sm">
              <Link href={session.linked_surfaces.review_href}>Open review</Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="surface-panel border">
          <CardHeader>
            <CardTitle className="text-lg">Route decision</CardTitle>
            <CardDescription>Visible route selection without manual tool choice.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-border/70 bg-background/20 p-4">
                <p className="page-eyebrow text-[10px]">Primary adapter</p>
                <p className="mt-2 font-medium">{session.route_decision.primary_adapter}</p>
                <p className="mt-1 text-xs text-muted-foreground">{session.route_decision.route_label}</p>
              </div>
              <div className="rounded-2xl border border-border/70 bg-background/20 p-4">
                <p className="page-eyebrow text-[10px]">Activation state</p>
                <p className="mt-2 font-medium">{formatLabel(session.route_decision.activation_state)}</p>
                <p className="mt-1 text-xs text-muted-foreground">{session.route_decision.workspace_plan}</p>
              </div>
            </div>
            <div className="rounded-2xl border border-border/70 bg-background/20 p-4">
              <p className="page-eyebrow text-[10px]">Fallback chain</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {session.route_decision.fallback_chain.map((fallback) => (
                  <Badge key={fallback} variant="outline">{fallback}</Badge>
                ))}
              </div>
              <p className="mt-3 text-xs text-muted-foreground">
                Policy basis: {session.route_decision.policy_basis.join(" · ")}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="surface-panel border">
          <CardHeader>
            <CardTitle className="text-lg">Verification</CardTitle>
            <CardDescription>{session.verification_state.summary}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {session.latest_result_packet?.validation.length ? (
              session.latest_result_packet.validation.map((record) => (
                <div key={record.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={badgeVariant(record.status)}>{formatLabel(record.status)}</Badge>
                    <p className="font-medium">{record.label}</p>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">{record.detail}</p>
                </div>
              ))
            ) : (
              <EmptyState
                title="No verification records yet"
                description="Verification records will appear here once the builder route emits evidence."
                className="py-8"
              />
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Card className="surface-panel border">
          <CardHeader>
            <CardTitle className="text-lg">Approval queue</CardTitle>
            <CardDescription>Shadow-mode builder sessions stay approval-gated until the worker bridge is linked.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {session.approvals.length ? (
              session.approvals.map((approval) => (
                <div key={approval.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={badgeVariant(approval.status)}>{formatLabel(approval.status)}</Badge>
                    <Badge variant="outline">{approval.privilege_class}</Badge>
                  </div>
                  <p className="mt-3 text-sm font-medium text-foreground">{approval.requested_action}</p>
                  <p className="mt-2 text-xs leading-5 text-muted-foreground">{approval.reason}</p>
                  {approval.status === "pending" ? (
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button size="sm" onClick={() => onControl("approve", approval.id)} disabled={busyAction !== null}>
                        Approve
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => onControl("reject", approval.id)} disabled={busyAction !== null}>
                        Reject
                      </Button>
                    </div>
                  ) : null}
                </div>
              ))
            ) : (
              <EmptyState title="No approval holds" description="This session does not currently need an explicit builder approval." className="py-8" />
            )}
          </CardContent>
        </Card>

        <Card className="surface-panel border">
          <CardHeader>
            <CardTitle className="text-lg">Result packet</CardTitle>
            <CardDescription>Structured packet transport instead of raw transcript fan-in.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {session.latest_result_packet ? (
              <>
                <div className="rounded-2xl border border-border/70 bg-background/20 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={badgeVariant(session.latest_result_packet.outcome)}>{formatLabel(session.latest_result_packet.outcome)}</Badge>
                    {session.fallback_state ? <Badge variant="outline">{formatLabel(session.fallback_state)}</Badge> : null}
                  </div>
                  <p className="mt-3 text-sm leading-6 text-muted-foreground">{session.latest_result_packet.summary}</p>
                  {session.latest_result_packet.recovery_gate ? (
                    <p className="mt-3 text-xs text-muted-foreground">
                      Recovery gate: {formatLabel(session.latest_result_packet.recovery_gate)}
                    </p>
                  ) : null}
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-border/70 bg-background/20 p-4">
                    <p className="page-eyebrow text-[10px]">Changed files</p>
                    {session.latest_result_packet.files_changed.length ? (
                      <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                        {session.latest_result_packet.files_changed.map((path) => (
                          <li key={path}>{path}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-2 text-xs text-muted-foreground">No changed files recorded yet.</p>
                    )}
                  </div>
                  <div className="rounded-2xl border border-border/70 bg-background/20 p-4">
                    <p className="page-eyebrow text-[10px]">Remaining risks</p>
                    {session.latest_result_packet.remaining_risks.length ? (
                      <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                        {session.latest_result_packet.remaining_risks.map((risk) => (
                          <li key={risk}>{risk}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-2 text-xs text-muted-foreground">No remaining risks recorded.</p>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <EmptyState title="No result packet yet" description="The builder kernel will attach a structured result packet once the route emits output." className="py-8" />
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="surface-panel border">
        <CardHeader>
          <CardTitle className="text-lg">Progress timeline</CardTitle>
          <CardDescription>Structured progress events and recovery notices for the selected session.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {events.length ? (
            events.map((event) => (
              <div key={event.id} className="rounded-2xl border border-border/70 bg-background/20 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={badgeVariant(event.tone === "danger" ? "failed" : event.tone === "warning" ? "planned" : "completed")}>
                    {formatLabel(event.tone)}
                  </Badge>
                  <p className="font-medium">{event.label}</p>
                  <span className="text-xs text-muted-foreground">{formatRelativeTime(event.timestamp)}</span>
                </div>
                <p className="mt-2 text-xs leading-5 text-muted-foreground">{event.detail}</p>
              </div>
            ))
          ) : (
            <EmptyState title="No progress events" description="Session events will appear here after intake begins." className="py-8" />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export function BuilderConsole() {
  const queryClient = useQueryClient();
  const { getSearchValue, setSearchValue } = useUrlState();
  const selectedSessionId = getSearchValue("session", "");

  const [goal, setGoal] = useState("Implement the first builder front-door Codex route with structured state.");
  const [taskClass, setTaskClass] = useState<BuilderTaskClass>("multi_file_implementation");
  const [sensitivityClass, setSensitivityClass] = useState<BuilderSensitivityClass>("private_but_cloud_allowed");
  const [workspaceMode, setWorkspaceMode] = useState<BuilderWorkspaceMode>("repo_worktree");
  const [needsBackground, setNeedsBackground] = useState(false);
  const [needsGithub, setNeedsGithub] = useState(false);
  const [acceptanceCriteriaText, setAcceptanceCriteriaText] = useState(
    "Create and persist a builder session\nExpose the chosen route in the builder console\nShow verification and approval state",
  );
  const [surfaceError, setSurfaceError] = useState<string | null>(null);

  const summaryQuery = useQuery({
    queryKey: queryKeys.builderSummary,
    queryFn: getBuilderSummary,
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
  });

  const sessionQuery = useQuery({
    queryKey: queryKeys.builderSession(selectedSessionId),
    queryFn: () => getBuilderSession(selectedSessionId),
    enabled: Boolean(selectedSessionId),
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
  });

  const eventsQuery = useQuery({
    queryKey: queryKeys.builderSessionEvents(selectedSessionId),
    queryFn: () => getBuilderSessionEvents(selectedSessionId),
    enabled: Boolean(selectedSessionId),
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
  });

  useEffect(() => {
    if (!selectedSessionId && summaryQuery.data?.current_session?.id) {
      setSearchValue("session", summaryQuery.data.current_session.id);
    }
  }, [selectedSessionId, setSearchValue, summaryQuery.data?.current_session?.id]);

  const createMutation = useMutation({
    mutationFn: async () =>
      createBuilderSession({
        goal,
        task_class: taskClass,
        sensitivity_class: sensitivityClass,
        workspace_mode: workspaceMode,
        needs_background: needsBackground,
        needs_github: needsGithub,
        acceptance_criteria: buildAcceptanceCriteria(acceptanceCriteriaText, goal),
      }),
    onSuccess: async (session) => {
      setSurfaceError(null);
      await queryClient.invalidateQueries({ queryKey: queryKeys.builderSummary });
      setSearchValue("session", session.id);
    },
    onError: (error) => {
      setSurfaceError(error instanceof Error ? error.message : "Failed to create builder session.");
    },
  });

  const controlMutation = useMutation({
    mutationFn: async ({ action, approvalId }: { action: BuilderControlAction; approvalId?: string | null }) =>
      controlBuilderSession(selectedSessionId, {
        action,
        approval_id: approvalId ?? null,
      }),
    onSuccess: async (result, variables) => {
      setSurfaceError(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.builderSummary }),
        queryClient.invalidateQueries({ queryKey: queryKeys.builderSession(selectedSessionId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.builderSessionEvents(selectedSessionId) }),
      ]);
      if (variables.action === "open_terminal" && result.terminal_href) {
        window.location.assign(result.terminal_href);
      }
    },
    onError: (error) => {
      setSurfaceError(error instanceof Error ? error.message : "Failed to update builder session.");
    },
  });

  const selectedSession = sessionQuery.data ?? null;
  const events = eventsQuery.data?.events ?? [];
  const sessions = summaryQuery.data?.sessions ?? [];
  const busyAction = controlMutation.isPending ? controlMutation.variables?.action ?? null : null;
  const selectedSummary = useMemo(
    () => sessions.find((session) => session.id === selectedSessionId) ?? null,
    [selectedSessionId, sessions],
  );

  if (summaryQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Build" title="Builder" description="The builder front door failed to load." />
        <ErrorPanel
          description={
            summaryQuery.error instanceof Error ? summaryQuery.error.message : "Failed to load builder summary."
          }
        />
      </div>
    );
  }

  const summary = summaryQuery.data;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Build"
        title="Builder"
        description="Canonical builder intake, route selection, approvals, artifacts, and recovery under the Athanor command-center shell."
        attentionHref="/builder"
        actions={
          <Button
            variant="outline"
            onClick={() =>
              void Promise.all([
                summaryQuery.refetch(),
                selectedSessionId ? sessionQuery.refetch() : Promise.resolve(),
                selectedSessionId ? eventsQuery.refetch() : Promise.resolve(),
              ])
            }
            disabled={summaryQuery.isFetching || sessionQuery.isFetching || eventsQuery.isFetching}
          >
            <RefreshCcw className={`mr-2 h-4 w-4 ${summaryQuery.isFetching || sessionQuery.isFetching || eventsQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Sessions" value={`${summary?.session_count ?? 0}`} detail="Tracked builder sessions." icon={<Hammer className="h-5 w-5" />} />
          <StatCard label="Active" value={`${summary?.active_count ?? 0}`} detail="Queued, running, or approval-held sessions." />
          <StatCard label="Approvals" value={`${summary?.pending_approval_count ?? 0}`} detail="Builder-specific approval holds." icon={<ShieldCheck className="h-5 w-5" />} />
          <StatCard label="Artifacts" value={`${summary?.recent_artifact_count ?? 0}`} detail="Artifacts on the current session." icon={<Workflow className="h-5 w-5" />} />
        </div>
      </PageHeader>

      {surfaceError ? <ErrorPanel title="Builder feedback" description={surfaceError} /> : null}
      {summary?.degraded ? <ErrorPanel title="Builder summary degraded" description={summary.detail ?? "Builder summary is temporarily degraded."} /> : null}

      <div className="grid gap-5 xl:grid-cols-[0.92fr_1.08fr]">
        <div className="space-y-4">
          <Card className="surface-panel border">
            <CardHeader>
              <CardTitle className="text-lg">Start a builder session</CardTitle>
              <CardDescription>Intake one goal and let the builder route decide the worker lane underneath.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <label className="block space-y-2">
                <span className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">Goal</span>
                <textarea
                  value={goal}
                  onChange={(event) => setGoal(event.target.value)}
                  rows={4}
                  className="w-full rounded-2xl border border-border/70 bg-background/30 px-3 py-2.5 text-sm outline-none transition focus:border-primary"
                />
              </label>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="block space-y-2">
                  <span className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">Task class</span>
                  <select
                    value={taskClass}
                    onChange={(event) => setTaskClass(event.target.value as BuilderTaskClass)}
                    className="w-full rounded-2xl border border-border/70 bg-background/30 px-3 py-2.5 text-sm outline-none transition focus:border-primary"
                  >
                    {TASK_CLASS_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block space-y-2">
                  <span className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">Sensitivity</span>
                  <select
                    value={sensitivityClass}
                    onChange={(event) => setSensitivityClass(event.target.value as BuilderSensitivityClass)}
                    className="w-full rounded-2xl border border-border/70 bg-background/30 px-3 py-2.5 text-sm outline-none transition focus:border-primary"
                  >
                    {SENSITIVITY_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="block space-y-2">
                  <span className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">Workspace</span>
                  <select
                    value={workspaceMode}
                    onChange={(event) => setWorkspaceMode(event.target.value as BuilderWorkspaceMode)}
                    className="w-full rounded-2xl border border-border/70 bg-background/30 px-3 py-2.5 text-sm outline-none transition focus:border-primary"
                  >
                    {WORKSPACE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="grid gap-2">
                  <label className="flex items-center gap-2 rounded-2xl border border-border/70 bg-background/20 px-3 py-2 text-sm">
                    <input type="checkbox" checked={needsBackground} onChange={(event) => setNeedsBackground(event.target.checked)} />
                    Needs background execution
                  </label>
                  <label className="flex items-center gap-2 rounded-2xl border border-border/70 bg-background/20 px-3 py-2 text-sm">
                    <input type="checkbox" checked={needsGithub} onChange={(event) => setNeedsGithub(event.target.checked)} />
                    Needs GitHub async flow
                  </label>
                </div>
              </div>

              <label className="block space-y-2">
                <span className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">Acceptance criteria</span>
                <textarea
                  value={acceptanceCriteriaText}
                  onChange={(event) => setAcceptanceCriteriaText(event.target.value)}
                  rows={4}
                  className="w-full rounded-2xl border border-border/70 bg-background/30 px-3 py-2.5 text-sm outline-none transition focus:border-primary"
                />
              </label>

              <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending || !goal.trim()} className="w-full justify-between">
                Start builder session
                <Hammer className="h-4 w-4" />
              </Button>
            </CardContent>
          </Card>

          <Card className="surface-panel border">
            <CardHeader>
              <CardTitle className="text-lg">Recent sessions</CardTitle>
              <CardDescription>Query-param session selection keeps deep links stable at `/builder?session=&lt;id&gt;`.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {sessions.length ? (
                sessions.map((session) => (
                  <SessionCard
                    key={session.id}
                    session={session}
                    selected={session.id === selectedSessionId}
                    onSelect={() => setSearchValue("session", session.id)}
                  />
                ))
              ) : (
                <EmptyState title="No builder sessions yet" description="Start the first builder session to establish route state, approvals, and structured packets." className="py-8" />
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          {selectedSessionId && sessionQuery.isLoading ? (
            <Card className="surface-panel border">
              <CardContent className="py-10 text-sm text-muted-foreground">Loading builder session…</CardContent>
            </Card>
          ) : null}

          {!selectedSession && !selectedSummary ? (
            <EmptyState
              title="Select a builder session"
              description="The command center can launch the builder surface directly into the current session, or you can start a new one from the intake form."
              action={
                <Button asChild variant="outline">
                  <Link href="/">Back to command center</Link>
                </Button>
              }
            />
          ) : null}

          {selectedSession ? (
            <SessionSurface
              session={selectedSession}
              events={events}
              busyAction={busyAction}
              onControl={(action, approvalId) => controlMutation.mutate({ action, approvalId })}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
