"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Clapperboard,
  Copy,
  Download,
  Home,
  LoaderCircle,
  Plus,
  RefreshCcw,
  Send,
  Square,
  Terminal,
  Trash2,
  Wrench,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { AgentCrewBar } from "@/components/agent-crew-bar";
import { GovernorCard } from "@/components/governor-card";
import { ModelGovernanceCard } from "@/components/model-governance-card";
import { RoutingContextCard } from "@/components/routing-context-card";
import { SubscriptionControlCard } from "@/components/subscription-control-card";
import { SystemMapCard } from "@/components/system-map-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { RichText } from "@/components/rich-text";
import { StatCard } from "@/components/stat-card";
import { StatusDot } from "@/components/status-dot";
import { getAgents } from "@/lib/api";
import {
  type AgentInfo,
  type AgentThread,
  type AgentsSnapshot,
  type ChatStreamEvent,
  type TranscriptMessage,
  type UiPreferences,
} from "@/lib/contracts";
import { formatRelativeTime, formatTimestamp } from "@/lib/format";
import { queryKeys } from "@/lib/query-client";
import {
  DEFAULT_UI_PREFERENCES,
  STORAGE_KEYS,
  usePersistentState,
} from "@/lib/state";
import { readChatEventStream } from "@/lib/sse";
import { useUrlState } from "@/lib/url-state";

const AGENT_CHAT_TARGET = "agent-server";

const ICON_MAP = {
  terminal: Terminal,
  film: Clapperboard,
  home: Home,
} as const;

const SUGGESTIONS_BY_AGENT: Record<string, string[]> = {
  "general-assistant": [
    "Check service health and call out anything degraded.",
    "How are the GPUs doing right now?",
    "What models are loaded across the cluster?",
  ],
  "media-agent": [
    "What is currently playing on Plex?",
    "Search for Severance and tell me what you find.",
    "Show my recent watch history.",
  ],
  "home-agent": [
    "What lights are currently on?",
    "List the available automations.",
    "Set the living room to 75%.",
  ],
};

