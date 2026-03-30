"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { LoaderCircle, RefreshCcw, Send, Square } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { StatusDot } from "@/components/status-dot";
import { getAgents } from "@/lib/api";
import { type AgentInfo, type ChatStreamEvent } from "@/lib/contracts";
import { compactText, formatRelativeTime } from "@/lib/format";
import { isOperatorSessionLocked, useOperatorSessionStatus } from "@/lib/operator-session";
import { queryKeys } from "@/lib/query-client";
import { requestJson } from "@/features/workforce/helpers";
import { readChatEventStream } from "@/lib/sse";
import { useUrlState } from "@/lib/url-state";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AgentTask {
  id: string;
  agent?: string;
  prompt?: string;
  description?: string;
  priority?: string;
  status?: string;
  model?: string;
  created_at?: string;
  started_at?: string;
}

interface AgentActivity {
  task_id?: string;
  agent_id?: string;
  action?: string;
  created_at?: string;
}

interface TrustScore {
  agent_id: string;
  agent_name: string;
  score: number;
  level: string;
}

interface AgentStats {
  tasks_completed: number;
  tasks_failed: number;
  avg_duration_ms: number;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
}

// ── Suggestions ───────────────────────────────────────────────────────────────

const SUGGESTIONS_BY_AGENT: Record<string, string[]> = {
  "general-assistant": [
    "What is the current cluster health?",
    "Summarize any recent errors or alerts.",
    "Which agents have been most active today?",
  ],
  "research-agent": [
    "What topics have you researched recently?",
    "Find recent news about vLLM performance.",
    "Summarize the latest in AI inference hardware.",
  ],
  "coding-agent": [
    "Review the latest commit for issues.",
    "Check for any TypeScript errors in the dashboard.",
    "What files were recently changed?",
  ],
  "creative-agent": [
    "Generate a short description of Athanor.",
    "Suggest names for a new monitoring feature.",
    "Write a brief status update for the cluster.",
  ],
  "knowledge-agent": [
    "What do you know about the current vLLM deployment?",
    "Retrieve notes on Qwen3.5 configuration.",
    "What is stored about FOUNDRY's GPU setup?",
  ],
  "home-agent": [
    "What automations are currently active?",
    "Show the current sensor readings.",
    "List any recent home events.",
  ],
  "media-agent": [
    "What is currently playing on Plex?",
    "Show my recent watch history.",
    "List available media libraries.",
  ],
  "stash-agent": [
    "What items are in the stash queue?",
    "Show recently saved items.",
    "Find anything saved about vLLM.",
  ],
  "data-curator": [
    "What data collections are active?",
    "Show recent ingestion activity.",
    "How many items are in the knowledge base?",
  ],
};

