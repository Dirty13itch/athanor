"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useDeferredValue, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, RefreshCcw, Sparkles } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { FamilyTabs } from "@/components/family-tabs";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { postWithoutBody } from "@/features/workforce/helpers";
import { getReview } from "@/lib/api";
import { type ReviewSnapshot } from "@/lib/contracts";
import { formatRelativeTime, formatTimestamp } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import { useUrlState } from "@/lib/url-state";

const TABS = [
  { href: "/insights", label: "Insights" },
  { href: "/learning", label: "Learning" },
  { href: "/review", label: "Review" },
];

function getProjectName(snapshot: ReviewSnapshot, projectId: string | null) {
  if (!projectId) {
    return "Unscoped";
  }
  return snapshot.projects.find((project) => project.id === projectId)?.name ?? projectId;
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

export function ReviewConsole({ initialSnapshot }: { initialSnapshot: ReviewSnapshot }) {
  const { getSearchValue, setSearchValue } = useUrlState();
  const search = getSearchValue("search", "");
  const project = getSearchValue("project", "all");
  const agent = getSearchValue("agent", "all");
  const review = getSearchValue("review", "all");
  const selection = getSearchValue("selection", "");
  const deferredSearch = useDeferredValue(search.trim().toLowerCase());
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const reviewQuery = useQuery({
    queryKey: queryKeys.review,
    queryFn: getReview,
    initialData: initialSnapshot,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  async function runAction(action: string, fn: () => Promise<void>) {
    setBusyAction(action);
    setFeedback(null);
    try {
      await fn();
      await reviewQuery.refetch();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Action failed.");
    } finally {
      setBusyAction(null);
    }
  }

  if (reviewQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Review"
          title="Review Queue"
          description="The dedicated review snapshot failed to load."
          attentionHref="/review"
        />
        <ErrorPanel
          description={
            reviewQuery.error instanceof Error
              ? reviewQuery.error.message
              : "Failed to load review snapshot."
          }
        />
      </div>
    );
  }

  const snapshot = reviewQuery.data ?? initialSnapshot;
  const visibleReviewItems = snapshot.reviewItems.filter((item) => {
    const text = `${item.prompt} ${item.resultSummary ?? ""} ${item.error ?? ""} ${item.remainingRisks.join(" ")}`.toLowerCase();
    return (
      (project === "all" || item.projectId === project) &&
      (agent === "all" || item.agentId === agent) &&
      (review === "all" || item.status === review) &&
      (!deferredSearch || text.includes(deferredSearch))
    );
  });
  const selectedReviewItem =
    snapshot.reviewItems.find(
      (item) => item.id === selection || item.reviewId === selection || item.resultId === selection || item.taskId === selection,
    ) ?? null;

  const pendingApprovals = snapshot.reviewItems.filter((item) => item.kind === "approval").length;
  const failedResults = snapshot.reviewItems.filter((item) => item.status === "failed").length;
  const completedResults = snapshot.reviewItems.filter((item) => item.status === "completed").length;
  const coveredProjects = new Set(snapshot.reviewItems.map((item) => item.projectId).filter(Boolean)).size;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Review"
        title="Review Queue"
        description="Shared execution approvals and result-backed review items, without intelligence snapshot coupling."
        attentionHref="/review"
        actions={
          <Button variant="outline" onClick={() => void reviewQuery.refetch()} disabled={reviewQuery.isFetching}>
            <RefreshCcw className={`mr-2 h-4 w-4 ${reviewQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      >
        <div className="space-y-4">
          <FamilyTabs tabs={TABS} />
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Review items" value={`${snapshot.reviewItems.length}`} detail="Explicit kernel-backed review feed." />
            <StatCard label="Approvals" value={`${pendingApprovals}`} detail="Human gates waiting on a decision." />
            <StatCard label="Failed results" value={`${failedResults}`} detail="Result-backed review items that failed verification or execution." />
            <StatCard label="Projects" value={`${coveredProjects}`} detail={`${completedResults} completed result items ready for inspection.`} />
          </div>
        </div>
      </PageHeader>

      {feedback ? <ErrorPanel title="Review action" description={feedback} /> : null}

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.35fr]">
        <Card className="surface-panel">
          <CardHeader>
            <CardTitle className="text-lg">Shared filters</CardTitle>
            <CardDescription>Project, agent, and review state stay URL-backed for the review feed.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              value={search}
              onChange={(event) => setSearchValue("search", event.target.value || null)}
              placeholder="Search review"
              className="surface-instrument"
            />
            <FilterRow
              label="Project"
              values={[
                { id: "all", label: "All" },
                ...snapshot.projects.map((projectEntry) => ({ id: projectEntry.id, label: projectEntry.name })),
              ]}
              activeValue={project}
              onChange={(value) => setSearchValue("project", value === "all" ? null : value)}
            />
            <FilterRow
              label="Agent"
              values={[
                { id: "all", label: "All" },
                ...snapshot.agents.map((agentEntry) => ({ id: agentEntry.id, label: agentEntry.name })),
              ]}
              activeValue={agent}
              onChange={(value) => setSearchValue("agent", value === "all" ? null : value)}
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

        <Card className="surface-panel">
          <CardHeader>
            <CardTitle className="text-lg">Review queue</CardTitle>
            <CardDescription>{visibleReviewItems.length} review items match the current filters.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {visibleReviewItems.length > 0 ? (
              visibleReviewItems.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSearchValue("selection", item.id)}
                  className={`w-full rounded-2xl p-4 text-left transition hover:bg-accent/40 ${reviewSurfaceClass(item.status)}`}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline" className="status-badge" data-tone={reviewTone(item.status)}>
                      {item.status}
                    </Badge>
                    <Badge variant="secondary">{item.agentId}</Badge>
                    {item.projectId ? <Badge variant="outline">{getProjectName(snapshot, item.projectId)}</Badge> : null}
                    <span className="ml-auto text-xs text-muted-foreground">{formatRelativeTime(item.createdAt)}</span>
                  </div>
                  <p className="mt-3 text-sm font-medium">{item.prompt}</p>
                  {item.resultSummary ? (
                    <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">{item.resultSummary}</p>
                  ) : null}
                </button>
              ))
            ) : (
              <EmptyState title="No review items match the current filters" description="Clear the review filter or search for a different task." />
            )}
          </CardContent>
        </Card>
      </div>

      <Sheet open={Boolean(selectedReviewItem)} onOpenChange={(open) => setSearchValue("selection", open ? selection : null)}>
        <SheetContent side="right" className="w-full max-w-xl overflow-y-auto border-l border-border/80 bg-background/95">
          {selectedReviewItem ? (
            <>
              <SheetHeader className="border-b border-border/80 px-6 py-5 text-left">
                <SheetTitle>{selectedReviewItem.prompt}</SheetTitle>
                <SheetDescription>
                  {selectedReviewItem.projectId ? getProjectName(snapshot, selectedReviewItem.projectId) : "Unscoped task"}
                </SheetDescription>
              </SheetHeader>
              <div className="space-y-6 p-6">
                <div className="grid gap-3 md:grid-cols-2">
                  <Metric label="Status" value={selectedReviewItem.status} />
                  <Metric label="Created" value={formatTimestamp(selectedReviewItem.createdAt)} />
                </div>
                {selectedReviewItem.resultOutcome ? <Section label="Outcome">{selectedReviewItem.resultOutcome}</Section> : null}
                {selectedReviewItem.resultVerificationStatus ? (
                  <Section label="Verification">{selectedReviewItem.resultVerificationStatus}</Section>
                ) : null}
                {selectedReviewItem.resultSummary ? <Section label="Result">{selectedReviewItem.resultSummary}</Section> : null}
                {selectedReviewItem.resultFilesChanged.length ? (
                  <Section label="Files changed">{selectedReviewItem.resultFilesChanged.join("\n")}</Section>
                ) : null}
                {selectedReviewItem.remainingRisks.length ? (
                  <Section label="Remaining risks">{selectedReviewItem.remainingRisks.join("\n")}</Section>
                ) : null}
                {selectedReviewItem.resumableHandle ? (
                  <Section label="Resumable handle">{selectedReviewItem.resumableHandle}</Section>
                ) : null}
                <Card className="surface-panel">
                  <CardHeader>
                    <CardTitle className="text-lg">Actions</CardTitle>
                    <CardDescription>Approve, reopen, or jump back into the related task and project context.</CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-wrap gap-2">
                    {selectedReviewItem.kind === "approval" && selectedReviewItem.reviewId ? (
                      <Button
                        size="sm"
                        disabled={busyAction === `approve:${selectedReviewItem.id}`}
                        onClick={() =>
                          void runAction(`approve:${selectedReviewItem.id}`, () =>
                            postWithoutBody(`/api/execution/reviews/${encodeURIComponent(selectedReviewItem.reviewId!)}/approve`),
                          )
                        }
                      >
                        <CheckCircle2 className="mr-2 h-4 w-4" />
                        Approve
                      </Button>
                    ) : null}
                    <Button asChild size="sm" variant="outline">
                      <Link href={`/runs?selection=${selectedReviewItem.taskId}`}>
                        <RefreshCcw className="mr-2 h-4 w-4" />
                        Open runs
                      </Link>
                    </Button>
                    <Button asChild size="sm" variant="outline">
                      <Link href={selectedReviewItem.deepLink}>
                        <Sparkles className="mr-2 h-4 w-4" />
                        Open source
                      </Link>
                    </Button>
                    {selectedReviewItem.projectId ? (
                      <Button asChild size="sm" variant="outline">
                        <Link href={`/backlog?project=${selectedReviewItem.projectId}`}>
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

function Section({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <div className="surface-instrument mt-2 rounded-xl border p-3 text-sm whitespace-pre-wrap">{children}</div>
    </div>
  );
}
