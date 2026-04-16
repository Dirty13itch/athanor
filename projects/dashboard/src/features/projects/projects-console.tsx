"use client";

import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Milestone,
  Plus,
  RotateCcw,
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
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import type { ProjectSnapshot, ProjectsSnapshot } from "@/lib/contracts";
import { isOperatorSessionLocked, useOperatorSessionStatus } from "@/lib/operator-session";
import { requestJson, postJson } from "@/features/workforce/helpers";

// ── Inline types for milestone data (no Zod schemas) ─────────────────

interface MilestoneTask {
  id: string;
  title: string;
  status: string;
}

interface MilestoneData {
  id: string;
  project_id: string;
  title: string;
  description: string;
  acceptance_criteria: string[];
  assigned_agents: string[];
  status: string;
  tasks: MilestoneTask[];
  progress: number;
  created_at: string;
  completed_at: string | null;
}

interface MilestonesResponse {
  milestones: MilestoneData[];
  count: number;
}

interface StalledProject {
  project_id: string;
  stalled_since: string;
}

interface StalledResponse {
  stalled: StalledProject[];
  projects?: StalledProject[];
  count: number;
}

interface ProjectPacketData {
  id: string;
  name: string;
  stage: string;
  template: string;
  class: string;
  visibility: string;
  sensitivity: string;
  runtime_target: string;
  deploy_target: string;
  workspace_root: string;
  primary_route: string;
  owner_domain: string;
  operators: string[];
  agents: string[];
  acceptance_bundle: string[];
  rollback_contract: string;
  maintenance_cadence: string;
  metadata?: Record<string, unknown>;
}

interface ArchitecturePacketData {
  project_id: string;
  service_shape: Record<string, unknown>;
  data_contracts: unknown[];
  auth_boundary: Record<string, unknown>;
  deploy_shape: Record<string, unknown>;
  risk_notes: unknown[];
  test_plan: unknown[];
  rollback_notes: unknown[];
}

interface FoundryRunData {
  id: string;
  project_id: string;
  slice_id: string;
  execution_run_id: string;
  status: string;
  summary: string;
  artifact_refs: string[];
  review_refs: string[];
}

interface FoundryRunsResponse {
  runs: FoundryRunData[];
  count: number;
}

interface ExecutionSliceData {
  id: string;
  project_id: string;
  owner_agent: string;
  lane: string;
  base_sha: string;
  worktree_path: string;
  acceptance_target: string;
  status: string;
  metadata?: Record<string, unknown>;
}

interface ExecutionSlicesResponse {
  slices: ExecutionSliceData[];
  count: number;
}

interface DeployCandidateData {
  id: string;
  project_id: string;
  channel: string;
  artifact_refs: string[];
  env_contract: Record<string, unknown>;
  smoke_results: Record<string, unknown>;
  rollback_target: Record<string, unknown>;
  promotion_status: string;
  metadata?: Record<string, unknown>;
}

interface DeploymentsResponse {
  deployments: DeployCandidateData[];
  count: number;
}

interface RollbackEventData {
  id: string;
  project_id: string;
  candidate_id: string;
  reason: string;
  rollback_target: Record<string, unknown>;
  status: string;
  metadata?: Record<string, unknown>;
  created_at: number | string;
}

interface RollbacksResponse {
  rollbacks: RollbackEventData[];
  count: number;
}

interface MaintenanceRunData {
  id: string;
  project_id: string;
  kind: string;
  trigger: string;
  status: string;
  evidence_ref: string;
  metadata?: Record<string, unknown>;
}

interface MaintenanceRunsResponse {
  maintenance_runs: MaintenanceRunData[];
  count: number;
}

interface ProjectFoundrySnapshot {
  packet: ProjectPacketData | null;
  architecture: ArchitecturePacketData | null;
  slices: ExecutionSlicesResponse;
  runs: FoundryRunsResponse;
  deployments: DeploymentsResponse;
  rollbacks: RollbacksResponse;
  maintenance: MaintenanceRunsResponse;
}

type ProvingStage = "slice_execution" | "candidate_evidence" | "rollback_record";

// ── Helpers ──────────────────────────────────────────────────────────

function statusBadgeVariant(status: string) {
  switch (status) {
    case "completed":
      return "default" as const;
    case "active":
    case "in_progress":
      return "secondary" as const;
    case "failed":
      return "destructive" as const;
    default:
      return "outline" as const;
  }
}

