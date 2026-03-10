"use client";

import Link from "next/link";
import { useDeferredValue } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, ExternalLink, Link2, RefreshCcw, Search } from "lucide-react";
import { FamilyTabs } from "@/components/family-tabs";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { StatCard } from "@/components/stat-card";
import { getHistory } from "@/lib/api";
import { type HistoryActivityItem, type HistoryConversationItem, type HistoryOutputItem, type HistorySnapshot } from "@/lib/contracts";
import { formatRelativeTime, formatTimestamp } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import { useUrlState } from "@/lib/url-state";

const TABS = [
  { href: "/activity", label: "Activity" },
  { href: "/conversations", label: "Conversations" },
  { href: "/outputs", label: "Outputs" },
];

type HistoryVariant = "activity" | "conversations" | "outputs";
type StatusFilter = "all" | "pending_approval" | "running" | "completed" | "failed";
type TimeframeFilter = "4h" | "24h" | "7d" | "30d";

function parseTimeframeMinutes(value: TimeframeFilter) {
  switch (value) {
    case "4h":
      return 240;
    case "7d":
      return 10080;
    case "30d":
      return 43200;
    default:
      return 1440;
  }
}

function withinTimeframe(timestamp: string, timeframe: TimeframeFilter) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return true;
  }
  return Date.now() - date.getTime() <= parseTimeframeMinutes(timeframe) * 60_000;
}

