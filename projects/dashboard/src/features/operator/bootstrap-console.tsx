"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeftRight, Bot, CircleAlert, FileText, GitBranch, PlayCircle, ShieldAlert, Wrench } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { requestJson } from "@/features/workforce/helpers";
import { isOperatorSessionLocked, useOperatorSessionStatus } from "@/lib/operator-session";

interface BootstrapNextAction {
  kind: string;
  family: string;
  slice_id: string;
  host_id?: string;
  worktree_required?: boolean;
  approval_class?: string;
  blocking_packet_id?: string;
  open_blocker_ids?: string[];
}

interface BootstrapProgram {
  id: string;
  label: string;
  objective: string;
  phase_scope: string;
  status: string;
  current_family: string;
  next_slice_id: string;
  recommended_host_id: string;
  waiting_on_approval_family?: string;
  waiting_on_approval_slice_id?: string;
  next_action?: BootstrapNextAction | null;
  pending_integrations: number;
  slice_counts: {
    total: number;
    queued: number;
    active: number;
    blocked: number;
    completed: number;
  };
}

interface BootstrapSlice {
  id: string;
  program_id: string;
  family: string;
  objective: string;
  status: string;
  host_id: string;
  validation_status: string;
  next_step: string;
}

interface BootstrapHandoff {
  id: string;
  slice_id: string;
  from_host: string;
  to_host: string;
  stop_reason: string;
  next_step: string;
}

interface BootstrapBlocker {
  id: string;
  family: string;
  blocker_class: string;
  reason: string;
  approval_required: boolean;
  inbox_id: string;
}

interface BootstrapApprovalContext {
  kind: string;
  family: string;
  slice_id: string;
  approval_class: string;
  packet_id: string;
  packet_label: string;
  approval_authority: string;
  open_blocker_ids: string[];
  follow_on_slice_id: string;
  summary: string;
  unlocks: string;
  operator_instruction: string;
  review_artifacts: string[];
  exact_steps: string[];
  rollback_steps: string[];
}

interface BootstrapStatusPayload {
  mode: string;
  authority?: string;
  sqlite_ready: boolean;
  mirror_ready: boolean;
  mirror_configured?: boolean;
  program_count: number;
  slice_count: number;
  open_blockers: number;
  busy_hosts: number;
  pending_integrations: number;
  active_program_id: string;
  active_family: string;
  next_slice_id: string;
  recommended_host_id: string;
  waiting_on_approval_family?: string;
  waiting_on_approval_slice_id?: string;
  next_action?: BootstrapNextAction | null;
  approval_context?: BootstrapApprovalContext | null;
  control_artifacts?: {
    snapshot_path?: string;
    approval_packet_registry_path?: string;
    durable_persistence_packet_path?: string;
    durable_state_sql_path?: string;
  };
  hosts: Array<{ id: string; status: string; active_slice_id: string; last_reason: string }>;
  takeover: {
    ready: boolean;
    blocker_ids: string[];
    criteria: Array<{ id: string; label: string; passed: boolean; detail: string }>;
    governance_drills?: {
      evidence_complete?: boolean;
      all_green?: boolean;
      drills?: Array<{
        drill_id: string;
        artifact_status?: string;
        evidence_present?: boolean;
        passed?: boolean;
        detail?: string;
      }>;
    };
  };
}

interface BootstrapProgramsResponse {
  programs: BootstrapProgram[];
  count: number;
  status: BootstrapStatusPayload;
  takeover: BootstrapStatusPayload["takeover"];
}

interface BootstrapIntegration {
  id: string;
  slice_id: string;
  family: string;
  method: string;
  target_ref: string;
  status: string;
  priority: number;
}

interface BootstrapApproveResponse {
  status: string;
  program: BootstrapProgram;
  snapshot: BootstrapStatusPayload;
  takeover: BootstrapStatusPayload["takeover"];
  approved_packet_id: string;
  approved_slice_ids: string[];
  resolved_blocker_ids: string[];
  recommendation?: BootstrapNextAction | null;
  next_action?: BootstrapNextAction | null;
  already_approved?: boolean;
}

type ApproveFeedback =
  | {
      tone: "success";
      message: string;
    }
  | {
      tone: "error";
      message: string;
    };

function toneForFlag(value: boolean) {
  return value ? "default" : "outline";
}