function projectStatusTone(status: string) {
  if (status === "active" || status === "active_development" || status === "operational")
    return "success" as const;
  if (status === "planning") return "warning" as const;
  return "default" as const;
}

function getNextProvingStageAction(
  foundry: ProjectFoundrySnapshot | undefined,
  projectId: string
): { stage: ProvingStage; label: string; description: string } | null {
  if (projectId !== "athanor") {
    return null;
  }

  const hasArchitecture = Boolean(foundry?.architecture);
  const hasSlice = (foundry?.slices.slices.length ?? 0) > 0;
  const hasRun = (foundry?.runs.runs.length ?? 0) > 0;
  const candidateWithRollback = foundry?.deployments.deployments.find(
    (candidate) => Object.keys(candidate.rollback_target ?? {}).length > 0
  );
  const hasRollbackEvidence =
    (foundry?.rollbacks.rollbacks.length ?? 0) > 0 ||
    Boolean(
      foundry?.deployments.deployments.find((candidate) =>
        ["promoted", "rolled_back"].includes(candidate.promotion_status)
      )
    );

  if (!hasArchitecture || !hasSlice || !hasRun) {
    return {
      stage: "slice_execution",
      label: "Prime Proving Slice",
      description: "Write the Athanor architecture packet, first execution slice, and first foundry run into governed foundry records.",
    };
  }
  if (!candidateWithRollback) {
    return {
      stage: "candidate_evidence",
      label: "Attach Candidate Evidence",
      description: "Record the proving deploy candidate with acceptance evidence and a rollback target before any promotion decision.",
    };
  }
  if (!hasRollbackEvidence) {
    return {
      stage: "rollback_record",
      label: "Record Rollback Proof",
      description: "Capture a bounded rollback record so the proving path has real rollback evidence without pretending a live promotion already happened.",
    };
  }
  return null;
}

// ── Component ────────────────────────────────────────────────────────

