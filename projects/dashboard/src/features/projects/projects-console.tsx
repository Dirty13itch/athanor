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

// ── Component ────────────────────────────────────────────────────────

export function ProjectsConsole() {
  const queryClient = useQueryClient();
  const operatorSession = useOperatorSessionStatus();
  const privilegedReadEnabled = !operatorSession.isPending && !isOperatorSessionLocked(operatorSession);
  const [expandedProject, setExpandedProject] = useState<string | null>(null);
  const [milestoneCache, setMilestoneCache] = useState<
    Record<string, MilestonesResponse>
  >({});
  const [loadingMilestones, setLoadingMilestones] = useState<string | null>(null);
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

  const toggleExpand = useCallback(
    async (projectId: string) => {
      if (expandedProject === projectId) {
        setExpandedProject(null);
        return;
      }
      setExpandedProject(projectId);
      if (!milestoneCache[projectId]) {
        setLoadingMilestones(projectId);
        try {
          const data: MilestonesResponse = await requestJson(
            `/api/projects/${encodeURIComponent(projectId)}/milestones`
          );
          setMilestoneCache((prev) => ({ ...prev, [projectId]: data }));
        } catch {
          // Milestones endpoint may not exist for this project yet
          setMilestoneCache((prev) => ({
            ...prev,
            [projectId]: { milestones: [], count: 0 },
          }));
        } finally {
          setLoadingMilestones(null);
        }
      }
    },
    [expandedProject, milestoneCache]
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
              loadingMilestones={loadingMilestones === project.id}
              milestoneProgress={getMilestoneProgress(project.id)}
              busy={busy}
              onToggle={() => toggleExpand(project.id)}
              onAdvance={() => handleAdvance(project.id)}
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
  loadingMilestones,
  milestoneProgress,
  busy,
  onToggle,
  onAdvance,
}: {
  project: ProjectSnapshot;
  expanded: boolean;
  milestones: MilestonesResponse | undefined;
  loadingMilestones: boolean;
  milestoneProgress: number | null;
  busy: string | null;
  onToggle: () => void;
  onAdvance: () => void;
}) {
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
            {expanded ? "Hide" : "View"} Milestones
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
          <div className="border-t border-border/30 pt-3">
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
