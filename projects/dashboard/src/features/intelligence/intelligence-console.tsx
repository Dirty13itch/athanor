"use client";

import Link from "next/link";
import { useDeferredValue, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Brain, CheckCircle2, RefreshCcw, Sparkles } from "lucide-react";
import { FamilyTabs } from "@/components/family-tabs";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { JudgePlaneCard } from "@/components/judge-plane-card";
import { ModelGovernanceCard } from "@/components/model-governance-card";
import { PageHeader } from "@/components/page-header";
import { ProvingGroundCard } from "@/components/proving-ground-card";
import { SkillsLane } from "@/components/skills-lane";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { StatCard } from "@/components/stat-card";
import { getIntelligence } from "@/lib/api";
import { type IntelligencePattern, type IntelligenceSnapshot } from "@/lib/contracts";
import { formatRelativeTime, formatTimestamp } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import { useUrlState } from "@/lib/url-state";
import { postWithoutBody } from "@/features/workforce/helpers";

const TABS = [
  { href: "/insights", label: "Insights" },
  { href: "/learning", label: "Learning" },
  { href: "/review", label: "Review" },
];

type IntelligenceVariant = "insights" | "learning" | "review";
type SeverityFilter = "all" | "high" | "medium" | "low";

function matchesProject(projectId: string | null, selectedProject: string) {
  return selectedProject === "all" || projectId === selectedProject;
}

function inferPatternProjectId(pattern: IntelligencePattern) {
  const combined = `${pattern.type} ${Object.keys(pattern.topics ?? {}).join(" ")}`.toLowerCase();
  if (combined.includes("eoq")) {
    return "eoq";
  }
  if (combined.includes("media")) {
    return "media";
  }
  if (combined.includes("kindred")) {
    return "kindred";
  }
  return "athanor";
}

function getProjectName(snapshot: IntelligenceSnapshot, projectId: string | null) {
  if (!projectId) {
    return "Athanor";
  }
  return snapshot.projects.find((project) => project.id === projectId)?.name ?? projectId;
}

function patternSurfaceClass(severity: string) {
  if (severity === "high") {
    return "surface-hero border";
  }
  if (severity === "medium") {
    return "surface-instrument border";
  }
  return "surface-tile border";
}

function patternTone(severity: string) {
  if (severity === "high") {
    return "danger";
  }
  if (severity === "medium") {
    return "warning";
  }
  return "info";
}

function reviewSurfaceClass(status: string) {
  if (status === "pending_approval") {
    return "surface-hero border";
  }
  if (status === "failed") {
    return "surface-instrument border";
  }
  return "surface-tile border";
}

function reviewTone(status: string) {
  if (status === "pending_approval") {
    return "review";
  }
  if (status === "failed") {
    return "danger";
  }
  return "success";
}