export function BootstrapConsole() {
  const session = useOperatorSessionStatus();
  const sessionLocked = isOperatorSessionLocked(session);
  const queryClient = useQueryClient();
  const [unlockToken, setUnlockToken] = useState("");
  const [approveFeedback, setApproveFeedback] = useState<ApproveFeedback | null>(null);
  const programsQuery = useQuery({
    queryKey: ["bootstrap-programs"],
    queryFn: async (): Promise<BootstrapProgramsResponse> => {
      return requestJson("/api/bootstrap/programs") as Promise<BootstrapProgramsResponse>;
    },
    refetchInterval: 20_000,
  });

  const slicesQuery = useQuery({
    queryKey: ["bootstrap-slices"],
    queryFn: async (): Promise<BootstrapSlice[]> => {
      const data = await requestJson("/api/bootstrap/slices");
      return (data?.slices ?? []) as BootstrapSlice[];
    },
    refetchInterval: 20_000,
  });

  const handoffsQuery = useQuery({
    queryKey: ["bootstrap-handoffs"],
    queryFn: async (): Promise<BootstrapHandoff[]> => {
      const data = await requestJson("/api/bootstrap/handoffs");
      return (data?.handoffs ?? []) as BootstrapHandoff[];
    },
    refetchInterval: 20_000,
  });

  const blockersQuery = useQuery({
    queryKey: ["bootstrap-blockers"],
    queryFn: async (): Promise<BootstrapBlocker[]> => {
      const data = await requestJson("/api/bootstrap/blockers");
      return (data?.blockers ?? []) as BootstrapBlocker[];
    },
    refetchInterval: 20_000,
  });

  const integrationsQuery = useQuery({
    queryKey: ["bootstrap-integrations"],
    queryFn: async (): Promise<BootstrapIntegration[]> => {
      const data = await requestJson("/api/bootstrap/integrations");
      return (data?.integrations ?? []) as BootstrapIntegration[];
    },
    refetchInterval: 20_000,
  });

  const programs = programsQuery.data?.programs ?? [];
  const status = programsQuery.data?.status;
  const takeover = programsQuery.data?.takeover;
  const slices = slicesQuery.data ?? [];
  const handoffs = handoffsQuery.data ?? [];
  const blockers = blockersQuery.data ?? [];
  const integrations = integrationsQuery.data ?? [];
  const approvalContext = status?.approval_context;
  const approvalBlockers = approvalContext?.open_blocker_ids?.length
    ? blockers.filter((blocker) => approvalContext.open_blocker_ids.includes(blocker.id))
    : [];
  const unlockMutation = useMutation({
    mutationFn: async (): Promise<{ ok: boolean; unlocked: boolean }> => {
      const token = unlockToken.trim();
      if (!token) {
        throw new Error("Operator token is required to unlock this action.");
      }
      return requestJson("/api/operator/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      }) as Promise<{ ok: boolean; unlocked: boolean }>;
    },
    onSuccess: () => {
      setUnlockToken("");
      queryClient.invalidateQueries({ queryKey: ["operator-session-status"] }).catch(() => undefined);
    },
  });
  const approveMutation = useMutation({
    mutationFn: async (): Promise<BootstrapApproveResponse> => {
      const programId = status?.active_program_id ?? "";
      const packetId = approvalContext?.packet_id ?? "";
      if (!programId || !packetId) {
        throw new Error("No approval packet is currently available.");
      }
      return requestJson(`/api/bootstrap/programs/${encodeURIComponent(programId)}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          packet_id: packetId,
          reason: `Approved bootstrap packet ${packetId} from /bootstrap`,
        }),
      }) as Promise<BootstrapApproveResponse>;
    },
    onMutate: () => {
      setApproveFeedback(null);
    },
    onSuccess: (result) => {
      setApproveFeedback({
        tone: "success",
        message: result?.already_approved
          ? `Approval for ${result.approved_packet_id} was already recorded. Bootstrap state has been refreshed.`
          : `Approval recorded for ${result?.approved_packet_id ?? approvalContext?.packet_id ?? "the packet"}. Bootstrap state has been refreshed.`,
      });
      queryClient.setQueryData<BootstrapProgramsResponse | undefined>(["bootstrap-programs"], (current) => {
        if (!current) {
          return current;
        }
        return {
          ...current,
          programs: current.programs.map((program) => (program.id === result.program.id ? { ...program, ...result.program } : program)),
          status: result.snapshot,
          takeover: result.takeover,
        };
      });
      queryClient.invalidateQueries({ queryKey: ["bootstrap-programs"] }).catch(() => undefined);
      queryClient.invalidateQueries({ queryKey: ["bootstrap-slices"] }).catch(() => undefined);
      queryClient.invalidateQueries({ queryKey: ["bootstrap-blockers"] }).catch(() => undefined);
      queryClient.invalidateQueries({ queryKey: ["bootstrap-integrations"] }).catch(() => undefined);
    },
    onError: async (error) => {
      const attemptedPacketId = approvalContext?.packet_id ?? "";
      try {
        const refreshed = (await queryClient.fetchQuery({
          queryKey: ["bootstrap-programs"],
          queryFn: async (): Promise<BootstrapProgramsResponse> => {
            return requestJson("/api/bootstrap/programs") as Promise<BootstrapProgramsResponse>;
          },
        })) as BootstrapProgramsResponse;
        const refreshedApprovalPacketId = refreshed?.status?.approval_context?.packet_id ?? "";
        const activeProgram = (refreshed?.programs ?? []).find(
          (program) => program.id === (status?.active_program_id ?? "")
        );
        const advancedPastPacket =
          Boolean(attemptedPacketId) &&
          refreshedApprovalPacketId !== attemptedPacketId &&
          !activeProgram?.waiting_on_approval_family &&
          !activeProgram?.waiting_on_approval_slice_id;
        if (advancedPastPacket) {
          setApproveFeedback({
            tone: "success",
            message: `Approval for ${attemptedPacketId} was already recorded. Bootstrap state has been refreshed.`,
          });
          return;
        }
      } catch {
        // Fall through to the original error.
      }

      setApproveFeedback({
        tone: "error",
        message:
          error instanceof Error
            ? error.message
            : "Failed to record bootstrap approval.",
      });
    },
  });

  if (programsQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Recursive Builder" title="Bootstrap Stack" description="The recursive builder stack failed to load." attentionHref="/bootstrap" />
        <ErrorPanel description={programsQuery.error instanceof Error ? programsQuery.error.message : "Failed to load bootstrap builder state."} />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Recursive Builder"
        title="Bootstrap Stack"
        description="External builder hosts, slice relay, integration queue posture, and explicit takeover readiness."
        attentionHref="/bootstrap"
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Programs" value={`${status?.program_count ?? programs.length}`} detail="Active bootstrap programs under the hybrid ledger." icon={<GitBranch className="h-5 w-5" />} />
          <StatCard label="Slices" value={`${status?.slice_count ?? slices.length}`} detail={`${status?.busy_hosts ?? 0} hosts are currently busy.`} icon={<Bot className="h-5 w-5" />} />
          <StatCard label="Open blockers" value={`${status?.open_blockers ?? blockers.length}`} detail={`${handoffs.length} recorded handoffs in the relay ledger.`} tone={(status?.open_blockers ?? blockers.length) > 0 ? "warning" : "success"} icon={<ShieldAlert className="h-5 w-5" />} />
          <StatCard label="Takeover" value={takeover?.ready ? "Ready" : "Blocked"} detail={`${takeover?.blocker_ids.length ?? 0} takeover blockers remain.`} tone={takeover?.ready ? "success" : "warning"} icon={<ArrowLeftRight className="h-5 w-5" />} />
        </div>
      </PageHeader>

      {approvalContext?.kind === "approval_required" ? (
        <Card className="surface-panel border-amber-500/40">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <CircleAlert className="h-5 w-5" />
              Approval Required
            </CardTitle>
            <CardDescription>
              The bootstrap program is paused on an ask-first boundary. Review the packet, then approve the maintenance window so the durable cutover can proceed.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">{approvalContext.packet_label}</Badge>
              <Badge variant="outline">{approvalContext.family}</Badge>
              <Badge variant="outline">{approvalContext.slice_id}</Badge>
              {approvalContext.follow_on_slice_id ? <Badge variant="outline">{`then ${approvalContext.follow_on_slice_id}`}</Badge> : null}
            </div>

            <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
              <div className="space-y-4">
                <div>
                  <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                    <PlayCircle className="h-4 w-4" />
                    What approval means
                  </div>
                  <p className="text-sm text-muted-foreground">{approvalContext.summary}</p>
                  <p className="mt-2 text-sm text-muted-foreground">{approvalContext.unlocks}</p>
                </div>

                <div>
                  <div className="mb-2 text-sm font-medium">Approve with this instruction</div>
                  <div className="rounded-2xl border border-border/70 bg-muted/30 p-3 text-sm font-mono break-all">
                    {approvalContext.operator_instruction}
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Approval authority: {approvalContext.approval_authority}
                  </p>
                  {sessionLocked ? (
                    <div className="mt-3 space-y-3 rounded-2xl border border-amber-500/40 bg-amber-500/5 p-3">
                      <div className="text-sm font-medium">Unlock operator session</div>
                      <p className="text-xs text-muted-foreground">
                        This mutation is locked until the operator session is unlocked in this browser.
                      </p>
                      <div className="flex flex-col gap-3 md:flex-row">
                        <Input
                          type="password"
                          value={unlockToken}
                          onChange={(event) => setUnlockToken(event.target.value)}
                          placeholder="Operator token"
                          autoComplete="current-password"
                        />
                        <Button
                          type="button"
                          size="sm"
                          onClick={() => unlockMutation.mutate()}
                          disabled={unlockMutation.isPending || !unlockToken.trim()}
                        >
                          {unlockMutation.isPending ? "Unlocking..." : "Unlock session"}
                        </Button>
                      </div>
                      {unlockMutation.isError ? (
                        <p className="text-sm text-destructive">
                          {unlockMutation.error instanceof Error ? unlockMutation.error.message : "Failed to unlock operator session."}
                        </p>
                      ) : null}
                      {unlockMutation.isSuccess ? (
                        <p className="text-sm text-emerald-600 dark:text-emerald-400">
                          Operator session unlocked. Approval controls are ready.
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                  <div className="mt-3 flex flex-wrap items-center gap-3">
                    <Button
                      type="button"
                      size="sm"
                      onClick={() => approveMutation.mutate()}
                      disabled={
                        approveMutation.isPending ||
                        sessionLocked ||
                        !status?.active_program_id ||
                        !approvalContext.packet_id
                      }
                    >
                      {approveMutation.isPending ? "Recording approval..." : "Approve packet"}
                    </Button>
                    <p className="text-xs text-muted-foreground">
                      {sessionLocked
                        ? "Unlock the operator session first. The runtime/schema cutover still runs as a separate controlled step."
                        : "This records operator approval in bootstrap truth. The runtime/schema cutover still runs as a separate controlled step."}
                    </p>
                  </div>
                  {approveFeedback?.tone === "error" ? (
                    <p className="mt-2 text-sm text-destructive">
                      {approveFeedback.message}
                    </p>
                  ) : null}
                  {approveFeedback?.tone === "success" ? (
                    <p className="mt-2 text-sm text-emerald-600 dark:text-emerald-400">
                      {approveFeedback.message}
                    </p>
                  ) : null}
                </div>

                {approvalBlockers.length > 0 ? (
                  <div>
                    <div className="mb-2 text-sm font-medium">Blocking records</div>
                    <div className="space-y-2">
                      {approvalBlockers.map((blocker) => (
                        <div key={blocker.id} className="rounded-xl border border-border/70 px-3 py-2 text-xs text-muted-foreground">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant="outline">{blocker.id}</Badge>
                            <Badge variant="secondary">{blocker.blocker_class}</Badge>
                          </div>
                          <p className="mt-2">{blocker.reason}</p>
                          {blocker.inbox_id ? <p className="mt-1">{`Inbox: ${blocker.inbox_id}`}</p> : null}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>

              <div className="space-y-4">
                <div>
                  <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                    <FileText className="h-4 w-4" />
                    Review artifacts
                  </div>
                  <div className="space-y-2">
                    {approvalContext.review_artifacts.map((artifactPath) => (
                      <div key={artifactPath} className="rounded-xl border border-border/70 px-3 py-2 text-xs text-muted-foreground">
                        <code className="break-all">{artifactPath}</code>
                      </div>
                    ))}
                  </div>
                </div>

                {approvalContext.exact_steps.length > 0 ? (
                  <div>
                    <div className="mb-2 text-sm font-medium">Execution steps after approval</div>
                    <ol className="space-y-2 text-sm text-muted-foreground">
                      {approvalContext.exact_steps.map((step) => (
                        <li key={step} className="rounded-xl border border-border/70 px-3 py-2">
                          {step}
                        </li>
                      ))}
                    </ol>
                  </div>
                ) : null}

                {approvalContext.rollback_steps.length > 0 ? (
                  <div>
                    <div className="mb-2 text-sm font-medium">Rollback posture</div>
                    <ol className="space-y-2 text-sm text-muted-foreground">
                      {approvalContext.rollback_steps.map((step) => (
                        <li key={step} className="rounded-xl border border-border/70 px-3 py-2">
                          {step}
                        </li>
                      ))}
                    </ol>
                  </div>
                ) : null}
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <Card className="surface-panel">
          <CardHeader>
            <CardTitle className="text-lg">Programs</CardTitle>
            <CardDescription>Program order, live family focus, and slice counts for the external bootstrap layer.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {programs.length > 0 ? (
              programs.map((program) => (
                <div key={program.id} className="surface-tile rounded-2xl border p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">{program.status}</Badge>
                    <Badge variant="outline">{program.phase_scope}</Badge>
                    {program.current_family ? <Badge variant="outline">{program.current_family}</Badge> : null}
                    {program.recommended_host_id ? <Badge variant="outline">{`next host ${program.recommended_host_id}`}</Badge> : null}
                  </div>
                  <p className="mt-3 font-medium">{program.label}</p>
                  <p className="mt-2 text-sm text-muted-foreground">{program.objective}</p>
                  <div className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-4">
                    <span>{`queued ${program.slice_counts.queued}`}</span>
                    <span>{`active ${program.slice_counts.active}`}</span>
                    <span>{`blocked ${program.slice_counts.blocked}`}</span>
                    <span>{`completed ${program.slice_counts.completed}`}</span>
                  </div>
                  {program.next_slice_id ? <p className="mt-3 text-xs text-muted-foreground">{`Next slice: ${program.next_slice_id}`}</p> : null}
                  {!program.next_slice_id && program.waiting_on_approval_slice_id ? (
                    <p className="mt-3 text-xs text-muted-foreground">{`Awaiting approval: ${program.waiting_on_approval_slice_id}`}</p>
                  ) : null}
                  {program.pending_integrations ? <p className="mt-1 text-xs text-muted-foreground">{`Pending integrations: ${program.pending_integrations}`}</p> : null}
                </div>
              ))
            ) : (
              <EmptyState title="No bootstrap programs" description="The bootstrap registry has not seeded any programs yet." className="py-10" />
            )}
          </CardContent>
        </Card>

        <Card className="surface-panel">
          <CardHeader>
            <CardTitle className="text-lg">Hosts</CardTitle>
            <CardDescription>External builder hosts and their current relay posture.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {(status?.hosts ?? []).length > 0 ? (
              (status?.hosts ?? []).map((host) => (
                <div key={host.id} className="surface-tile rounded-2xl border p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={host.status === "busy" ? "secondary" : "outline"}>{host.status}</Badge>
                    <span className="text-sm font-medium">{host.id}</span>
                  </div>
                  {host.active_slice_id ? <p className="mt-2 text-xs text-muted-foreground">{`Active slice: ${host.active_slice_id}`}</p> : null}
                  {host.last_reason ? <p className="mt-1 text-xs text-muted-foreground">{host.last_reason}</p> : null}
                </div>
              ))
            ) : (
              <EmptyState title="No host state" description="Bootstrap host state has not been initialized yet." className="py-10" />
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-4">
        <Card className="surface-panel">
          <CardHeader>
            <CardTitle className="text-lg">Open slices</CardTitle>
            <CardDescription>Ready, claimed, and handed-off work across the bootstrap loop.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {slices.length > 0 ? (
              slices.slice(0, 8).map((slice) => (
                <div key={slice.id} className="surface-tile rounded-2xl border p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{slice.status}</Badge>
                    <Badge variant="secondary">{slice.family}</Badge>
                  </div>
                  <p className="mt-3 font-medium">{slice.id}</p>
                  <p className="mt-2 text-sm text-muted-foreground">{slice.objective}</p>
                  <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
                    {slice.host_id ? <span>{`host ${slice.host_id}`}</span> : null}
                    <span>{`validation ${slice.validation_status}`}</span>
                  </div>
                  {slice.next_step ? <p className="mt-2 text-xs text-muted-foreground">{slice.next_step}</p> : null}
                </div>
              ))
            ) : (
              <EmptyState title="No slices" description="The bootstrap slice ledger is empty." className="py-10" />
            )}
          </CardContent>
        </Card>

        <Card className="surface-panel">
          <CardHeader>
            <CardTitle className="text-lg">Integration queue</CardTitle>
            <CardDescription>Validated slices waiting for serial replay onto the main integration lane.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {integrations.length > 0 ? (
              integrations.slice(0, 6).map((integration) => (
                <div key={integration.id} className="surface-tile rounded-2xl border p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{integration.status}</Badge>
                    <Badge variant="secondary">{integration.family}</Badge>
                  </div>
                  <p className="mt-3 font-medium">{integration.slice_id}</p>
                  <p className="mt-2 text-xs text-muted-foreground">{`${integration.method} -> ${integration.target_ref}`}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{`priority ${integration.priority}`}</p>
                </div>
              ))
            ) : (
              <EmptyState title="No integrations queued" description="No validated slices are waiting for the serial integration lane." className="py-10" />
            )}
          </CardContent>
        </Card>

        <Card className="surface-panel">
          <CardHeader>
            <CardTitle className="text-lg">Relay ledger</CardTitle>
            <CardDescription>Most recent host handoffs in the external builder stack.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {handoffs.length > 0 ? (
              handoffs.slice(0, 6).map((handoff) => (
                <div key={handoff.id} className="surface-tile rounded-2xl border p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{handoff.slice_id}</Badge>
                    <Badge variant="secondary">{`${handoff.from_host} -> ${handoff.to_host}`}</Badge>
                  </div>
                  {handoff.stop_reason ? <p className="mt-3 text-sm text-muted-foreground">{handoff.stop_reason}</p> : null}
                  {handoff.next_step ? <p className="mt-2 text-xs text-muted-foreground">{handoff.next_step}</p> : null}
                </div>
              ))
            ) : (
              <EmptyState title="No handoffs yet" description="The relay ledger has not recorded any host swaps." className="py-10" />
            )}
          </CardContent>
        </Card>

        <Card className="surface-panel">
          <CardHeader>
            <CardTitle className="text-lg">Takeover blockers</CardTitle>
            <CardDescription>Explicit criteria that still prevent the internal builder from becoming primary.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {(takeover?.criteria ?? []).length > 0 ? (
              (takeover?.criteria ?? []).map((criterion) => (
                <div key={criterion.id} className="surface-tile rounded-2xl border p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={toneForFlag(criterion.passed)}>{criterion.passed ? "green" : "blocked"}</Badge>
                    <span className="text-sm font-medium">{criterion.label}</span>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">{criterion.detail}</p>
                </div>
              ))
            ) : (
              <EmptyState title="No takeover criteria" description="The bootstrap takeover registry did not return any criteria." className="py-10" />
            )}

            {blockers.length > 0 ? (
              <div className="pt-2">
                <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                  <Wrench className="h-4 w-4" />
                  Active blockers
                </div>
                <div className="space-y-2">
                  {blockers.slice(0, 5).map((blocker) => (
                    <div key={blocker.id} className="rounded-xl border border-border/70 px-3 py-2 text-xs text-muted-foreground">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="outline">{blocker.family}</Badge>
                        <Badge variant="secondary">{blocker.blocker_class}</Badge>
                      </div>
                      <p className="mt-2">{blocker.reason}</p>
                      {blocker.approval_required ? <p className="mt-1">{`Inbox: ${blocker.inbox_id || "pending"}`}</p> : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {(takeover?.governance_drills?.drills ?? []).length > 0 ? (
              <div className="pt-2">
                <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                  <ShieldAlert className="h-4 w-4" />
                  Governance drills
                </div>
                <div className="space-y-2">
                  {(takeover?.governance_drills?.drills ?? []).map((drill) => (
                    <div key={drill.drill_id} className="rounded-xl border border-border/70 px-3 py-2 text-xs text-muted-foreground">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant={toneForFlag(Boolean(drill.passed))}>{drill.artifact_status ?? (drill.evidence_present ? "recorded" : "missing")}</Badge>
                        <Badge variant="outline">{drill.drill_id}</Badge>
                      </div>
                      {drill.detail ? <p className="mt-2">{drill.detail}</p> : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