function exportSnapshot(name: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `athanor-${name}-${new Date().toISOString()}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function itemMatchesStatus(
  item: HistoryActivityItem | HistoryConversationItem | HistoryOutputItem,
  status: StatusFilter,
  snapshot: HistorySnapshot
) {
  if (status === "all") {
    return true;
  }

  if ("status" in item && item.status) {
    return item.status === status;
  }

  const relatedTaskId = item.relatedTaskId;
  if (!relatedTaskId) {
    return false;
  }

  return snapshot.tasks.find((task) => task.id === relatedTaskId)?.status === status;
}

function itemProjectId(item: HistoryActivityItem | HistoryConversationItem | HistoryOutputItem) {
  return item.projectId ?? "unassigned";
}

function getProjectName(snapshot: HistorySnapshot, projectId: string | null) {
  if (!projectId) {
    return "Unassigned";
  }
  return snapshot.projects.find((project) => project.id === projectId)?.name ?? projectId;
}

function getAgentName(snapshot: HistorySnapshot, agentId: string) {
  return snapshot.agents.find((agent) => agent.id === agentId)?.name ?? agentId;
}

function SelectionDetails({
  item,
  snapshot,
}: {
  item: HistoryActivityItem | HistoryConversationItem | HistoryOutputItem;
  snapshot: HistorySnapshot;
}) {
  const projectName = getProjectName(snapshot, item.projectId ?? null);
  const relatedTask = item.relatedTaskId
    ? snapshot.tasks.find((task) => task.id === item.relatedTaskId) ?? null
    : null;

  return (
    <div className="space-y-6 p-6">
      <div className="grid gap-3 md:grid-cols-2">
        <Metric label="Project" value={projectName} />
        <Metric
          label="Timestamp"
          value={"modifiedAt" in item ? formatTimestamp(item.modifiedAt) : formatTimestamp(item.timestamp)}
        />
      </div>

      {"inputSummary" in item ? (
        <>
          <Section label="Input">{item.inputSummary}</Section>
          {item.outputSummary ? <Section label="Output">{item.outputSummary}</Section> : null}
        </>
      ) : null}

      {"userMessage" in item ? (
        <>
          <Section label="User message">{item.userMessage}</Section>
          {item.assistantResponse ? <Section label="Assistant response">{item.assistantResponse}</Section> : null}
        </>
      ) : null}

      {"path" in item ? (
        <Section label="Output path">{item.path}</Section>
      ) : null}

      <Card className="border-border/70 bg-card/70">
        <CardHeader>
          <CardTitle className="text-lg">Back-links</CardTitle>
          <CardDescription>Follow this item through related task, project, and review surfaces.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {item.projectId ? (
            <Button asChild size="sm" variant="outline">
              <Link href={`/workplanner?project=${item.projectId}`}>
                <Link2 className="mr-2 h-4 w-4" />
                Open project
              </Link>
            </Button>
          ) : null}
          {item.relatedTaskId ? (
            <Button asChild size="sm" variant="outline">
              <Link href={`/tasks?selection=${item.relatedTaskId}`}>
                <Link2 className="mr-2 h-4 w-4" />
                Open task
              </Link>
            </Button>
          ) : null}
          {"threadId" in item ? (
            <Button asChild size="sm" variant="outline">
              <Link href={`/conversations?selection=${encodeURIComponent(item.threadId)}`}>
                <Link2 className="mr-2 h-4 w-4" />
                Conversation
              </Link>
            </Button>
          ) : null}
          {"path" in item && item.previewAvailable ? (
            <Button asChild size="sm" variant="outline">
              <Link href={item.href}>
                <ExternalLink className="mr-2 h-4 w-4" />
                Preview output
              </Link>
            </Button>
          ) : null}
          {relatedTask && ["pending_approval", "failed"].includes(relatedTask.status) ? (
            <Button asChild size="sm" variant="outline">
              <Link href={`/review?selection=${relatedTask.id}`}>
                <ExternalLink className="mr-2 h-4 w-4" />
                Review item
              </Link>
            </Button>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

export function HistoryConsole({
  initialSnapshot,
  variant,
}: {
  initialSnapshot: HistorySnapshot;
  variant: HistoryVariant;
}) {
  const { getSearchValue, setSearchValue } = useUrlState();
  const search = getSearchValue("search", "");
  const project = getSearchValue("project", "all");
  const agent = getSearchValue("agent", "all");
  const status = getSearchValue("status", "all") as StatusFilter;
  const timeframe = getSearchValue("timeframe", "24h") as TimeframeFilter;
  const selection = getSearchValue("selection", "");
  const deferredSearch = useDeferredValue(search.trim().toLowerCase());

  const historyQuery = useQuery({
    queryKey: queryKeys.history,
    queryFn: getHistory,
    initialData: initialSnapshot,
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });

  if (historyQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="History / Handoff" title="History Console" description="The history snapshot failed to load." />
        <ErrorPanel
          description={
            historyQuery.error instanceof Error ? historyQuery.error.message : "Failed to load history snapshot."
          }
        />
      </div>
    );
  }

  const snapshot = historyQuery.data ?? initialSnapshot;
  const activity = snapshot.activity.filter(
    (item) =>
      (project === "all" || itemProjectId(item) === project) &&
      (agent === "all" || item.agentId === agent) &&
      withinTimeframe(item.timestamp, timeframe) &&
      itemMatchesStatus(item, status, snapshot) &&
      (!deferredSearch ||
        item.inputSummary.toLowerCase().includes(deferredSearch) ||
        (item.outputSummary ?? "").toLowerCase().includes(deferredSearch))
  );
  const conversations = snapshot.conversations.filter(
    (item) =>
      (project === "all" || itemProjectId(item) === project) &&
      (agent === "all" || item.agentId === agent) &&
      withinTimeframe(item.timestamp, timeframe) &&
      itemMatchesStatus(item, status, snapshot) &&
      (!deferredSearch ||
        item.userMessage.toLowerCase().includes(deferredSearch) ||
        (item.assistantResponse ?? "").toLowerCase().includes(deferredSearch))
  );
  const outputs = snapshot.outputs.filter(
    (item) =>
      (project === "all" || itemProjectId(item) === project) &&
      withinTimeframe(item.modifiedAt, timeframe) &&
      itemMatchesStatus(item, status, snapshot) &&
      (!deferredSearch ||
        item.fileName.toLowerCase().includes(deferredSearch) ||
        item.path.toLowerCase().includes(deferredSearch) ||
        item.category.toLowerCase().includes(deferredSearch))
  );

  const selectedItem =
    variant === "activity"
      ? activity.find((item) => item.id === selection) ?? null
      : variant === "conversations"
        ? conversations.find((item) => item.threadId === selection || item.id === selection) ?? null
        : outputs.find((item) => item.id === selection) ?? null;

  const activeCount =
    variant === "activity" ? activity.length : variant === "conversations" ? conversations.length : outputs.length;
  const title =
    variant === "activity" ? "Activity Feed" : variant === "conversations" ? "Conversations" : "Outputs";
  const description =
    variant === "activity"
      ? "Shared operator activity surface with task and review back-links."
      : variant === "conversations"
        ? "Transcript and thread history with deterministic selection and handoff links."
        : "Agent-generated outputs with preview context and cross-links into review.";

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="History / Handoff"
        title={title}
        description={description}
        actions={
          <>
            <Button variant="outline" onClick={() => exportSnapshot(`${variant}-view`, snapshot)}>
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
            <Button variant="outline" onClick={() => void historyQuery.refetch()} disabled={historyQuery.isFetching}>
              <RefreshCcw className={`mr-2 h-4 w-4 ${historyQuery.isFetching ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <FamilyTabs tabs={TABS} />
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Visible items"
              value={`${activeCount}`}
              detail={`Current ${variant} view after filters.`}
            />
            <StatCard
              label="Review backlog"
              value={`${snapshot.summary.reviewCount}`}
              detail="Pending approvals, failures, and file-op outputs."
              tone={snapshot.summary.reviewCount > 0 ? "warning" : "success"}
            />
            <StatCard
              label="Featured project"
              value="EoBQ"
              detail="First-class tenant across handoff flows."
            />
            <StatCard
              label="Latest refresh"
              value={formatRelativeTime(snapshot.generatedAt)}
              detail={formatTimestamp(snapshot.generatedAt)}
              detailVolatile
            />
          </div>
        </div>
      </PageHeader>

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.35fr]">
        <Card className="border-border/70 bg-card/70">
          <CardHeader>
            <CardTitle className="text-lg">Shared filters</CardTitle>
            <CardDescription>URL-backed filters round-trip across the family routes and browser history.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(event) => setSearchValue("search", event.target.value || null)}
                placeholder={`Search ${variant}`}
                className="pl-9"
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
              label="Timeframe"
              values={[
                { id: "4h", label: "4h" },
                { id: "24h", label: "24h" },
                { id: "7d", label: "7d" },
                { id: "30d", label: "30d" },
              ]}
              activeValue={timeframe}
              onChange={(value) => setSearchValue("timeframe", value)}
            />
            <FilterRow
              label="Status"
              values={[
                { id: "all", label: "All" },
                { id: "pending_approval", label: "Approval" },
                { id: "running", label: "Running" },
                { id: "completed", label: "Completed" },
                { id: "failed", label: "Failed" },
              ]}
              activeValue={status}
              onChange={(value) => setSearchValue("status", value === "all" ? null : value)}
            />
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-card/70">
          <CardHeader>
            <CardTitle className="text-lg">Cross-links</CardTitle>
            <CardDescription>Use the detail drawer to move from any item into tasks, projects, outputs, or review.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>Activity items link into related tasks and review surfaces when they require approval.</p>
            <p>Conversation threads keep their selection in the URL, so browser back restores the exact thread.</p>
            <p>Outputs stay tied to projects and task context for faster handoffs into review and work planning.</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/70 bg-card/70">
        <CardHeader>
          <CardTitle className="text-lg">
            {variant === "activity" ? "Activity feed" : variant === "conversations" ? "Conversations" : "Outputs"}
          </CardTitle>
          <CardDescription>{activeCount} items match the current filters.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {variant === "activity" ? (
            activity.length > 0 ? (
              activity.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSearchValue("selection", item.id)}
                  className="w-full rounded-2xl border border-border/70 bg-background/20 p-4 text-left transition hover:bg-accent/40"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">{getAgentName(snapshot, item.agentId)}</Badge>
                    {item.projectId ? <Badge variant="outline">{getProjectName(snapshot, item.projectId)}</Badge> : null}
                    {item.status ? <Badge variant="outline">{item.status}</Badge> : null}
                    <span className="ml-auto text-xs text-muted-foreground">{formatRelativeTime(item.timestamp)}</span>
                  </div>
                  <p className="mt-3 text-sm font-medium">{item.inputSummary}</p>
                  {item.outputSummary ? <p className="mt-2 text-sm text-muted-foreground">{item.outputSummary}</p> : null}
                  {item.toolsUsed.length > 0 ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {item.toolsUsed.map((tool) => (
                        <Badge key={`${item.id}-${tool}`} variant="outline">
                          {tool}
                        </Badge>
                      ))}
                    </div>
                  ) : null}
                </button>
              ))
            ) : (
              <EmptyState title="No activity matches the current filters" description="Widen the timeframe or clear the project and status filters." />
            )
          ) : null}

          {variant === "conversations" ? (
            conversations.length > 0 ? (
              conversations.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSearchValue("selection", item.threadId)}
                  className="w-full rounded-2xl border border-border/70 bg-background/20 p-4 text-left transition hover:bg-accent/40"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">{getAgentName(snapshot, item.agentId)}</Badge>
                    {item.projectId ? <Badge variant="outline">{getProjectName(snapshot, item.projectId)}</Badge> : null}
                    <span className="ml-auto text-xs text-muted-foreground">{formatRelativeTime(item.timestamp)}</span>
                  </div>
                  <p className="mt-3 text-sm font-medium">{item.userMessage}</p>
                  {item.assistantResponse ? (
                    <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">{item.assistantResponse}</p>
                  ) : null}
                </button>
              ))
            ) : (
              <EmptyState title="No conversations match the current filters" description="Clear the search or widen the timeframe." />
            )
          ) : null}

          {variant === "outputs" ? (
            outputs.length > 0 ? (
              outputs.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSearchValue("selection", item.id)}
                  className="w-full rounded-2xl border border-border/70 bg-background/20 p-4 text-left transition hover:bg-accent/40"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">{item.category}</Badge>
                    {item.projectId ? <Badge variant="outline">{getProjectName(snapshot, item.projectId)}</Badge> : null}
                    <span className="ml-auto text-xs text-muted-foreground">{formatRelativeTime(item.modifiedAt)}</span>
                  </div>
                  <p className="mt-3 text-sm font-medium">{item.fileName}</p>
                  <p className="mt-2 font-mono text-xs text-muted-foreground">{item.path}</p>
                </button>
              ))
            ) : (
              <EmptyState title="No outputs match the current filters" description="Try a wider timeframe or clear the search query." />
            )
          ) : null}
        </CardContent>
      </Card>

      <Sheet open={Boolean(selectedItem)} onOpenChange={(open) => setSearchValue("selection", open ? selection : null)}>
        <SheetContent side="right" className="w-full max-w-xl overflow-y-auto border-l border-border/80 bg-background/95">
          {selectedItem ? (
            <>
              <SheetHeader className="border-b border-border/80 px-6 py-5 text-left">
                <SheetTitle>
                  {"path" in selectedItem
                    ? selectedItem.fileName
                    : "userMessage" in selectedItem
                      ? getAgentName(snapshot, selectedItem.agentId)
                      : selectedItem.actionType}
                </SheetTitle>
                <SheetDescription>
                  {"path" in selectedItem
                    ? selectedItem.path
                    : getProjectName(snapshot, selectedItem.projectId ?? null)}
                </SheetDescription>
              </SheetHeader>
              <SelectionDetails item={selectedItem} snapshot={snapshot} />
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
    <div className="rounded-xl border border-border/60 bg-background/30 px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 font-medium">{value}</p>
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <div className="mt-2 rounded-xl border border-border/60 bg-background/30 p-3 text-sm">
        {children}
      </div>
    </div>
  );
}