export function IntelligenceConsole({
  initialSnapshot,
  variant,
}: {
  initialSnapshot: IntelligenceSnapshot;
  variant: IntelligenceVariant;
}) {
  const { getSearchValue, setSearchValue } = useUrlState();
  const search = getSearchValue("search", "");
  const project = getSearchValue("project", "all");
  const agent = getSearchValue("agent", "all");
  const severity = getSearchValue("severity", "all") as SeverityFilter;
  const review = getSearchValue("review", "all");
  const selection = getSearchValue("selection", "");
  const deferredSearch = useDeferredValue(search.trim().toLowerCase());
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const intelligenceQuery = useQuery({
    queryKey: queryKeys.intelligence,
    queryFn: getIntelligence,
    initialData: initialSnapshot,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  async function runAction(action: string, fn: () => Promise<void>) {
    setBusyAction(action);
    setFeedback(null);
    try {
      await fn();
      await intelligenceQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Action failed.");
    } finally {
      setBusyAction(null);
    }
  }

  if (intelligenceQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Intelligence"
          title="Intelligence Console"
          description="The intelligence snapshot failed to load."
          attentionHref={variant === "review" ? "/review" : undefined}
        />
        <ErrorPanel
          description={
            intelligenceQuery.error instanceof Error
              ? intelligenceQuery.error.message
              : "Failed to load intelligence snapshot."
          }
        />
      </div>
    );
  }

  const snapshot = intelligenceQuery.data ?? initialSnapshot;
  const visiblePatterns = (snapshot.report?.patterns ?? []).filter((pattern) => {
    const projectId = inferPatternProjectId(pattern);
    const text = `${pattern.type} ${pattern.agentId ?? ""} ${Object.keys(pattern.topics ?? {}).join(" ")}`.toLowerCase();
    return (
      matchesProject(projectId, project) &&
      (agent === "all" || pattern.agentId === agent) &&
      (severity === "all" || pattern.severity === severity) &&
      (!deferredSearch || text.includes(deferredSearch))
    );
  });
  const visibleReviewTasks = snapshot.reviewTasks.filter((task) => {
    const text = `${task.prompt} ${task.result ?? ""} ${task.error ?? ""}`.toLowerCase();
    return (
      matchesProject(task.projectId, project) &&
      (agent === "all" || task.agentId === agent) &&
      (review === "all" || task.status === review) &&
      (!deferredSearch || text.includes(deferredSearch))
    );
  });
  const selectedReviewTask = snapshot.reviewTasks.find((task) => task.id === selection) ?? null;
  const title =
    variant === "insights" ? "Insights" : variant === "learning" ? "Learning Metrics" : "Code Review";
  const description =
    variant === "insights"
      ? "Pattern detection and recommendations across project, agent, and severity lanes."
      : variant === "learning"
        ? "Learning health, benchmark posture, and self-improvement telemetry."
        : "Approval and review queue management with direct task and project links.";

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Intelligence"
        title={title}
        description={description}
        attentionHref={variant === "review" ? "/review" : undefined}
        actions={
          <>
            <Button variant="outline" onClick={() => void intelligenceQuery.refetch()} disabled={intelligenceQuery.isFetching}>
              <RefreshCcw className={`mr-2 h-4 w-4 ${intelligenceQuery.isFetching ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button
              variant="outline"
              onClick={() =>
                void runAction("patterns", () => postWithoutBody("/api/insights/run"))
              }
              disabled={busyAction === "patterns"}
            >
              <Sparkles className="mr-2 h-4 w-4" />
              Run insights
            </Button>
            <Button
              variant="outline"
              onClick={() =>
                void runAction("benchmarks", () => postWithoutBody("/api/learning/benchmarks"))
              }
              disabled={busyAction === "benchmarks"}
            >
              <Brain className="mr-2 h-4 w-4" />
              Run benchmarks
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <FamilyTabs tabs={TABS} />
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Patterns"
              value={`${snapshot.report?.patterns.length ?? 0}`}
              detail={`${snapshot.report?.recommendations.length ?? 0} recommendations.`}
              tone={(snapshot.report?.patterns.some((pattern) => pattern.severity === "high") ?? false) ? "warning" : "success"}
            />
            <StatCard
              label="Learning health"
              value={`${Math.round((snapshot.learning?.summary.overallHealth ?? 0) * 100)}%`}
              detail={snapshot.learning?.summary.assessment ?? "Unavailable"}
            />
            <StatCard
              label="Review queue"
              value={`${snapshot.reviewTasks.length}`}
              detail="Approvals, failures, and code-heavy completions."
            />
            <StatCard
              label="Featured project"
              value="EoBQ"
              detail="Primary tenant context across the intelligence family."
            />
          </div>
        </div>
      </PageHeader>

      {feedback ? <ErrorPanel title="Intelligence action" description={feedback} /> : null}

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.35fr]">
        <Card className="surface-panel">
          <CardHeader>
            <CardTitle className="text-lg">Shared filters</CardTitle>
            <CardDescription>Project, agent, and review state all stay URL-backed across the family routes.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="relative">
              <Input
                value={search}
                onChange={(event) => setSearchValue("search", event.target.value || null)}
                placeholder={`Search ${variant}`}
                className="surface-instrument"
              />
            </div>
            <FilterRow
              label="Project"
              values={[{ id: "all", label: "All" }, ...snapshot.projects.map((projectEntry) => ({ id: projectEntry.id, label: projectEntry.id === "eoq" ? `${projectEntry.name} (Featured)` : projectEntry.name }))]}
              activeValue={project}
              onChange={(value) => setSearchValue("project", value === "all" ? null : value)}
            />
            <FilterRow
              label="Agent"
              values={[{ id: "all", label: "All" }, ...snapshot.agents.map((agentEntry) => ({ id: agentEntry.id, label: agentEntry.name }))]}
              activeValue={agent}
              onChange={(value) => setSearchValue("agent", value === "all" ? null : value)}
            />
            <FilterRow
              label="Severity"
              values={[
                { id: "all", label: "All" },
                { id: "high", label: "High" },
                { id: "medium", label: "Medium" },
                { id: "low", label: "Low" },
              ]}
              activeValue={severity}
              onChange={(value) => setSearchValue("severity", value === "all" ? null : value)}
            />
            <FilterRow
              label="Review"
              values={[
                { id: "all", label: "All" },
                { id: "pending_approval", label: "Approval" },
                { id: "failed", label: "Failed" },
                { id: "completed", label: "Completed" },
              ]}
              activeValue={review}
              onChange={(value) => setSearchValue("review", value === "all" ? null : value)}
            />
          </CardContent>
        </Card>

        <Card className="surface-hero">
          <CardHeader>
            <CardTitle className="text-lg">Operator posture</CardTitle>
            <CardDescription>What needs judgment now, what is improving, and where the next intervention helps most.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            <Metric label="Last report" value={formatRelativeTime(snapshot.report?.timestamp ?? snapshot.generatedAt)} />
            <Metric label="Benchmarks" value={`${snapshot.improvement?.benchmarkResults ?? 0}`} />
            <Metric label="Pending proposals" value={`${snapshot.improvement?.pending ?? 0}`} />
          </CardContent>
        </Card>
      </div>

      {variant === "insights" ? (
        <>
          <Card className="surface-panel">
            <CardHeader>
              <CardTitle className="text-lg">Detected patterns</CardTitle>
              <CardDescription>{visiblePatterns.length} patterns match the current filters.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 lg:grid-cols-2">
              {visiblePatterns.length > 0 ? (
                visiblePatterns.map((pattern) => (
                  <div
                    key={`${pattern.type}-${pattern.agentId ?? "global"}`}
                    className={`rounded-2xl p-4 ${patternSurfaceClass(pattern.severity)}`}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline" className="status-badge" data-tone={patternTone(pattern.severity)}>
                        {pattern.severity}
                      </Badge>
                      <Badge variant="secondary">{pattern.type.replace(/_/g, " ")}</Badge>
                      {pattern.agentId ? <Badge variant="outline">{pattern.agentId}</Badge> : null}
                      <span className="ml-auto text-xs text-muted-foreground">{getProjectName(snapshot, inferPatternProjectId(pattern))}</span>
                    </div>
                    {pattern.count ? <p className="mt-3 text-sm font-medium">{pattern.count} observed signals</p> : null}
                    {pattern.sampleErrors.length > 0 ? (
                      <p className="mt-2 text-sm text-muted-foreground">{pattern.sampleErrors[0]}</p>
                    ) : null}
                    {Object.keys(pattern.topics).length > 0 ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {Object.entries(pattern.topics).slice(0, 4).map(([topic, count]) => (
                          <Badge key={topic} variant="outline">
                            {topic} x{count}
                          </Badge>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))
              ) : (
                <EmptyState title="No patterns match the current filters" description="Widen the project or severity filters to inspect more signals." className="lg:col-span-2" />
              )}
            </CardContent>
          </Card>

          <Card className="surface-panel">
            <CardHeader>
              <CardTitle className="text-lg">Recommendations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {(snapshot.report?.recommendations ?? []).length > 0 ? (
                snapshot.report?.recommendations.map((recommendation) => (
                  <div key={recommendation} className="surface-instrument rounded-2xl border p-4 text-sm">
                    {recommendation}
                  </div>
                ))
              ) : (
                <EmptyState title="No recommendations yet" description="Run insights collection to refresh pattern-derived guidance." />
              )}
            </CardContent>
          </Card>
        </>
      ) : null}

      {variant === "learning" ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Overall health" value={`${Math.round((snapshot.learning?.summary.overallHealth ?? 0) * 100)}%`} detail={snapshot.learning?.summary.assessment ?? "Unavailable"} />
            <StatCard label="Cache hit rate" value={`${Math.round((snapshot.learning?.metrics.cache?.hitRate ?? 0) * 100)}%`} detail={`${snapshot.learning?.metrics.cache?.tokensSaved ?? 0} tokens saved`} />
            <StatCard label="Trust average" value={`${((snapshot.learning?.metrics.trust?.avgTrustScore ?? 0) * 100).toFixed(0)}%`} detail={`${snapshot.learning?.metrics.trust?.agentsTracked ?? 0} agents tracked`} />
            <StatCard label="Success rate" value={`${Math.round((snapshot.learning?.metrics.tasks?.successRate ?? 0) * 100)}%`} detail={`${snapshot.learning?.metrics.tasks?.completed ?? 0} completed tasks`} />
          </div>

          <SkillsLane />

          <div className="grid gap-4 xl:grid-cols-[1fr_1fr_1fr]">
            <ModelGovernanceCard />
            <ProvingGroundCard />
            <JudgePlaneCard />
          </div>

          <Card className="surface-panel">
            <CardHeader>
              <CardTitle className="text-lg">Learning health</CardTitle>
              <CardDescription>{snapshot.learning?.summary.positiveSignals.length ?? 0} positive signals in the current cycle.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 lg:grid-cols-2">
              <MetricGroup
                title="Semantic cache"
                rows={[
                  { label: "Entries", value: `${snapshot.learning?.metrics.cache?.totalEntries ?? 0}` },
                  { label: "Hit rate", value: `${Math.round((snapshot.learning?.metrics.cache?.hitRate ?? 0) * 100)}%` },
                  { label: "Avg similarity", value: `${snapshot.learning?.metrics.cache?.avgSimilarity?.toFixed(2) ?? "0.00"}` },
                ]}
              />
              <MetricGroup
                title="Self-improvement"
                rows={[
                  { label: "Proposals", value: `${snapshot.improvement?.totalProposals ?? 0}` },
                  { label: "Pending", value: `${snapshot.improvement?.pending ?? 0}` },
                  { label: "Deployed", value: `${snapshot.improvement?.deployed ?? 0}` },
                ]}
              />
            </CardContent>
          </Card>
        </>
      ) : null}

      {variant === "review" ? (
        <>
          <div className="grid gap-4 xl:grid-cols-[1fr_1fr_1fr]">
            <ModelGovernanceCard />
            <ProvingGroundCard />
            <JudgePlaneCard />
          </div>

          <Card className="surface-panel">
            <CardHeader>
              <CardTitle className="text-lg">Review queue</CardTitle>
              <CardDescription>{visibleReviewTasks.length} review items match the current filters.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {visibleReviewTasks.length > 0 ? (
                visibleReviewTasks.map((task) => (
                  <button
                    key={task.id}
                    type="button"
                    onClick={() => setSearchValue("selection", task.id)}
                    className={`w-full rounded-2xl p-4 text-left transition hover:bg-accent/40 ${reviewSurfaceClass(task.status)}`}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline" className="status-badge" data-tone={reviewTone(task.status)}>
                        {task.status}
                      </Badge>
                      <Badge variant="secondary">{task.agentId}</Badge>
                      {task.projectId ? <Badge variant="outline">{getProjectName(snapshot, task.projectId)}</Badge> : null}
                      <span className="ml-auto text-xs text-muted-foreground">{formatRelativeTime(task.createdAt)}</span>
                    </div>
                    <p className="mt-3 text-sm font-medium">{task.prompt}</p>
                    {task.result ? <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">{task.result}</p> : null}
                  </button>
                ))
              ) : (
                <EmptyState title="No review items match the current filters" description="Clear the review filter or search for a different task." />
              )}
            </CardContent>
          </Card>
        </>
      ) : null}

      <Sheet open={Boolean(selectedReviewTask)} onOpenChange={(open) => setSearchValue("selection", open ? selection : null)}>
        <SheetContent side="right" className="w-full max-w-xl overflow-y-auto border-l border-border/80 bg-background/95">
          {selectedReviewTask ? (
            <>
              <SheetHeader className="border-b border-border/80 px-6 py-5 text-left">
                <SheetTitle>{selectedReviewTask.prompt}</SheetTitle>
                <SheetDescription>
                  {selectedReviewTask.projectId ? getProjectName(snapshot, selectedReviewTask.projectId) : "Unscoped task"}
                </SheetDescription>
              </SheetHeader>
              <div className="space-y-6 p-6">
                <div className="grid gap-3 md:grid-cols-2">
                  <Metric label="Status" value={selectedReviewTask.status} />
                  <Metric label="Created" value={formatTimestamp(selectedReviewTask.createdAt)} />
                </div>
                {selectedReviewTask.result ? <Section label="Result">{selectedReviewTask.result}</Section> : null}
                {selectedReviewTask.error ? <Section label="Error">{selectedReviewTask.error}</Section> : null}
                <Card className="surface-panel">
                  <CardHeader>
                    <CardTitle className="text-lg">Actions</CardTitle>
                    <CardDescription>Approve, reopen, or jump back into the related task and project context.</CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-wrap gap-2">
                    {selectedReviewTask.status === "pending_approval" ? (
                      <Button
                        size="sm"
                        onClick={() =>
                          void runAction(`approve:${selectedReviewTask.id}`, () =>
                            postWithoutBody(`/api/workforce/tasks/${selectedReviewTask.id}/approve`)
                          )
                        }
                      >
                        <CheckCircle2 className="mr-2 h-4 w-4" />
                        Approve
                      </Button>
                    ) : null}
                    <Button asChild size="sm" variant="outline">
                      <Link href={`/tasks?agent=${selectedReviewTask.agentId}`}>
                        <RefreshCcw className="mr-2 h-4 w-4" />
                        Open task board
                      </Link>
                    </Button>
                    {selectedReviewTask.projectId ? (
                      <Button asChild size="sm" variant="outline">
                        <Link href={`/workplanner?project=${selectedReviewTask.projectId}`}>
                          <Sparkles className="mr-2 h-4 w-4" />
                          Open project
                        </Link>
                      </Button>
                    ) : null}
                  </CardContent>
                </Card>
              </div>
            </>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function FilterRow({
  label,
  values,
  activeValue,
  onChange,
}: {
  label: string;
  values: Array<{ id: string; label: string }>;
  activeValue: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
      <div className="flex flex-wrap gap-2">
        {values.map((value) => (
          <Button
            key={value.id}
            size="sm"
            variant={activeValue === value.id ? "default" : "outline"}
            onClick={() => onChange(value.id)}
          >
            {value.label}
          </Button>
        ))}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="surface-metric rounded-xl border px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 font-medium">{value}</p>
    </div>
  );
}

function MetricGroup({
  title,
  rows,
}: {
  title: string;
  rows: Array<{ label: string; value: string }>;
}) {
  return (
    <div className="surface-instrument rounded-2xl border p-4">
      <p className="text-sm font-medium">{title}</p>
      <div className="mt-3 space-y-2">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{row.label}</span>
            <span className="font-medium">{row.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <div className="surface-instrument mt-2 rounded-xl border p-3 text-sm whitespace-pre-wrap">
        {children}
      </div>
    </div>
  );
}