const AGENT_NAMES: Record<string, string> = {
  "general-assistant": "General Assistant",
  "research-agent": "Research Agent",
  "coding-agent": "Coding Agent",
  "creative-agent": "Creative Agent",
  "knowledge-agent": "Knowledge Agent",
  "home-agent": "Home Agent",
  "media-agent": "Media Agent",
  "stash-agent": "Stash Agent",
  "data-curator": "Data Curator",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function createId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function trustBarColor(score: number) {
  if (score >= 0.8) return "bg-[color:var(--signal-success)]";
  if (score >= 0.5) return "bg-[color:var(--signal-warning)]";
  return "bg-[color:var(--signal-danger)]";
}

function trustBadgeVariant(level: string) {
  if (level === "high" || level === "full") return "outline" as const;
  if (level === "medium" || level === "standard") return "secondary" as const;
  return "destructive" as const;
}

function priorityVariant(priority: string | undefined) {
  if (priority === "critical" || priority === "high") return "destructive" as const;
  if (priority === "medium") return "secondary" as const;
  return "outline" as const;
}

function elapsedSince(iso: string | undefined): string {
  if (!iso) return "--";
  const ms = Date.now() - new Date(iso).getTime();
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ${s % 60}s`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}

function taskPrompt(task: AgentTask): string {
  return task.prompt ?? task.description ?? "(no description)";
}

// ── Sub-components ────────────────────────────────────────────────────────────

function AgentRosterItem({
  agent,
  selected,
  pendingCount,
  trustScore,
  onClick,
}: {
  agent: AgentInfo;
  selected: boolean;
  pendingCount: number;
  trustScore: TrustScore | undefined;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-xl border px-3 py-2.5 text-left transition ${
        selected
          ? "surface-hero border-[color:color-mix(in_oklab,var(--accent-structural)_34%,transparent)]"
          : "surface-tile hover:bg-accent/40"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <StatusDot tone={agent.status === "ready" ? "healthy" : "muted"} />
          <span className="truncate text-sm font-medium">
            {AGENT_NAMES[agent.id] ?? agent.name}
          </span>
        </div>
        {pendingCount > 0 && (
          <Badge variant="secondary" className="shrink-0 text-xs">
            {pendingCount}
          </Badge>
        )}
      </div>
      {trustScore && (
        <div className="mt-1.5 flex items-center gap-2">
          <div className="h-1 flex-1 rounded-full bg-border/50">
            <div
              className={`h-1 rounded-full transition-all ${trustBarColor(trustScore.score)}`}
              style={{ width: `${Math.min(trustScore.score * 100, 100)}%` }}
            />
          </div>
          <span className="text-[10px] tabular-nums text-muted-foreground">
            {(trustScore.score * 100).toFixed(0)}%
          </span>
        </div>
      )}
    </button>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export function AgentWorkbench() {
  const { getSearchValue, setSearchValue } = useUrlState();
  const selectedAgentId = getSearchValue("agent", "general-assistant");
  const operatorSession = useOperatorSessionStatus();
  const liveReadEnabled = !operatorSession.isPending && !isOperatorSessionLocked(operatorSession);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const agentsQuery = useQuery({
    queryKey: queryKeys.agents,
    queryFn: getAgents,
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
  });

  const trustQuery = useQuery({
    queryKey: ["workbench-trust-scores"],
    queryFn: async (): Promise<TrustScore[]> => {
      const data = await requestJson("/api/trust");
      return (data?.scores ?? data ?? []) as TrustScore[];
    },
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  const runningTasksQuery = useQuery({
    queryKey: ["workbench-running", selectedAgentId],
    queryFn: async (): Promise<AgentTask[]> => {
      const data = await requestJson(
          `/api/workforce/tasks?agent=${encodeURIComponent(selectedAgentId)}&status=running`
      );
      return (data?.tasks ?? data ?? []) as AgentTask[];
    },
    enabled: !!selectedAgentId && liveReadEnabled,
    refetchInterval: 5_000,
    refetchIntervalInBackground: false,
  });

  const pendingTasksQuery = useQuery({
    queryKey: ["workbench-pending", selectedAgentId],
    queryFn: async (): Promise<AgentTask[]> => {
      const data = await requestJson(
          `/api/workforce/tasks?agent=${encodeURIComponent(selectedAgentId)}&status=pending`
      );
      return (data?.tasks ?? data ?? []) as AgentTask[];
    },
    enabled: !!selectedAgentId && liveReadEnabled,
    refetchInterval: 10_000,
    refetchIntervalInBackground: false,
  });

  const activityQuery = useQuery({
    queryKey: ["workbench-activity", selectedAgentId],
    queryFn: async (): Promise<AgentActivity[]> => {
      const data = await requestJson(
          `/api/activity?agent=${encodeURIComponent(selectedAgentId)}&limit=10`
      );
      return (data?.activity ?? data ?? []) as AgentActivity[];
    },
    enabled: !!selectedAgentId,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const statsQuery = useQuery({
    queryKey: ["workbench-stats", selectedAgentId],
    queryFn: async (): Promise<AgentStats | null> => {
      const data = await requestJson(
          `/api/activity/stats?agent=${encodeURIComponent(selectedAgentId)}&window=24h`
      );
      return (data?.stats ?? data ?? null) as AgentStats | null;
    },
    enabled: !!selectedAgentId,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  const agents = agentsQuery.data?.agents ?? [];
  const selectedAgent = agents.find((a) => a.id === selectedAgentId) ?? agents[0] ?? null;
  const trustScores = trustQuery.data ?? [];
  const runningTasks = runningTasksQuery.data ?? [];
  const pendingTasks = pendingTasksQuery.data ?? [];
  const stats = statsQuery.data ?? null;
  const activeTask = runningTasks[0] ?? null;

  // Scroll chat to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isStreaming]);

  // Clear chat when agent changes
  useEffect(() => {
    setMessages([]);
    setStreamError(null);
  }, [selectedAgentId]);

  function selectAgent(agent: AgentInfo) {
    setSearchValue("agent", agent.id);
  }

  function applyStreamEvent(assistantId: string, event: ChatStreamEvent) {
    if (event.type === "assistant_delta") {
      setMessages((current) =>
        current.map((msg) =>
          msg.id === assistantId
            ? { ...msg, content: `${msg.content}${event.content}` }
            : msg
        )
      );
    }
    if (event.type === "error") {
      setStreamError(event.message);
    }
  }

  async function sendMessage(promptOverride?: string) {
    const content = (promptOverride ?? input).trim();
    if (!content || !selectedAgent || isStreaming) return;

    const userMessage: ChatMessage = {
      id: createId("msg"),
      role: "user",
      content,
      createdAt: new Date().toISOString(),
    };
    const assistantMessage: ChatMessage = {
      id: createId("msg"),
      role: "assistant",
      content: "",
      createdAt: new Date().toISOString(),
    };

    setMessages((current) => [...current, userMessage, assistantMessage]);
    setInput("");
    setStreamError(null);
    setIsStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const historyMessages = [...messages, userMessage].map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target: "agent-server",
          model: selectedAgent.id,
          threadId: `workbench-${selectedAgent.id}`,
          messages: historyMessages,
        }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`Agent request failed (${response.status})`);
      }

      await readChatEventStream(response.body, (event) => {
        applyStreamEvent(assistantMessage.id, event);
      });
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setStreamError("Stopped.");
      } else {
        setStreamError(err instanceof Error ? err.message : "Request failed.");
      }
    } finally {
      abortRef.current = null;
      setIsStreaming(false);
    }
  }

  const suggestions = selectedAgent ? (SUGGESTIONS_BY_AGENT[selectedAgent.id] ?? []) : [];
  const selectedTrust = trustScores.find((t) => t.agent_id === selectedAgentId);

  if (agentsQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Agents"
          title="Agent Workbench"
          description="Agent metadata failed to load."
          attentionHref="/agents/workbench"
        />
        <ErrorPanel
          description={
            agentsQuery.error instanceof Error
              ? agentsQuery.error.message
              : "Failed to load agent metadata."
          }
        />
      </div>
    );
  }

  const successRate =
    stats && stats.tasks_completed + stats.tasks_failed > 0
      ? ((stats.tasks_completed / (stats.tasks_completed + stats.tasks_failed)) * 100).toFixed(0) +
        "%"
      : "--";

  const avgDuration =
    stats && stats.avg_duration_ms > 0
      ? stats.avg_duration_ms < 1000
        ? `${stats.avg_duration_ms}ms`
        : `${(stats.avg_duration_ms / 1000).toFixed(1)}s`
      : "--";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Agents"
        title="Agent Workbench"
        description="Real-time agent monitoring, task inspection, and direct steering."
        attentionHref="/agents/workbench"
        actions={
          <Button
            variant="outline"
            onClick={() => {
              void agentsQuery.refetch();
              void trustQuery.refetch();
            }}
            disabled={agentsQuery.isFetching}
          >
            <RefreshCcw
              className={`mr-2 h-4 w-4 ${agentsQuery.isFetching ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
        }
      />

      {/* Mobile agent selector — horizontal scroll */}
      <div className="flex gap-2 overflow-x-auto pb-1 xl:hidden">
        {agents.map((agent) => {
          const pending = pendingTasksQuery.data?.length ?? 0;
          const trust = trustScores.find((t) => t.agent_id === agent.id);
          return (
            <button
              key={agent.id}
              type="button"
              onClick={() => selectAgent(agent)}
              className={`flex shrink-0 items-center gap-2 rounded-xl border px-3 py-2 text-sm transition ${
                selectedAgent?.id === agent.id
                  ? "surface-hero border-[color:color-mix(in_oklab,var(--accent-structural)_34%,transparent)]"
                  : "surface-tile hover:bg-accent/40"
              }`}
            >
              <StatusDot tone={agent.status === "ready" ? "healthy" : "muted"} />
              <span className="font-medium">{AGENT_NAMES[agent.id] ?? agent.name}</span>
              {agent.id === selectedAgentId && pending > 0 && (
                <Badge variant="secondary" className="text-xs">
                  {pending}
                </Badge>
              )}
              {trust && (
                <span className="text-[10px] tabular-nums text-muted-foreground">
                  {(trust.score * 100).toFixed(0)}%
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Desktop three-panel layout */}
      <div className="grid gap-4 xl:grid-cols-[200px_1fr_2fr]">
        {/* Left: Agent Roster */}
        <Card className="surface-panel hidden xl:block">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Roster</CardTitle>
            <CardDescription className="text-xs">Select an agent to inspect.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {agents.map((agent) => {
              const pending =
                agent.id === selectedAgentId ? (pendingTasksQuery.data?.length ?? 0) : 0;
              const trust = trustScores.find((t) => t.agent_id === agent.id);
              return (
                <AgentRosterItem
                  key={agent.id}
                  agent={agent}
                  selected={selectedAgent?.id === agent.id}
                  pendingCount={pending}
                  trustScore={trust}
                  onClick={() => selectAgent(agent)}
                />
              );
            })}
          </CardContent>
        </Card>

        {/* Center: Work Surface */}
        <div className="space-y-4">
          {/* Current State */}
          <Card className="surface-panel">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Current State</CardTitle>
              <CardDescription className="text-xs">
                {selectedAgent?.name ?? "No agent selected"} — live task status.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {activeTask ? (
                <div className="surface-instrument space-y-3 rounded-xl border p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="font-mono text-xs text-muted-foreground">
                        {activeTask.id.slice(0, 16)}
                      </p>
                      <p className="mt-1 text-sm">{compactText(taskPrompt(activeTask), 100)}</p>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1.5">
                      <Badge variant={priorityVariant(activeTask.priority)}>
                        {activeTask.priority ?? "normal"}
                      </Badge>
                      <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                        <LoaderCircle className="h-3 w-3 animate-spin text-[color:var(--signal-success)]" />
                        {elapsedSince(activeTask.started_at ?? activeTask.created_at)}
                      </div>
                    </div>
                  </div>
                  {activeTask.model && (
                    <p className="text-xs text-muted-foreground">
                      Model: <span className="font-mono">{activeTask.model}</span>
                    </p>
                  )}
                </div>
              ) : (
                <EmptyState
                  title="No active task"
                  description="This agent is idle."
                  className="py-6"
                />
              )}
            </CardContent>
          </Card>

          {/* Task Queue */}
          <Card className="surface-panel">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base">Task Queue</CardTitle>
                  <CardDescription className="text-xs">
                    Pending tasks for {selectedAgent?.name ?? "agent"}.
                  </CardDescription>
                </div>
                {pendingTasks.length > 0 && (
                  <Badge variant="secondary">{pendingTasks.length}</Badge>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {pendingTasks.length > 0 ? (
                <div className="space-y-2">
                  {pendingTasks.map((task) => (
                    <div
                      key={task.id}
                      className="surface-instrument flex items-center justify-between gap-3 rounded-xl border px-3 py-2.5"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="font-mono text-[10px] text-muted-foreground">
                          {task.id.slice(0, 12)}
                        </p>
                        <p className="mt-0.5 truncate text-sm">
                          {compactText(taskPrompt(task), 60)}
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <Badge variant={priorityVariant(task.priority)}>
                          {task.priority ?? "normal"}
                        </Badge>
                        <span className="text-[10px] text-muted-foreground" data-volatile="true">
                          {formatRelativeTime(task.created_at ?? null)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="Queue empty"
                  description="No pending tasks for this agent."
                  className="py-6"
                />
              )}
            </CardContent>
          </Card>

          {/* Performance 24h */}
          <Card className="surface-panel">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Performance (24h)</CardTitle>
              <CardDescription className="text-xs">
                {selectedTrust ? (
                  <>
                    Trust:{" "}
                    <Badge variant={trustBadgeVariant(selectedTrust.level)} className="ml-1 text-xs">
                      {selectedTrust.level}
                    </Badge>
                    <span className="ml-2 tabular-nums">
                      {(selectedTrust.score * 100).toFixed(0)}%
                    </span>
                  </>
                ) : (
                  "Trust data unavailable."
                )}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
                <StatCard
                  label="Completed"
                  value={stats ? String(stats.tasks_completed) : "--"}
                  detail="Last 24h"
                />
                <StatCard
                  label="Failed"
                  value={stats ? String(stats.tasks_failed) : "--"}
                  detail="Last 24h"
                  tone={stats && stats.tasks_failed > 0 ? "warning" : undefined}
                />
                <StatCard label="Success Rate" value={successRate} detail="Completed / total" />
                <StatCard label="Avg Duration" value={avgDuration} detail="Per task" />
              </div>

              {selectedTrust && (
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Trust score</span>
                    <span className="tabular-nums">
                      {(selectedTrust.score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-border/50">
                    <div
                      className={`h-1.5 rounded-full transition-all ${trustBarColor(selectedTrust.score)}`}
                      style={{ width: `${Math.min(selectedTrust.score * 100, 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right: Agent Chat */}
        <Card className="surface-panel flex min-h-[36rem] flex-col overflow-hidden xl:min-h-[48rem]">
          <CardHeader className="border-b border-border/70 pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base">Agent Chat</CardTitle>
                <CardDescription className="text-xs">
                  {selectedAgent
                    ? `Direct channel to ${selectedAgent.name}.`
                    : "Select an agent to begin."}
                </CardDescription>
              </div>
              {selectedAgent && (
                <StatusDot tone={selectedAgent.status === "ready" ? "healthy" : "muted"} />
              )}
            </div>
          </CardHeader>

          <CardContent className="flex min-h-0 flex-1 flex-col overflow-hidden p-0">
            <ScrollArea className="flex-1 px-4 sm:px-5" ref={scrollRef}>
              <div className="space-y-3 py-4">
                {messages.length === 0 ? (
                  <EmptyState
                    title={selectedAgent ? `Ready for ${selectedAgent.name}` : "Select an agent"}
                    description="Send a message to steer the agent directly."
                  />
                ) : (
                  messages.map((msg) => (
                    <div key={msg.id}>
                      {msg.role === "user" ? (
                        <div className="flex justify-end">
                          <div className="max-w-[85%] rounded-2xl bg-primary px-4 py-3 text-primary-foreground">
                            <div className="mb-1.5 flex items-center justify-between gap-3 text-[10px] uppercase tracking-[0.2em] opacity-70">
                              <span>Operator</span>
                              <span data-volatile="true">
                                {formatRelativeTime(msg.createdAt)}
                              </span>
                            </div>
                            <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                          </div>
                        </div>
                      ) : (
                        <div className="max-w-[90%]">
                          <div className="rounded-2xl bg-muted px-4 py-3 text-foreground">
                            <div className="mb-1.5 flex items-center justify-between gap-3 text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                              <span>{selectedAgent?.name ?? "Agent"}</span>
                              <span data-volatile="true">
                                {formatRelativeTime(msg.createdAt)}
                              </span>
                            </div>
                            <p className="text-sm whitespace-pre-wrap">
                              {msg.content ||
                                (isStreaming ? (
                                  <span className="text-muted-foreground">Thinking...</span>
                                ) : (
                                  ""
                                ))}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>

            {streamError && (
              <div className="mx-4 mb-2 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {streamError}
              </div>
            )}

            {/* Suggestions */}
            {messages.length === 0 && suggestions.length > 0 && (
              <div className="border-t border-border/40 px-4 py-2.5">
                <div className="flex flex-wrap gap-1.5">
                  {suggestions.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      className="surface-metric rounded-full border px-3 py-1 text-xs text-muted-foreground transition hover:bg-accent/40 hover:text-foreground"
                      onClick={() => setInput(prompt)}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Input */}
            <div className="border-t border-border/70 px-4 py-3">
              <form
                className="flex gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  void sendMessage();
                }}
              >
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                      e.preventDefault();
                      void sendMessage();
                    }
                  }}
                  placeholder={
                    selectedAgent ? `Message ${selectedAgent.name}...` : "Select an agent first"
                  }
                  disabled={!selectedAgent || isStreaming}
                  className="flex-1"
                />
                {isStreaming ? (
                  <Button type="button" variant="outline" onClick={() => abortRef.current?.abort()}>
                    <Square className="h-4 w-4" />
                  </Button>
                ) : (
                  <Button type="submit" disabled={!selectedAgent || !input.trim()}>
                    <Send className="h-4 w-4" />
                  </Button>
                )}
              </form>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
