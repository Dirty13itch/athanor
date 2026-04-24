"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FolderRoot,
  RefreshCcw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { requestJson } from "@/features/workforce/helpers";
import { formatRelativeTime } from "@/lib/format";
import type {
  CommandCenterFinalFormGap,
  ProjectFactoryConsoleSnapshot,
  ProjectFactoryProjectRecord,
} from "@/lib/project-factory";
import { cn } from "@/lib/utils";

function humanize(value: string) {
  return value.replaceAll("_", " ");
}

function badgeVariantForReadiness(readinessTier: string) {
  if (readinessTier === "ready_now" || readinessTier === "eligible_now") {
    return "secondary" as const;
  }
  if (readinessTier === "policy_blocked" || readinessTier === "core_gate_hold") {
    return "outline" as const;
  }
  return "outline" as const;
}

function toneClassForBuild(buildHealth: string) {
  if (buildHealth === "passed") return "text-[color:var(--signal-success)]";
  if (buildHealth === "failed") return "text-[color:var(--signal-danger)]";
  return "text-[color:var(--signal-warning)]";
}

function severityToneClass(severity: string) {
  if (severity === "critical" || severity === "high") return "text-[color:var(--signal-danger)]";
  if (severity === "medium") return "text-[color:var(--signal-warning)]";
  return "text-[color:var(--signal-success)]";
}

function ArtifactRefs({
  label,
  refs,
}: {
  label: string;
  refs: string[];
}) {
  if (refs.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      <p className="page-eyebrow text-[10px]">{label}</p>
      <div className="space-y-1.5">
        {refs.slice(0, 4).map((ref) => (
          <p key={ref} className="truncate font-mono text-xs text-muted-foreground">
            {ref}
          </p>
        ))}
      </div>
    </div>
  );
}

