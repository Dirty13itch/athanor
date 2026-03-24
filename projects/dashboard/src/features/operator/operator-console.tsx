"use client";

import { useCallback, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  FileText,
  Inbox,
  LoaderCircle,
  MessageSquare,
  RefreshCcw,
  Send,
  Square,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { RichText } from "@/components/rich-text";
import { StatCard } from "@/components/stat-card";
import { requestJson, postWithoutBody, postJson } from "@/features/workforce/helpers";
import { formatRelativeTime } from "@/lib/format";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
}

interface PendingTask {
  id: string;
  prompt: string;
  agent_id?: string;
  agent_name?: string;
  priority?: string;
  status: string;
  created_at?: string;
}

interface PendingPlan {
  id: string;
  title?: string;
  description?: string;
  status: string;
  created_at?: string;
  agent_id?: string;
}

function createId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

const SUGGESTED_PROMPTS = [
  "What needs my attention?",
  "Show me today's plans",
  "What did agents do overnight?",
];

const PENDING_TASKS_KEY = ["operator-pending-tasks"] as const;
const PENDING_PLANS_KEY = ["operator-pending-plans"] as const;

export function OperatorConsole() {
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const pendingTasksQuery = useQuery({
    queryKey: PENDING_TASKS_KEY,
    queryFn: async (): Promise<PendingTask[]> => {
      const data = await requestJson(
        "/api/agents/proxy?path=/v1/tasks?status=pending_approval"
      );
      return (data?.tasks ?? data ?? []) as PendingTask[];
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const pendingPlansQuery = useQuery({
    queryKey: PENDING_PLANS_KEY,
    queryFn: async (): Promise<PendingPlan[]> => {
      const data = await requestJson(
        "/api/pipeline/plans?status=pending"
      );
      return (data?.plans ?? data ?? []) as PendingPlan[];
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const pendingTasks = pendingTasksQuery.data ?? [];
  const pendingPlans = pendingPlansQuery.data ?? [];
  const totalPending = pendingTasks.length + pendingPlans.length;

  const approveMutation = useMutation({
    mutationFn: async (taskId: string) => {
      await postWithoutBody(`/api/agents/proxy?path=/v1/tasks/${taskId}/approve`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PENDING_TASKS_KEY });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async ({ taskId, reason }: { taskId: string; reason: string }) => {
      await postJson(`/api/agents/proxy?path=/v1/tasks/${taskId}/reject`, { reason });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PENDING_TASKS_KEY });
    },
  });

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    });
  }, []);

  async function sendMessage(promptOverride?: string) {
    const content = (promptOverride ?? input).trim();
    if (!content || isStreaming) return;

    const userMsg: ChatMessage = {
      id: createId("msg"),
      role: "user",
      content,
      createdAt: new Date().toISOString(),
    };

    const assistantMsg: ChatMessage = {
      id: createId("msg"),
      role: "assistant",
      content: "",
      createdAt: new Date().toISOString(),
    };

    const allMessages = [...messages, userMsg];

    setMessages([...allMessages, assistantMsg]);
    setInput("");
    setError(null);
    setIsStreaming(true);
    scrollToBottom();

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch("/api/agents/proxy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path: "/v1/chat/completions",
          body: {
            model: "meta-orchestrator",
            messages: allMessages.map((m) => ({ role: m.role, content: m.content })),
            stream: true,
          },
        }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`Request failed (${response.status})`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data:")) continue;
          const payload = trimmed.slice(5).trim();
          if (payload === "[DONE]") continue;

          try {
            const parsed = JSON.parse(payload);
            const delta =
              parsed?.choices?.[0]?.delta?.content ??
              parsed?.content ??
              "";
            if (delta) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsg.id
                    ? { ...m, content: m.content + delta }
                    : m
                )
              );
              scrollToBottom();
            }
          } catch {
            // skip malformed chunks
          }
        }
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setError("Stopped.");
      } else {
        setError(err instanceof Error ? err.message : "Request failed.");
      }
    } finally {
      abortRef.current = null;
      setIsStreaming(false);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Command Center"
        title="Operator Console"
        description="Meta-orchestrator chat and approval queue."
        attentionHref="/operator"
        actions={
          <Button
            variant="outline"
            onClick={() => {
              void pendingTasksQuery.refetch();
              void pendingPlansQuery.refetch();
            }}
            disabled={pendingTasksQuery.isFetching || pendingPlansQuery.isFetching}
          >
            <RefreshCcw
              className={`mr-2 h-4 w-4 ${
                pendingTasksQuery.isFetching || pendingPlansQuery.isFetching ? "animate-spin" : ""
              }`}
            />
            Refresh
          </Button>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Messages"
            value={`${messages.length}`}
            detail="This session"
            icon={<MessageSquare className="h-5 w-5" />}
          />
          <StatCard
            label="Pending Tasks"
            value={`${pendingTasks.length}`}
            detail="Awaiting approval"
            icon={<Inbox className="h-5 w-5" />}
            tone={pendingTasks.length > 0 ? "warning" : "success"}
          />
          <StatCard
            label="Pending Plans"
            value={`${pendingPlans.length}`}
            detail="Awaiting review"
            icon={<FileText className="h-5 w-5" />}
            tone={pendingPlans.length > 0 ? "warning" : "success"}
          />
          <StatCard
            label="Total Queue"
            value={`${totalPending}`}
            detail="Tasks + plans"
            tone={totalPending > 0 ? "warning" : "success"}
          />
        </div>
      </PageHeader>

      <div className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        {/* Left: Chat Panel */}
        <Card className="surface-panel flex min-h-[32rem] flex-col overflow-hidden sm:min-h-[42rem]">
          <CardHeader className="border-b border-border/70">
            <CardTitle className="text-lg">Meta-Orchestrator</CardTitle>
            <CardDescription>
              Direct chat with the orchestration layer.
            </CardDescription>
          </CardHeader>

          <CardContent className="flex min-h-0 flex-1 flex-col overflow-hidden p-0">
            <ScrollArea className="flex-1 px-4 sm:px-6" ref={scrollRef}>
              <div className="space-y-4 py-4">
                {messages.length === 0 ? (
                  <EmptyState
                    title="Ready for commands"
                    description="Ask the meta-orchestrator about system state, plans, or overnight activity."
                  />
                ) : (
                  messages.map((msg) => (
                    <div key={msg.id}>
                      {msg.role === "user" ? (
                        <div className="flex justify-end">
                          <div className="max-w-[88%] rounded-2xl bg-primary px-4 py-3 text-primary-foreground sm:max-w-[78%]">
                            <div className="mb-2 flex items-center justify-between gap-3 text-[11px] uppercase tracking-[0.2em] opacity-70">
                              <span>Operator</span>
                              <span data-volatile="true">{formatRelativeTime(msg.createdAt)}</span>
                            </div>
                            <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                          </div>
                        </div>
                      ) : (
                        <div className="flex max-w-[92%] flex-col gap-2 sm:max-w-[84%]">
                          <div className="rounded-2xl bg-muted px-4 py-3 text-foreground">
                            <div className="mb-2 flex items-center justify-between gap-3 text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                              <span>Orchestrator</span>
                              <span data-volatile="true">{formatRelativeTime(msg.createdAt)}</span>
                            </div>
                            {msg.content ? (
                              <RichText content={msg.content} />
                            ) : isStreaming ? (
                              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                <LoaderCircle className="h-4 w-4 animate-spin" />
                                Streaming...
                              </div>
                            ) : null}
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
                {SUGGESTED_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    className="surface-metric rounded-full border px-3 py-1.5 text-xs text-muted-foreground transition hover:bg-accent/40 hover:text-foreground"
                    onClick={() => void sendMessage(prompt)}
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
                  placeholder="Message the meta-orchestrator..."
                  disabled={isStreaming}
                  className="flex-1"
                  autoFocus
                />
                {isStreaming ? (
                  <Button type="button" variant="outline" onClick={() => abortRef.current?.abort()}>
                    <Square className="mr-2 h-4 w-4" />
                    Stop
                  </Button>
                ) : null}
                <Button type="submit" disabled={!input.trim() || isStreaming}>
                  <Send className="mr-2 h-4 w-4" />
                  Send
                </Button>
              </form>
            </div>
          </CardContent>
        </Card>

        {/* Right: Approval Queue */}
        <Card className="surface-panel flex min-h-[32rem] flex-col overflow-hidden sm:min-h-[42rem]">
          <CardHeader className="border-b border-border/70">
            <CardTitle className="text-lg">Approval Queue</CardTitle>
            <CardDescription>
              Tasks and plans awaiting operator review.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col overflow-hidden p-0">
            <ScrollArea className="flex-1 px-4 sm:px-6">
              <div className="space-y-4 py-4">
                {/* Pending Tasks */}
                {pendingTasks.length > 0 ? (
                  <div className="space-y-3">
                    <h3 className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
                      Tasks ({pendingTasks.length})
                    </h3>
                    {pendingTasks.map((task) => (
                      <div
                        key={task.id}
                        className="surface-instrument space-y-2 rounded-2xl border p-3"
                      >
                        <p className="text-sm font-medium">
                          {task.prompt.length > 100
                            ? `${task.prompt.slice(0, 100)}...`
                            : task.prompt}
                        </p>
                        <div className="flex flex-wrap items-center gap-2">
                          {task.agent_name || task.agent_id ? (
                            <Badge variant="outline" className="text-xs">
                              {task.agent_name ?? task.agent_id}
                            </Badge>
                          ) : null}
                          {task.created_at ? (
                            <span className="text-xs text-muted-foreground" data-volatile="true">
                              {formatRelativeTime(task.created_at)}
                            </span>
                          ) : null}
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            onClick={() => void approveMutation.mutateAsync(task.id)}
                            disabled={approveMutation.isPending}
                          >
                            <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() =>
                              void rejectMutation.mutateAsync({
                                taskId: task.id,
                                reason: "Rejected from operator console",
                              })
                            }
                            disabled={rejectMutation.isPending}
                          >
                            <XCircle className="mr-1.5 h-3.5 w-3.5" />
                            Reject
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}

                {/* Pending Plans */}
                {pendingPlans.length > 0 ? (
                  <div className="space-y-3">
                    <h3 className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
                      Plans ({pendingPlans.length})
                    </h3>
                    {pendingPlans.map((plan) => (
                      <div
                        key={plan.id}
                        className="surface-instrument space-y-2 rounded-2xl border p-3"
                      >
                        <p className="text-sm font-medium">
                          {plan.title ?? plan.id}
                        </p>
                        {plan.description ? (
                          <p className="text-xs text-muted-foreground">
                            {plan.description.length > 120
                              ? `${plan.description.slice(0, 120)}...`
                              : plan.description}
                          </p>
                        ) : null}
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            {plan.status}
                          </Badge>
                          {plan.created_at ? (
                            <span className="text-xs text-muted-foreground" data-volatile="true">
                              {formatRelativeTime(plan.created_at)}
                            </span>
                          ) : null}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}

                {pendingTasks.length === 0 && pendingPlans.length === 0 ? (
                  <EmptyState
                    title="Queue clear"
                    description="No tasks or plans waiting for approval."
                    className="py-8"
                  />
                ) : null}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