export function ProjectsConsole() {
  const queryClient = useQueryClient();
  const operatorSession = useOperatorSessionStatus();
  const privilegedReadEnabled = !operatorSession.isPending && !isOperatorSessionLocked(operatorSession);
  const [expandedProject, setExpandedProject] = useState<string | null>(null);
  const [milestoneCache, setMilestoneCache] = useState<
    Record<string, MilestonesResponse>
  >({});
  const [foundryCache, setFoundryCache] = useState<Record<string, ProjectFoundrySnapshot>>({});
  const [loadingMilestones, setLoadingMilestones] = useState<string | null>(null);
  const [loadingFoundry, setLoadingFoundry] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  // Create milestone form state
  const [newProjectId, setNewProjectId] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");

  const projectsQuery = useQuery<ProjectsSnapshot>({
    queryKey: ["projects"],
    queryFn: () => requestJson("/api/overview").then((d) => ({ generatedAt: d.generatedAt, projects: d.projects })),
    refetchInterval: 30_000,
  });

  const stalledQuery = useQuery<StalledResponse>({
    queryKey: ["projects-stalled"],
    queryFn: () => requestJson("/api/projects/stalled"),
    enabled: privilegedReadEnabled,
    refetchInterval: 60_000,
  });

  const projects = projectsQuery.data?.projects ?? [];
  const stalled = stalledQuery.data?.stalled ?? [];

  const activeProjects = projects.filter(
    (p) => ["active", "active_development", "operational"].includes(p.status)
  );
  const totalAgents = new Set(projects.flatMap((p) => p.agents)).size;

  const loadProjectFoundry = useCallback(async (projectId: string) => {
    setLoadingFoundry(projectId);
    try {
      const [
        packetResponse,
        architectureResponse,
        slicesResponse,
        runsResponse,
        deploymentsResponse,
        rollbacksResponse,
        maintenanceResponse,
      ] =
        await Promise.all([
          requestJson(`/api/projects/${encodeURIComponent(projectId)}/packet`).catch(() => null),
          requestJson(`/api/projects/${encodeURIComponent(projectId)}/architecture`).catch(() => null),
          requestJson(`/api/projects/${encodeURIComponent(projectId)}/slices`).catch(
            () => ({ slices: [], count: 0 })
          ),
          requestJson(`/api/projects/${encodeURIComponent(projectId)}/foundry/runs`).catch(
            () => ({ runs: [], count: 0 })
          ),
          requestJson(`/api/projects/${encodeURIComponent(projectId)}/deployments`).catch(
            () => ({ deployments: [], count: 0 })
          ),
          requestJson(`/api/projects/${encodeURIComponent(projectId)}/rollbacks`).catch(
            () => ({ rollbacks: [], count: 0 })
          ),
          requestJson(`/api/projects/${encodeURIComponent(projectId)}/maintenance`).catch(
            () => ({ maintenance_runs: [], count: 0 })
          ),
        ]);

      setFoundryCache((prev) => ({
        ...prev,
        [projectId]: {
          packet:
            packetResponse && typeof packetResponse === "object" && "packet" in packetResponse
              ? (packetResponse.packet as ProjectPacketData)
              : null,
          architecture:
            architectureResponse &&
            typeof architectureResponse === "object" &&
            "architecture" in architectureResponse
              ? (architectureResponse.architecture as ArchitecturePacketData)
              : null,
          slices:
            slicesResponse &&
            typeof slicesResponse === "object" &&
            "slices" in slicesResponse
              ? (slicesResponse as ExecutionSlicesResponse)
              : { slices: [], count: 0 },
          runs:
            runsResponse && typeof runsResponse === "object" && "runs" in runsResponse
              ? (runsResponse as FoundryRunsResponse)
              : { runs: [], count: 0 },
          deployments:
            deploymentsResponse &&
            typeof deploymentsResponse === "object" &&
            "deployments" in deploymentsResponse
              ? (deploymentsResponse as DeploymentsResponse)
              : { deployments: [], count: 0 },
          rollbacks:
            rollbacksResponse &&
            typeof rollbacksResponse === "object" &&
            "rollbacks" in rollbacksResponse
              ? (rollbacksResponse as RollbacksResponse)
              : { rollbacks: [], count: 0 },
          maintenance:
            maintenanceResponse &&
            typeof maintenanceResponse === "object" &&
            "maintenance_runs" in maintenanceResponse
              ? (maintenanceResponse as MaintenanceRunsResponse)
              : { maintenance_runs: [], count: 0 },
        },
      }));
    } finally {
      setLoadingFoundry(null);
    }
  }, []);

  const toggleExpand = useCallback(
    async (projectId: string) => {
      if (expandedProject === projectId) {
        setExpandedProject(null);
        return;
      }
      setExpandedProject(projectId);
      const loadPromises: Promise<unknown>[] = [];
      if (!milestoneCache[projectId]) {
        setLoadingMilestones(projectId);
        loadPromises.push(
          requestJson(`/api/projects/${encodeURIComponent(projectId)}/milestones`)
            .then((data: MilestonesResponse) => {
              setMilestoneCache((prev) => ({ ...prev, [projectId]: data }));
            })
            .catch(() => {
              setMilestoneCache((prev) => ({
                ...prev,
                [projectId]: { milestones: [], count: 0 },
              }));
            })
            .finally(() => {
              setLoadingMilestones(null);
            })
        );
      }
      if (!foundryCache[projectId]) {
        loadPromises.push(loadProjectFoundry(projectId));
      }
      if (loadPromises.length > 0) {
        await Promise.all(loadPromises);
      }
    },
    [expandedProject, foundryCache, loadProjectFoundry, milestoneCache]
  );

  async function handleAdvance(projectId: string) {
    setBusy(`advance-${projectId}`);
    setFeedback(null);
    try {
      await postJson(`/api/projects/${encodeURIComponent(projectId)}/advance`, {});
      setFeedback(`Advancement triggered for ${projectId}`);
      // Refresh milestones
      const data: MilestonesResponse = await requestJson(
        `/api/projects/${encodeURIComponent(projectId)}/milestones`
      );
      setMilestoneCache((prev) => ({ ...prev, [projectId]: data }));
    } catch (error) {
      setFeedback(
        error instanceof Error ? error.message : "Advance request failed."
      );
    } finally {
      setBusy(null);
    }
  }

  async function handlePromote(projectId: string, candidateId: string, channel: string) {
    setBusy(`promote-${candidateId}`);
    setFeedback(null);
    try {
      await postJson(`/api/projects/${encodeURIComponent(projectId)}/promote`, {
        candidate_id: candidateId,
        channel,
      });
      await loadProjectFoundry(projectId);
      setFeedback(`Promoted ${candidateId} for ${projectId}`);
    } catch (error) {
      setFeedback(
        error instanceof Error ? error.message : "Failed to promote deploy candidate."
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleRollback(projectId: string, candidateId: string) {
    setBusy(`rollback-${candidateId}`);
    setFeedback(null);
    try {
      await postJson(`/api/projects/${encodeURIComponent(projectId)}/rollback`, {
        candidate_id: candidateId,
        protected_mode: true,
      });
      await loadProjectFoundry(projectId);
      setFeedback(`Rolled back ${candidateId} for ${projectId}`);
    } catch (error) {
      setFeedback(
        error instanceof Error ? error.message : "Failed to roll back deploy candidate."
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleProvingStage(projectId: string, stage: ProvingStage) {
    setBusy(`proving-${projectId}-${stage}`);
    setFeedback(null);
    try {
      await postJson(`/api/projects/${encodeURIComponent(projectId)}/proving`, { stage });
      await loadProjectFoundry(projectId);
      setFeedback(`Recorded ${stage} for ${projectId}`);
    } catch (error) {
      setFeedback(
        error instanceof Error ? error.message : "Failed to materialize proving stage."
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleCreateMilestone() {
    if (!newProjectId || !newTitle) return;
    setBusy("create-milestone");
    setFeedback(null);
    try {
      await postJson(
        `/api/projects/${encodeURIComponent(newProjectId)}/milestones`,
        { title: newTitle, description: newDescription }
      );
      setFeedback(`Milestone "${newTitle}" created.`);
      setNewTitle("");
      setNewDescription("");
      // Refresh milestones for that project
      const data: MilestonesResponse = await requestJson(
        `/api/projects/${encodeURIComponent(newProjectId)}/milestones`
      );
      setMilestoneCache((prev) => ({ ...prev, [newProjectId]: data }));
    } catch (error) {
      setFeedback(
        error instanceof Error ? error.message : "Failed to create milestone."
      );
    } finally {
      setBusy(null);
    }
  }

  function getMilestoneProgress(projectId: string): number | null {
    const cached = milestoneCache[projectId];
    if (!cached || cached.milestones.length === 0) return null;
    const total = cached.milestones.length;
    const avgProgress =
      cached.milestones.reduce((sum, m) => sum + m.progress, 0) / total;
    return Math.round(avgProgress);
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Projects"
        description="Milestone tracking, autonomous continuation, and stall detection."
        attentionHref="/projects"
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              queryClient.invalidateQueries({ queryKey: ["projects"] });
              queryClient.invalidateQueries({ queryKey: ["projects-stalled"] });
            }}
          >
            <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
            Refresh
          </Button>
        }
      />

      {/* Stalled projects alert */}
      {stalled.length > 0 && (
        <Card className="border-[color:var(--signal-warning)]/40 bg-[color:var(--signal-warning)]/5">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base text-[color:var(--signal-warning)]">
              <AlertTriangle className="h-4 w-4" />
              {stalled.length} Stalled Project{stalled.length !== 1 ? "s" : ""}
            </CardTitle>
            <CardDescription>
              These projects have not progressed recently and may need attention.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {stalled.map((s) => (
              <Badge key={s.project_id} variant="outline">
                {s.project_id}
              </Badge>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Total Projects" value={String(projects.length)} />
        <StatCard
          label="Active"
          value={String(activeProjects.length)}
          tone="success"
        />
        <StatCard
          label="Stalled"
          value={String(stalled.length)}
          tone={stalled.length > 0 ? "warning" : "default"}
        />
        <StatCard label="Agents Assigned" value={String(totalAgents)} />
      </div>

      {/* Project cards */}
      {projects.length === 0 ? (
        <EmptyState
          title="No projects"
          description="No projects are registered with the agent server."
          icon={<Milestone className="h-5 w-5" />}
        />
      ) : (
        <div className="space-y-3">
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              expanded={expandedProject === project.id}
              milestones={milestoneCache[project.id]}
              foundry={foundryCache[project.id]}
              loadingMilestones={loadingMilestones === project.id}
              loadingFoundry={loadingFoundry === project.id}
              milestoneProgress={getMilestoneProgress(project.id)}
              busy={busy}
              onToggle={() => toggleExpand(project.id)}
              onAdvance={() => handleAdvance(project.id)}
              onMaterializeProvingStage={(stage) =>
                handleProvingStage(project.id, stage)
              }
              onPromote={(candidateId, channel) =>
                handlePromote(project.id, candidateId, channel)
              }
              onRollback={(candidateId) => handleRollback(project.id, candidateId)}
            />
          ))}
        </div>
      )}

      {/* Create milestone form */}
      {projects.length > 0 && (
        <Card className="surface-tile">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Plus className="h-4 w-4" />
              Create Milestone
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-col gap-3 sm:flex-row">
              <select
                className="h-9 rounded-md border border-input bg-transparent px-3 text-sm text-foreground"
                value={newProjectId}
                onChange={(e) => setNewProjectId(e.target.value)}
              >
                <option value="">Select project...</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
              <Input
                placeholder="Milestone title"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                className="sm:flex-1"
              />
            </div>
            <Input
              placeholder="Description (optional)"
              value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
            />
            <Button
              size="sm"
              disabled={
                !newProjectId ||
                !newTitle.trim() ||
                busy === "create-milestone"
              }
              onClick={handleCreateMilestone}
            >
              {busy === "create-milestone" ? "Creating..." : "Create"}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Feedback toast */}
      {feedback && (
        <div className="rounded-lg border border-border/50 bg-background/80 px-4 py-2 text-sm text-muted-foreground">
          {feedback}
        </div>
      )}
    </div>
  );
}

// ── Project Card ─────────────────────────────────────────────────────

function ProjectCard({
  project,
  expanded,
  milestones,
  foundry,
  loadingMilestones,
  loadingFoundry,
  milestoneProgress,
  busy,
  onToggle,
  onAdvance,
  onMaterializeProvingStage,
  onPromote,
  onRollback,
}: {
  project: ProjectSnapshot;
  expanded: boolean;
  milestones: MilestonesResponse | undefined;
  foundry: ProjectFoundrySnapshot | undefined;
  loadingMilestones: boolean;
  loadingFoundry: boolean;
  milestoneProgress: number | null;
  busy: string | null;
  onToggle: () => void;
  onAdvance: () => void;
  onMaterializeProvingStage: (stage: ProvingStage) => void;
  onPromote: (candidateId: string, channel: string) => void;
  onRollback: (candidateId: string) => void;
}) {
  const provingAction = getNextProvingStageAction(foundry, project.id);

  return (
    <Card className="surface-tile">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1 space-y-1">
            <CardTitle className="text-base">{project.name}</CardTitle>
            <CardDescription className="line-clamp-2 text-xs">
              {project.description || project.headline}
            </CardDescription>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Badge variant={statusBadgeVariant(project.status)}>
              {project.status}
            </Badge>
            {project.firstClass && (
              <Badge variant="outline" className="text-[10px]">
                1st class
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Progress bar */}
        {milestoneProgress !== null && (
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Milestone progress</span>
              <span>{milestoneProgress}%</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${milestoneProgress}%` }}
              />
            </div>
          </div>
        )}

        {/* Agent chips */}
        {project.agents.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {project.agents.map((agent) => (
              <Badge key={agent} variant="secondary" className="text-[10px]">
                {agent}
              </Badge>
            ))}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={onToggle}>
            {expanded ? (
              <ChevronDown className="mr-1 h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="mr-1 h-3.5 w-3.5" />
            )}
            {expanded ? "Hide" : "View"} Details
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onAdvance}
            disabled={busy === `advance-${project.id}`}
          >
            {busy === `advance-${project.id}` ? "Advancing..." : "Advance"}
          </Button>
        </div>

        {/* Expanded milestones */}
        {expanded && (
          <div className="space-y-4 border-t border-border/30 pt-3">
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
                  Foundry Packet
                </p>
                {loadingFoundry && (
                  <span className="text-[11px] text-muted-foreground">Loading foundry…</span>
                )}
              </div>
              {!foundry?.packet ? (
                <p className="text-xs text-muted-foreground">
                  No governed packet loaded for this project yet.
                </p>
              ) : (
                <div className="rounded-lg border border-border/30 bg-background/30 p-3 text-xs text-muted-foreground">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={statusBadgeVariant(foundry.packet.stage)}>
                      {foundry.packet.stage}
                    </Badge>
                    <Badge variant="outline">{foundry.packet.template}</Badge>
                    <Badge variant="secondary">{foundry.packet.runtime_target}</Badge>
                    <Badge variant="secondary">{foundry.packet.deploy_target}</Badge>
                  </div>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    <div>
                      <p className="font-medium text-foreground">Owner domain</p>
                      <p>{foundry.packet.owner_domain}</p>
                    </div>
                    <div>
                      <p className="font-medium text-foreground">Maintenance cadence</p>
                      <p>{foundry.packet.maintenance_cadence}</p>
                    </div>
                  </div>
                  {foundry.packet.acceptance_bundle.length > 0 && (
                    <div className="mt-3">
                      <p className="font-medium text-foreground">Acceptance bundle</p>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {foundry.packet.acceptance_bundle.map((item) => (
                          <Badge key={item} variant="outline" className="text-[10px]">
                            {item}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  {foundry.architecture && (
                    <div className="mt-3 grid gap-2 sm:grid-cols-2">
                      <div>
                        <p className="font-medium text-foreground">Service shape</p>
                        <p>
                          {String(foundry.architecture.service_shape.app ?? "service")} on{" "}
                          {String(foundry.architecture.service_shape.runtime ?? "runtime")}
                        </p>
                      </div>
                      <div>
                        <p className="font-medium text-foreground">Auth boundary</p>
                        <p>
                          {String(
                            foundry.architecture.auth_boundary.product_auth ??
                              foundry.architecture.auth_boundary.operator_auth_shared ??
                              "governed"
                          )}
                        </p>
                      </div>
                    </div>
                  )}
                  {provingAction && (
                    <div className="mt-3 flex flex-col gap-3 rounded-lg border border-border/30 bg-background/40 p-3 sm:flex-row sm:items-start sm:justify-between">
                      <div className="space-y-1">
                        <p className="font-medium text-foreground">{provingAction.label}</p>
                        <p>{provingAction.description}</p>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={busy === `proving-${project.id}-${provingAction.stage}`}
                        onClick={() => onMaterializeProvingStage(provingAction.stage)}
                      >
                        {busy === `proving-${project.id}-${provingAction.stage}`
                          ? "Recording..."
                          : provingAction.label}
                      </Button>
                    </div>
                  )}
                  {!provingAction && project.id === "athanor" && (
                    <div className="mt-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3">
                      <p className="font-medium text-foreground">Athanor proving path is recorded</p>
                      <p className="mt-1">
                        The governed packet, slice, run, candidate, and rollback evidence are all present in foundry records.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="space-y-2">
              <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
                Milestones
              </p>
            {loadingMilestones ? (
              <p className="text-xs text-muted-foreground">
                Loading milestones...
              </p>
            ) : !milestones || milestones.milestones.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No milestones defined for this project.
              </p>
            ) : (
              <div className="space-y-3">
                {milestones.milestones.map((ms) => (
                  <MilestoneRow key={ms.id} milestone={ms} />
                ))}
              </div>
            )}
            </div>

            <div className="grid gap-3 lg:grid-cols-2">
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
                  Execution Slices
                </p>
                {!foundry || foundry.slices.slices.length === 0 ? (
                  <p className="text-xs text-muted-foreground">
                    No execution slices recorded yet.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {foundry.slices.slices.slice(0, 3).map((slice) => (
                      <div
                        key={slice.id}
                        className="rounded-lg border border-border/30 bg-background/30 p-3"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-foreground">{slice.id}</p>
                            <p className="text-xs text-muted-foreground">
                              {slice.owner_agent} via {slice.lane}
                            </p>
                          </div>
                          <Badge variant={statusBadgeVariant(slice.status)}>{slice.status}</Badge>
                        </div>
                        <p className="mt-2 text-xs text-muted-foreground">
                          Acceptance target: {slice.acceptance_target || "n/a"}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
                  Foundry Runs
                </p>
                {!foundry || foundry.runs.runs.length === 0 ? (
                  <p className="text-xs text-muted-foreground">
                    No foundry runs recorded yet.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {foundry.runs.runs.slice(0, 3).map((run) => (
                      <div
                        key={run.id}
                        className="rounded-lg border border-border/30 bg-background/30 p-3"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-foreground">{run.id}</p>
                            <p className="text-xs text-muted-foreground">{run.summary}</p>
                          </div>
                          <Badge variant={statusBadgeVariant(run.status)}>{run.status}</Badge>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-1">
                          {run.artifact_refs.map((artifact) => (
                            <Badge key={artifact} variant="outline" className="text-[10px]">
                              {artifact}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
                  Deploy Candidates
                </p>
                {!foundry || foundry.deployments.deployments.length === 0 ? (
                  <p className="text-xs text-muted-foreground">
                    No deploy candidates recorded yet.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {foundry.deployments.deployments.slice(0, 3).map((deployment) => (
                      <div
                        key={deployment.id}
                        className="rounded-lg border border-border/30 bg-background/30 p-3"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-foreground">
                              {deployment.channel}
                            </p>
                            <p className="text-xs text-muted-foreground">{deployment.id}</p>
                          </div>
                          <Badge variant={statusBadgeVariant(deployment.promotion_status)}>
                            {deployment.promotion_status}
                          </Badge>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-1">
                          <Badge variant="secondary" className="text-[10px]">
                            smoke {String(deployment.smoke_results.status ?? "unknown")}
                          </Badge>
                          <Badge variant="outline" className="text-[10px]">
                            rollback {Object.keys(deployment.rollback_target ?? {}).length > 0 ? "ready" : "missing"}
                          </Badge>
                        </div>
                        {deployment.promotion_status !== "promoted" &&
                          Object.keys(deployment.rollback_target ?? {}).length > 0 && (
                            <div className="mt-3">
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={busy === `promote-${deployment.id}`}
                                onClick={() => onPromote(deployment.id, deployment.channel)}
                              >
                                {busy === `promote-${deployment.id}` ? "Promoting..." : "Promote"}
                              </Button>
                            </div>
                          )}
                        {deployment.promotion_status === "promoted" &&
                          Object.keys(deployment.rollback_target ?? {}).length > 0 && (
                            <div className="mt-3">
                              <Button
                                size="sm"
                                variant="destructive"
                                disabled={busy === `rollback-${deployment.id}`}
                                onClick={() => onRollback(deployment.id)}
                              >
                                {busy === `rollback-${deployment.id}` ? "Rolling back..." : "Rollback"}
                              </Button>
                            </div>
                          )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
                Rollback Events
              </p>
              {!foundry || foundry.rollbacks.rollbacks.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  No rollback events recorded yet.
                </p>
              ) : (
                <div className="space-y-2">
                  {foundry.rollbacks.rollbacks.slice(0, 3).map((rollback) => (
                    <div
                      key={rollback.id}
                      className="rounded-lg border border-border/30 bg-background/30 p-3"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-foreground">
                            {rollback.candidate_id}
                          </p>
                          <p className="text-xs text-muted-foreground">{rollback.reason}</p>
                        </div>
                        <Badge variant={statusBadgeVariant(rollback.status)}>{rollback.status}</Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="space-y-2">
              <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
                Maintenance Runs
              </p>
              {!foundry || foundry.maintenance.maintenance_runs.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  No maintenance runs recorded yet.
                </p>
              ) : (
                <div className="space-y-2">
                  {foundry.maintenance.maintenance_runs.slice(0, 3).map((maintenance) => (
                    <div
                      key={maintenance.id}
                      className="rounded-lg border border-border/30 bg-background/30 p-3"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-foreground">
                            {maintenance.kind}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Trigger: {maintenance.trigger}
                          </p>
                        </div>
                        <Badge variant={statusBadgeVariant(maintenance.status)}>
                          {maintenance.status}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Milestone Row ────────────────────────────────────────────────────

function MilestoneRow({ milestone }: { milestone: MilestoneData }) {
  return (
    <div className="rounded-lg border border-border/30 bg-background/30 p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">{milestone.title}</p>
          {milestone.description && (
            <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
              {milestone.description}
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Badge variant={statusBadgeVariant(milestone.status)}>
            {milestone.status}
          </Badge>
          <span className="text-xs font-medium tabular-nums text-muted-foreground">
            {milestone.progress}%
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary/70 transition-all"
          style={{ width: `${milestone.progress}%` }}
        />
      </div>

      {/* Acceptance criteria */}
      {milestone.acceptance_criteria.length > 0 && (
        <ul className="space-y-0.5 pl-1">
          {milestone.acceptance_criteria.map((criterion, i) => (
            <li
              key={i}
              className="flex items-start gap-1.5 text-xs text-muted-foreground"
            >
              <span className="mt-0.5 text-[10px]">
                {milestone.progress >= 100 ? "✓" : "○"}
              </span>
              {criterion}
            </li>
          ))}
        </ul>
      )}

      {/* Assigned agents */}
      {milestone.assigned_agents.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {milestone.assigned_agents.map((agent) => (
            <Badge
              key={agent}
              variant="secondary"
              className="text-[10px]"
            >
              {agent}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