function ProjectLanePanel({ project }: { project: ProjectFactoryProjectRecord }) {
  return (
    <article className="surface-panel rounded-[28px] border px-5 py-5 sm:px-6">
      <div className="flex flex-col gap-4 border-b border-border/70 pb-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <p className="page-eyebrow text-[10px]">
              {project.isTopPriority ? "Top governed lane" : project.isFirstClass ? "First-class governed lane" : "Baseline lane"}
            </p>
            {project.isTopPriority ? <Badge>top priority</Badge> : null}
            <Badge variant={badgeVariantForReadiness(project.readinessTier)}>{humanize(project.readinessTier)}</Badge>
          </div>
          <div>
            <h2 className="font-heading text-2xl font-medium tracking-[-0.03em] text-foreground">
              {project.label}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {humanize(project.projectClass)} · {humanize(project.platformClass)} · {humanize(project.routingClass)}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Badge variant="outline">{humanize(project.autonomyEligibility)}</Badge>
          <Badge variant="outline">{humanize(project.authorityCleanliness)}</Badge>
          <Badge variant="outline" className={cn("font-medium", toneClassForBuild(project.buildHealth))}>
            build {humanize(project.buildHealth)}
          </Badge>
        </div>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="space-y-4">
          <div>
            <p className="page-eyebrow text-[10px]">First output target</p>
            <p className="mt-2 text-sm leading-6 text-foreground">{project.firstOutputTarget}</p>
          </div>

          <div>
            <p className="page-eyebrow text-[10px]">Next tranche</p>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">{project.nextTranche}</p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="surface-instrument rounded-2xl border px-4 py-3">
              <p className="page-eyebrow text-[10px]">Canonical root</p>
              <p className="mt-2 break-all font-mono text-xs text-muted-foreground">{project.canonicalRoot}</p>
            </div>
            <div className="surface-instrument rounded-2xl border px-4 py-3">
              <p className="page-eyebrow text-[10px]">Acceptance posture</p>
              <p className="mt-2 text-sm text-muted-foreground">
                {project.acceptedCandidateCount} accepted · {project.pendingCandidateCount} pending · {project.candidateCount} total candidates
              </p>
            </div>
          </div>

          <div>
            <p className="page-eyebrow text-[10px]">Blocking reasons</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {project.blockers.length > 0 ? (
                project.blockers.map((blocker) => (
                  <Badge key={blocker} variant="outline">
                    {humanize(blocker)}
                  </Badge>
                ))
              ) : (
                <Badge variant="secondary">no blockers recorded</Badge>
              )}
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <ArtifactRefs label="Verification bundle" refs={project.verificationBundle} />
            <ArtifactRefs label="Acceptance bundle" refs={project.acceptanceBundle} />
          </div>
        </div>

        <div className="space-y-4">
          <div className="surface-instrument rounded-2xl border px-4 py-4">
            <p className="page-eyebrow text-[10px]">Latest candidate</p>
            {project.latestCandidate ? (
              <div className="mt-3 space-y-3">
                <div>
                  <p className="text-sm font-medium text-foreground">{project.latestCandidate.title}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {humanize(project.latestCandidate.deliverableKind)} · {humanize(project.latestCandidate.acceptanceState ?? "pending")}
                    {project.latestCandidate.generatedAt ? ` · ${formatRelativeTime(project.latestCandidate.generatedAt)}` : ""}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {project.latestCandidate.acceptanceBacklogId ? (
                    <Badge variant="outline">{project.latestCandidate.acceptanceBacklogId}</Badge>
                  ) : null}
                  {project.latestCandidate.acceptanceMode ? (
                    <Badge variant="outline">{project.latestCandidate.acceptanceMode}</Badge>
                  ) : null}
                  {project.latestCandidate.verificationStatus ? (
                    <Badge variant="outline">{humanize(project.latestCandidate.verificationStatus)}</Badge>
                  ) : null}
                </div>
                <ArtifactRefs label="Deliverable refs" refs={project.latestCandidate.deliverableRefs} />
                <ArtifactRefs label="Workflow refs" refs={project.latestCandidate.workflowRefs} />
              </div>
            ) : (
              <p className="mt-3 text-sm text-muted-foreground">No governed project-output candidate recorded yet.</p>
            )}
          </div>

          <div className="surface-instrument rounded-2xl border px-4 py-4">
            <p className="page-eyebrow text-[10px]">Latest accepted output</p>
            {project.latestAcceptedEntry ? (
              <div className="mt-3 space-y-2">
                <p className="text-sm font-medium text-foreground">{project.latestAcceptedEntry.title}</p>
                <p className="text-xs text-muted-foreground">
                  {humanize(project.latestAcceptedEntry.deliverableKind)}
                  {project.latestAcceptedEntry.acceptedAt ? ` · ${formatRelativeTime(project.latestAcceptedEntry.acceptedAt)}` : ""}
                  {project.latestAcceptedEntry.acceptedBy ? ` · accepted by ${project.latestAcceptedEntry.acceptedBy}` : ""}
                </p>
                <ArtifactRefs label="Accepted deliverable refs" refs={project.latestAcceptedEntry.deliverableRefs} />
              </div>
            ) : (
              <p className="mt-3 text-sm text-muted-foreground">Nothing accepted-counted for this project yet.</p>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}

function FinalFormGapRow({ gap }: { gap: CommandCenterFinalFormGap }) {
  return (
    <div className="grid gap-2 border-b border-border/70 px-4 py-3 last:border-b-0 sm:grid-cols-[12rem_1fr_auto] sm:items-start">
      <div>
        <p className="text-sm font-medium text-foreground">{gap.route}</p>
        <p className="mt-1 text-[10px] uppercase tracking-[0.22em] text-muted-foreground">{humanize(gap.tranche)}</p>
      </div>
      <div>
        <p className="text-sm text-muted-foreground">{gap.detail}</p>
      </div>
      <div className="flex flex-wrap gap-2 sm:justify-end">
        <Badge variant="outline" className={severityToneClass(gap.severity)}>
          {gap.severity}
        </Badge>
        <Badge variant="outline">{humanize(gap.verificationState)}</Badge>
      </div>
    </div>
  );
}

export function ProjectsConsole({ initialSnapshot = null }: { initialSnapshot?: ProjectFactoryConsoleSnapshot | null }) {
  const projectFactoryQuery = useQuery({
    queryKey: ["project-factory-console"],
    queryFn: async (): Promise<ProjectFactoryConsoleSnapshot> => {
      const data = await requestJson("/api/projects/factory");
      return (data ?? {}) as ProjectFactoryConsoleSnapshot;
    },
    initialData: initialSnapshot ?? undefined,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  if (projectFactoryQuery.isError) {
    return (
      <ErrorPanel
        title="Project Factory"
        description={
          projectFactoryQuery.error instanceof Error
            ? projectFactoryQuery.error.message
            : "Failed to load governed project-factory data."
        }
      />
    );
  }

  const snapshot = projectFactoryQuery.data;
  if (!snapshot) {
    return null;
  }

  const latestPendingCandidate = snapshot.latestPendingCandidate;
  const openGaps = snapshot.finalFormStatus?.openGaps ?? [];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Project Factory"
        title="Governed Projects"
        description="Real project outputs, governed acceptance, and the current top product lanes. This route is the canonical project-factory console, not the old proving dashboard."
        attentionHref="/projects"
        actions={
          <Button variant="outline" onClick={() => void projectFactoryQuery.refetch()} disabled={projectFactoryQuery.isFetching}>
            <RefreshCcw className={cn("mr-2 h-4 w-4", projectFactoryQuery.isFetching ? "animate-spin" : "")} />
            Refresh
          </Button>
        }
      >
        {snapshot.degraded ? (
          <div className="surface-panel rounded-[24px] border border-[color:var(--signal-warning)]/40 px-5 py-4 sm:px-6">
            <p className="page-eyebrow text-[color:var(--signal-warning)]">Project-factory feed degraded</p>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {snapshot.detail ?? "One or more project-factory truth artifacts are unavailable from this dashboard runtime."}
            </p>
          </div>
        ) : null}

        <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-6">
          <StatCard
            label="Top project"
            value={snapshot.summary.topPriorityProjectLabel ?? snapshot.summary.topPriorityProjectId ?? "none"}
            detail={snapshot.summary.operatingMode.replaceAll("_", " ")}
            icon={<Sparkles className="h-5 w-5" />}
            tone={latestPendingCandidate ? "warning" : "default"}
          />
          <StatCard
            label="Accepted outputs"
            value={`${snapshot.summary.acceptedProjectOutputCount}`}
            detail={`${snapshot.summary.distinctProjectCount} distinct project${snapshot.summary.distinctProjectCount === 1 ? "" : "s"}`}
            icon={<CheckCircle2 className="h-5 w-5" />}
            tone={snapshot.summary.acceptedProjectOutputCount > 0 ? "success" : "default"}
          />
          <StatCard
            label="Pending review"
            value={`${snapshot.summary.pendingHybridAcceptanceCount}`}
            detail={`${snapshot.summary.pendingCandidateCount} pending candidate${snapshot.summary.pendingCandidateCount === 1 ? "" : "s"}`}
            icon={<Clock3 className="h-5 w-5" />}
            tone={snapshot.summary.pendingCandidateCount > 0 ? "warning" : "default"}
          />
          <StatCard
            label="Eligible now"
            value={`${snapshot.summary.eligibleNowCount}`}
            detail={snapshot.summary.projectOutputStageMet ? "project-output stage met" : "project-output stage still open"}
            icon={<ShieldCheck className="h-5 w-5" />}
            tone={snapshot.summary.projectOutputStageMet ? "success" : "warning"}
          />
          <StatCard
            label="Core gate"
            value={humanize(snapshot.coreRuntimeGate.singleLiveBlocker)}
            detail={`${snapshot.coreRuntimeGate.stableOperatingDayHours.toFixed(1).replace(/\.0$/, "")}/${snapshot.coreRuntimeGate.stableOperatingDayRequiredHours.toFixed(1).replace(/\.0$/, "")}h stable day · ${humanize(snapshot.coreRuntimeGate.continuityHealthStatus)}`}
            icon={<AlertTriangle className="h-5 w-5" />}
            tone={snapshot.coreRuntimeGate.proofGateOpen ? "success" : "warning"}
          />
          <StatCard
            label="Cockpit polish"
            value={snapshot.finalFormStatus ? `${snapshot.finalFormStatus.summary.openGapCount}` : "offline"}
            detail={
              snapshot.finalFormStatus
                ? `${snapshot.finalFormStatus.summary.highestSeverity} severity · ${snapshot.finalFormStatus.summary.consecutiveCleanUiAuditPassCount} clean pass`
                : "Final-form status artifact unavailable."
            }
            icon={<FolderRoot className="h-5 w-5" />}
            tone={snapshot.finalFormStatus?.done ? "success" : "warning"}
          />
        </div>
      </PageHeader>

      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="surface-panel rounded-[28px] border px-5 py-5 sm:px-6">
          <p className="page-eyebrow">Current governed work</p>
          <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">Top lane and approvals</h2>
          {latestPendingCandidate ? (
            <div className="mt-4 space-y-4">
              <div>
                <p className="text-lg font-medium text-foreground">{latestPendingCandidate.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {snapshot.summary.topPriorityProjectLabel ?? latestPendingCandidate.projectId} · {humanize(latestPendingCandidate.deliverableKind)} · {humanize(latestPendingCandidate.acceptanceState ?? "pending")}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {latestPendingCandidate.acceptanceBacklogId ? <Badge>{latestPendingCandidate.acceptanceBacklogId}</Badge> : null}
                {latestPendingCandidate.acceptanceMode ? <Badge variant="outline">{latestPendingCandidate.acceptanceMode}</Badge> : null}
                {latestPendingCandidate.verificationStatus ? (
                  <Badge variant="outline">{humanize(latestPendingCandidate.verificationStatus)}</Badge>
                ) : null}
              </div>
              <p className="text-sm leading-6 text-muted-foreground">
                {latestPendingCandidate.nextAction ?? "Open the operator desk and governed project route to review this pending output."}
              </p>
              <ArtifactRefs label="Deliverable refs" refs={latestPendingCandidate.deliverableRefs} />
              <ArtifactRefs label="Workflow refs" refs={latestPendingCandidate.workflowRefs} />
              <div className="flex flex-wrap gap-2 pt-1">
                <Button asChild size="sm">
                  <Link href="/operator">Open Operator Review</Link>
                </Button>
                <Button asChild size="sm" variant="outline">
                  <Link href="/projects">Stay on Project Factory</Link>
                </Button>
              </div>
            </div>
          ) : (
            <EmptyState
              title="No pending project-output review"
              description="No governed project-output candidate is waiting on hybrid review right now."
              className="mt-4 py-8"
            />
          )}
        </div>

        <div className="surface-panel rounded-[28px] border px-5 py-5 sm:px-6">
          <p className="page-eyebrow">Factory posture</p>
          <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">What blocks broad throughput</h2>
          <div className="mt-4 space-y-4">
            <div className="surface-instrument rounded-2xl border px-4 py-4">
              <p className="page-eyebrow text-[10px]">Single live blocker</p>
              <p className="mt-2 text-lg font-medium text-foreground">
                {humanize(snapshot.coreRuntimeGate.singleLiveBlocker)}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                Proof gate {snapshot.coreRuntimeGate.proofGateOpen ? "open" : "closed"} · runtime parity {humanize(snapshot.coreRuntimeGate.runtimeParityClass)} · continuity {humanize(snapshot.coreRuntimeGate.continuityHealthStatus)}
              </p>
            </div>
            <div className="surface-instrument rounded-2xl border px-4 py-4">
              <p className="page-eyebrow text-[10px]">Command-center final form</p>
              {snapshot.finalFormStatus ? (
                <>
                  <p className="mt-2 text-lg font-medium text-foreground">
                    {snapshot.finalFormStatus.summary.openGapCount} open gap{snapshot.finalFormStatus.summary.openGapCount === 1 ? "" : "s"}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Highest severity {snapshot.finalFormStatus.summary.highestSeverity} · clean pass streak {snapshot.finalFormStatus.summary.consecutiveCleanUiAuditPassCount}
                  </p>
                </>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">Final-form status artifact unavailable.</p>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <p className="page-eyebrow">First-class governed lanes</p>
          <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">Projects Athanor should make legible first</h2>
        </div>
        <div className="space-y-4">
          {snapshot.firstClassProjects.map((project) => (
            <ProjectLanePanel key={project.projectId} project={project} />
          ))}
        </div>
      </section>

      {snapshot.baselineProjects.length > 0 ? (
        <section className="space-y-4">
          <div>
            <p className="page-eyebrow">Baseline portfolio</p>
            <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">Visible, but lower emphasis until admitted</h2>
          </div>
          <div className="grid gap-3 xl:grid-cols-2">
            {snapshot.baselineProjects.map((project) => (
              <div key={project.projectId} className="surface-panel rounded-[24px] border px-5 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium text-foreground">{project.label}</p>
                  <Badge variant="outline">{humanize(project.readinessTier)}</Badge>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  {humanize(project.projectClass)} · {humanize(project.platformClass)} · {humanize(project.autonomyEligibility)}
                </p>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">{project.nextTranche}</p>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section className="space-y-4">
        <div>
          <p className="page-eyebrow">Cockpit final-form status</p>
          <h2 className="mt-1 font-heading text-2xl font-medium tracking-[-0.03em]">What still blocks the best full command center</h2>
        </div>
        <div className="surface-panel rounded-[28px] border">
          {openGaps.length > 0 ? (
            openGaps.map((gap) => <FinalFormGapRow key={gap.id} gap={gap} />)
          ) : (
            <EmptyState
              title="No open cockpit gaps"
              description="The command-center final-form ledger currently reports no open UI program gaps."
              className="py-10"
            />
          )}
        </div>
      </section>
    </div>
  );
}