function createId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function exportThread(thread: AgentThread) {
  const blob = new Blob([JSON.stringify(thread, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `athanor-agent-thread-${thread.id}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function AgentConsole({ initialAgents }: { initialAgents: AgentsSnapshot }) {
  const { getSearchValue, setSearchValue } = useUrlState();
  const selectedAgentId = getSearchValue("agent", "");
  const threadId = getSearchValue("thread", "");
  const [threads, setThreads] = usePersistentState<AgentThread[]>(STORAGE_KEYS.agentThreads, []);
  const [preferences, setPreferences] = usePersistentState<UiPreferences>(
    STORAGE_KEYS.uiPreferences,
    DEFAULT_UI_PREFERENCES
  );
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [pendingThreadId, setPendingThreadId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const agentsQuery = useQuery({
    queryKey: queryKeys.agents,
    queryFn: getAgents,
    initialData: initialAgents,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [threadId, threads, pendingThreadId]);

  const agentsSnapshot = agentsQuery.data ?? initialAgents;
  const activeAgent =
    agentsSnapshot.agents.find((agent) => agent.id === selectedAgentId) ??
    agentsSnapshot.agents.find((agent) => agent.id === preferences.lastSelectedAgentId) ??
    agentsSnapshot.agents.find((agent) => agent.status === "ready") ??
    null;
  const resolvedThreadId = threadId || pendingThreadId || "";
  const activeThread = threads.find((thread) => thread.id === resolvedThreadId) ?? null;

  function persistThread(nextThread: AgentThread) {
    setThreads((current) => {
      const existing = current.filter((thread) => thread.id !== nextThread.id);
      return [nextThread, ...existing].sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
    });
  }

  function mutateThread(targetThreadId: string, mutator: (thread: AgentThread) => AgentThread) {
    setThreads((current) => {
      const thread = current.find((entry) => entry.id === targetThreadId);
      if (!thread) {
        return current;
      }

      const nextThread = mutator(thread);
      const existing = current.filter((entry) => entry.id !== targetThreadId);
      return [nextThread, ...existing].sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
    });
  }

  function createThread(agent: AgentInfo | null = activeAgent) {
    if (!agent) {
      return null;
    }

    const thread: AgentThread = {
      id: createId("thread"),
      agentId: agent.id,
      title: `New ${agent.name} thread`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: [],
    };
    persistThread(thread);
    setPendingThreadId(thread.id);
    setSearchValue("thread", thread.id);
    setSearchValue("agent", agent.id);
    setPreferences((current) => ({ ...current, lastSelectedAgentId: agent.id }));
    return thread;
  }

  function applyStreamEvent(thread: AgentThread, assistantId: string, event: ChatStreamEvent) {
    if (event.type === "assistant_delta") {
      return {
        ...thread,
        updatedAt: new Date().toISOString(),
        messages: thread.messages.map((message) =>
          message.id === assistantId
            ? { ...message, content: `${message.content}${event.content}` }
            : message
        ),
      };
    }

    if (event.type === "tool_start") {
      return {
        ...thread,
        updatedAt: new Date().toISOString(),
        messages: thread.messages.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                toolCalls: [
                  ...(message.toolCalls ?? []),
                  {
                    id: event.toolCallId,
                    name: event.name,
                    args: event.args,
                    status: "running" as const,
                  },
                ],
              }
            : message
        ),
      };
    }

    if (event.type === "tool_end") {
      return {
        ...thread,
        updatedAt: new Date().toISOString(),
        messages: thread.messages.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                toolCalls: (message.toolCalls ?? []).map((toolCall) =>
                  toolCall.id === event.toolCallId
                    ? {
                        ...toolCall,
                        output: event.output,
                        durationMs: event.durationMs,
                        status: (event.error ? "error" : "done") as "error" | "done",
                      }
                    : toolCall
                ),
              }
            : message
        ),
      };
    }

    return thread;
  }

  async function sendMessage(promptOverride?: string) {
    const content = (promptOverride ?? input).trim();
    if (!content || !activeAgent || isStreaming) {
      return;
    }

    const userMessage: TranscriptMessage = {
      id: createId("msg"),
      role: "user",
      content,
      createdAt: new Date().toISOString(),
    };
    const assistantMessage: TranscriptMessage = {
      id: createId("msg"),
      role: "assistant",
      content: "",
      createdAt: new Date().toISOString(),
      toolCalls: [],
    };

    const baseThread = activeThread ?? createThread();
    if (!baseThread) {
      return;
    }

    const nextThread: AgentThread = {
      ...baseThread,
      agentId: activeAgent.id,
      title: baseThread.messages.length === 0 ? content.slice(0, 48) : baseThread.title,
      updatedAt: new Date().toISOString(),
      messages: [...baseThread.messages, userMessage, assistantMessage],
    };
    persistThread(nextThread);
    setPendingThreadId(nextThread.id);
    setSearchValue("thread", nextThread.id);

    setInput("");
    setError(null);
    setIsStreaming(true);
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target: AGENT_CHAT_TARGET,
          model: activeAgent.id,
          threadId: nextThread.id,
          messages: nextThread.messages
            .filter((message) => message.id !== assistantMessage.id)
            .map((message) => ({ role: message.role, content: message.content })),
        }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`Agent request failed (${response.status})`);
      }

      await readChatEventStream(response.body, (event) => {
        mutateThread(nextThread.id, (current) => applyStreamEvent(current, assistantMessage.id, event));
        if (event.type === "error") {
          setError(event.message);
        }
      });
    } catch (streamError) {
      if (
        streamError instanceof DOMException &&
        streamError.name === "AbortError"
      ) {
        setError("Agent run stopped.");
      } else {
        setError(streamError instanceof Error ? streamError.message : "Agent request failed.");
      }
    } finally {
      abortRef.current = null;
      setIsStreaming(false);
    }
  }

  function selectAgent(agent: AgentInfo) {
    setSearchValue("agent", agent.id);
    setPreferences((current) => ({ ...current, lastSelectedAgentId: agent.id }));
    setPendingThreadId(null);
    if (!threads.some((thread) => thread.agentId === agent.id)) {
      createThread(agent);
    }
  }

  if (agentsQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Agents"
          title="Agent Console"
          description="Agent metadata failed to load."
          attentionHref="/agents"
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

  const suggestionList = activeAgent ? SUGGESTIONS_BY_AGENT[activeAgent.id] ?? [] : [];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Agents"
        title="Agent Console"
        description="Persisted agent threads with stable tool timelines, normalized streaming, and quick session management."
        attentionHref="/agents"
        actions={
          <>
            <Button variant="outline" onClick={() => void agentsQuery.refetch()} disabled={agentsQuery.isFetching}>
              <RefreshCcw className={`mr-2 h-4 w-4 ${agentsQuery.isFetching ? "animate-spin" : ""}`} />
              Refresh agents
            </Button>
            <Button variant="outline" onClick={() => activeThread && exportThread(activeThread)} disabled={!activeThread}>
              <Download className="mr-2 h-4 w-4" />
              Export thread
            </Button>
            <Button onClick={() => createThread()}>
              <Plus className="mr-2 h-4 w-4" />
              New thread
            </Button>
          </>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Ready agents" value={`${agentsSnapshot.agents.filter((agent) => agent.status === "ready").length}/${agentsSnapshot.agents.length}`} detail="Live agent availability." icon={<Terminal className="h-5 w-5" />} />
          <StatCard label="Threads" value={`${threads.length}`} detail="Persisted in this browser." icon={<Wrench className="h-5 w-5" />} />
          <StatCard label="Selected tools" value={`${activeAgent?.tools.length ?? 0}`} detail={activeAgent ? activeAgent.name : "Choose an agent"} />
          <StatCard label="Thread id" value={activeThread ? activeThread.id.slice(0, 8) : "--"} detail={activeThread ? formatRelativeTime(activeThread.updatedAt) : "No active thread"} />
        </div>
      </PageHeader>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="surface-hero">
          <CardHeader>
            <CardTitle className="text-lg">Crew surface</CardTitle>
            <CardDescription>
              Live agent presence, lens-aware highlighting, and direct detail access.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <AgentCrewBar />
          </CardContent>
        </Card>

        <div className="grid gap-4">
          <SubscriptionControlCard
            title="Subscription broker"
            description="Provider availability, policy routing, and recent premium execution leases."
            requester="coding-agent"
            taskClass="multi_file_implementation"
            compact
          />
          <RoutingContextCard
            key={activeAgent?.id ?? "general-assistant"}
            title="Agent routing preview"
            description="Preview how the current agent lane will be enriched and routed before execution."
            defaultAgent={activeAgent?.id ?? "general-assistant"}
            defaultPrompt="Review the current repo state and identify the next safe implementation batch."
          />
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <SystemMapCard />
        <GovernorCard compact />
        <ModelGovernanceCard />
      </div>

      <div className="grid gap-4 xl:grid-cols-[18rem_18rem_1fr]">
        <Card className="surface-panel order-2 xl:order-none">
          <CardHeader>
            <CardTitle className="text-lg">Agent roster</CardTitle>
            <CardDescription>Choose an agent capability surface.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {agentsSnapshot.agents.map((agent) => {
              const Icon = ICON_MAP[agent.icon as keyof typeof ICON_MAP] ?? Terminal;
              return (
                <button
                  key={agent.id}
                  type="button"
                  onClick={() => selectAgent(agent)}
                  disabled={agent.status !== "ready"}
                  className={`w-full rounded-2xl border p-4 text-left transition ${
                    activeAgent?.id === agent.id
                        ? "surface-hero border-[color:color-mix(in_oklab,var(--accent-structural)_34%,transparent)]"
                        : "surface-tile hover:bg-accent/40"
                    } ${agent.status !== "ready" ? "opacity-60" : ""}`}
                >
                  <div className="flex items-start gap-3">
                    <div className="surface-metric rounded-xl border p-2">
                      <Icon className="h-4 w-4 text-primary" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="truncate font-medium">{agent.name}</p>
                        <StatusDot tone={agent.status === "ready" ? "healthy" : "muted"} />
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{agent.description}</p>
                      <p className="mt-2 text-xs text-muted-foreground">{agent.tools.length} tools</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </CardContent>
        </Card>

        <Card className="surface-panel order-3 xl:order-none">
          <CardHeader>
            <CardTitle className="text-lg">Threads</CardTitle>
            <CardDescription>Continue a prior run or start fresh.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {threads.filter((thread) => !activeAgent || thread.agentId === activeAgent.id).length > 0 ? (
              threads
                .filter((thread) => !activeAgent || thread.agentId === activeAgent.id)
                .map((thread) => (
                  <button
                    key={thread.id}
                    type="button"
                    onClick={() => {
                      setPendingThreadId(thread.id);
                      setSearchValue("thread", thread.id);
                      setSearchValue("agent", thread.agentId);
                    }}
                    className={`w-full rounded-2xl border p-4 text-left transition ${
                      resolvedThreadId === thread.id
                        ? "surface-hero border-[color:color-mix(in_oklab,var(--accent-structural)_34%,transparent)]"
                        : "surface-tile hover:bg-accent/40"
                    }`}
                  >
                    <p className="truncate font-medium">{thread.title}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                      {thread.messages.length} messages
                    </p>
                    <p className="mt-2 text-xs text-muted-foreground" data-volatile="true">
                      {formatRelativeTime(thread.updatedAt)}
                    </p>
                  </button>
                ))
            ) : (
              <EmptyState title="No threads yet" description="Create a new thread for the selected agent to begin." />
            )}
          </CardContent>
        </Card>

        <Card className="surface-panel order-1 flex min-h-[32rem] flex-col overflow-hidden sm:min-h-[42rem] xl:order-none">
          <CardHeader className="border-b border-border/70">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle className="text-lg">Conversation</CardTitle>
                <CardDescription>
                  {activeAgent ? `Threaded run with ${activeAgent.name}` : "Choose an agent to begin."}
                </CardDescription>
              </div>
              {activeThread ? (
                <Badge variant="outline" data-volatile="true">
                  {formatTimestamp(activeThread.updatedAt)}
                </Badge>
              ) : null}
            </div>
          </CardHeader>

          <CardContent className="flex min-h-0 flex-1 flex-col overflow-hidden p-0">
            <ScrollArea className="flex-1 px-4 sm:px-6" ref={scrollRef}>
              <div className="space-y-4 py-4">
                {!activeThread || activeThread.messages.length === 0 ? (
                  <EmptyState
                    title={activeAgent ? `Ready for ${activeAgent.name}` : "Choose an agent to begin"}
                    description="The console will stream tool activity and the final assistant response into the same persisted thread."
                  />
                ) : (
                  activeThread.messages.map((message) => (
                    <div key={message.id}>
                      {message.role === "user" ? (
                        <div className="flex justify-end">
                          <div className="max-w-[88%] rounded-2xl bg-primary px-4 py-3 text-primary-foreground sm:max-w-[78%]">
                            <div className="mb-2 flex items-center justify-between gap-3 text-[11px] uppercase tracking-[0.2em] opacity-70">
                              <span>Operator</span>
                              <span data-volatile="true">{formatRelativeTime(message.createdAt)}</span>
                            </div>
                            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                          </div>
                        </div>
                      ) : (
                        <div className="flex max-w-[92%] flex-col gap-2 sm:max-w-[84%]">
                          {(message.toolCalls ?? []).map((toolCall) => (
                            <div key={toolCall.id} className="surface-instrument rounded-2xl border p-4">
                              <div className="flex items-center gap-3">
                                {toolCall.status === "running" ? (
                                  <LoaderCircle className="h-4 w-4 animate-spin text-primary" />
                                ) : (
                                  <Wrench className="h-4 w-4 text-primary" />
                                )}
                                <div className="min-w-0 flex-1">
                                  <p className="font-mono text-sm">{toolCall.name}</p>
                                  <p className="text-xs text-muted-foreground">
                                    {toolCall.durationMs ? `${toolCall.durationMs}ms` : toolCall.status}
                                  </p>
                                </div>
                                <Badge variant={toolCall.status === "error" ? "destructive" : "outline"}>
                                  {toolCall.status}
                                </Badge>
                              </div>
                              {toolCall.output ? (
                                <pre className="mt-3 max-h-48 overflow-y-auto whitespace-pre-wrap rounded-xl border border-border/60 bg-background/60 p-3 font-mono text-xs text-muted-foreground">
                                  {toolCall.output}
                                </pre>
                              ) : null}
                            </div>
                          ))}

                          <div className="rounded-2xl bg-muted px-4 py-3 text-foreground">
                            <div className="mb-2 flex items-center justify-between gap-3 text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                              <span>{activeAgent?.name ?? "Agent"}</span>
                              <span data-volatile="true">{formatRelativeTime(message.createdAt)}</span>
                            </div>
                            <RichText content={message.content || (isStreaming ? "Streaming..." : "")} />
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>

            {error ? (
              <div className="mx-4 mb-2 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive sm:mx-6">
                {error}
              </div>
            ) : null}

            <div className="border-t border-border/70 px-4 py-3 sm:px-6">
              <div className="mb-3 flex flex-wrap gap-2">
                {suggestionList.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    className="surface-metric rounded-full border px-3 py-1.5 text-xs text-muted-foreground transition hover:bg-accent/40 hover:text-foreground"
                    onClick={() => setInput(prompt)}
                  >
                    {prompt}
                  </button>
                ))}
              </div>

              <form
                className="flex flex-col gap-2 sm:flex-row"
                onSubmit={(event) => {
                  event.preventDefault();
                  void sendMessage();
                }}
              >
                <Input
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                      event.preventDefault();
                      void sendMessage();
                    }
                  }}
                  placeholder={activeAgent ? `Message ${activeAgent.name}...` : "Select an agent first"}
                  disabled={!activeAgent || isStreaming}
                  className="flex-1"
                  autoFocus
                />
                {isStreaming ? (
                  <Button type="button" variant="outline" onClick={() => abortRef.current?.abort()}>
                    <Square className="mr-2 h-4 w-4" />
                    Stop
                  </Button>
                ) : null}
                <Button type="submit" disabled={!activeAgent || !input.trim() || isStreaming}>
                  <Send className="mr-2 h-4 w-4" />
                  Send
                </Button>
                {activeThread ? (
                  <>
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() =>
                        navigator.clipboard.writeText(
                          activeThread.messages
                            .map((message) => `${message.role.toUpperCase()}: ${message.content}`)
                            .join("\n\n")
                        )
                      }
                    >
                      <Copy className="mr-2 h-4 w-4" />
                      Copy
                    </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={() => {
                        setPendingThreadId(null);
                        setSearchValue("thread", null);
                        setThreads((current) =>
                          current.filter((thread) => thread.id !== activeThread.id)
                        );
                      }}
                    >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Remove
                      </Button>
                  </>
                ) : null}
              </form>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
