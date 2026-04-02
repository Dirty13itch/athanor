"use client";

import { useCallback, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Inbox,
  LoaderCircle,
  MessageSquare,
  RefreshCcw,
  Send,
  ShieldCheck,
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
import { readChatEventStream } from "@/lib/sse";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
}

interface PendingApproval {
  id: string;
  related_run_id?: string;
  related_task_id?: string;
  requested_action: string;
  privilege_class: string;
  reason: string;
  status: string;
  requested_at?: number;
  task_prompt?: string;
  task_agent_id?: string;
  task_priority?: string;
  task_status?: string;
  metadata?: Record<string, unknown>;
}

interface GovernanceSnapshot {
  current_mode?: {
    mode?: string;
    entered_at?: number;
    trigger?: string;
  };
  launch_blockers?: string[];
  launch_ready?: boolean;
  attention_posture?: {
    recommended_mode?: string;
    breaches?: string[];
  };
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

const PENDING_APPROVALS_KEY = ["operator-pending-approvals"] as const;
const GOVERNANCE_KEY = ["operator-governance"] as const;

export function OperatorConsole() {
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const pendingApprovalsQuery = useQuery({
    queryKey: PENDING_APPROVALS_KEY,
    queryFn: async (): Promise<PendingApproval[]> => {
      const data = await requestJson("/api/operator/approvals?status=pending");
      return (data?.approvals ?? data ?? []) as PendingApproval[];
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const governanceQuery = useQuery({
    queryKey: GOVERNANCE_KEY,
    queryFn: async (): Promise<GovernanceSnapshot> => {
      const data = await requestJson("/api/operator/governance");
      return (data ?? {}) as GovernanceSnapshot;
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const pendingApprovals = pendingApprovalsQuery.data ?? [];
  const governance = governanceQuery.data ?? {};
  const currentMode = governance.current_mode?.mode ?? "unknown";
  const launchBlockers = governance.launch_blockers ?? [];
  const attentionBreaches = governance.attention_posture?.breaches ?? [];

  const approveMutation = useMutation({
    mutationFn: async (approvalId: string) => {
      await postWithoutBody(`/api/operator/approvals/${encodeURIComponent(approvalId)}/approve`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PENDING_APPROVALS_KEY });
      void queryClient.invalidateQueries({ queryKey: GOVERNANCE_KEY });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async ({ approvalId, reason }: { approvalId: string; reason: string }) => {
      await postJson(`/api/operator/approvals/${encodeURIComponent(approvalId)}/reject`, { reason });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PENDING_APPROVALS_KEY });
      void queryClient.invalidateQueries({ queryKey: GOVERNANCE_KEY });
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
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target: "agent-server",
          model: "meta-orchestrator",
          messages: allMessages.map((m) => ({ role: m.role, content: m.content })),
        }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`Request failed (${response.status})`);
      }

      let assistantContent = "";
      await readChatEventStream(response.body, (event) => {
        if (event.type === "assistant_delta") {
          assistantContent += event.content;
          setMessages((prev) =>
            prev.map((message) =>
              message.id === assistantMsg.id
                ? { ...message, content: assistantContent }
                : message
            )
          );
          scrollToBottom();
        }

        if (event.type === "error") {
          setError(event.message);
        }
      });
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
              void pendingApprovalsQuery.refetch();
              void governanceQuery.refetch();
            }}
            disabled={pendingApprovalsQuery.isFetching || governanceQuery.isFetching}
          >
            <RefreshCcw
              className={`mr-2 h-4 w-4 ${
                pendingApprovalsQuery.isFetching || governanceQuery.isFetching ? "animate-spin" : ""
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
            label="Pending Approvals"
            value={`${pendingApprovals.length}`}
            detail="Canonical approval requests."
            icon={<Inbox className="h-5 w-5" />}
            tone={pendingApprovals.length > 0 ? "warning" : "success"}
          />
          <StatCard
            label="System Mode"
            value={currentMode}
            detail={governance.attention_posture?.recommended_mode ? `Recommended: ${governance.attention_posture.recommended_mode}` : "Governance posture"}
            icon={<ShieldCheck className="h-5 w-5" />}
            tone={currentMode === "normal" ? "success" : "warning"}
          />
          <StatCard
            label="Launch Blockers"
            value={`${launchBlockers.length}`}
            detail={governance.launch_ready ? "Launch posture is clear." : "Still blocking promotion."}
            icon={<AlertTriangle className="h-5 w-5" />}
            tone={launchBlockers.length > 0 ? "warning" : "success"}
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
              Canonical approval requests and launch posture.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col overflow-hidden p-0">
            <ScrollArea className="flex-1 px-4 sm:px-6">
              <div className="space-y-4 py-4">
                <div className="surface-instrument space-y-3 rounded-2xl border p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={governance.launch_ready ? "secondary" : "outline"}>{currentMode}</Badge>
                    <span className="text-xs text-muted-foreground">
                      {governance.current_mode?.entered_at
                        ? formatRelativeTime(new Date(governance.current_mode.entered_at * 1000).toISOString())
                        : "Mode history unavailable"}
                    </span>
                  </div>
                  <p className="text-sm font-medium">
                    {governance.current_mode?.trigger
                      ? `Entered via ${governance.current_mode.trigger}`
                      : "No mode trigger recorded."}
                  </p>
                  {launchBlockers.length > 0 ? (
                    <div className="space-y-1">
                      <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
                        Launch blockers
                      </p>
                      {launchBlockers.slice(0, 3).map((blocker) => (
                        <p key={blocker} className="text-xs text-amber-600">
                          {blocker}
                        </p>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-emerald-600">Launch posture is clear.</p>
                  )}
                  {attentionBreaches.length > 0 ? (
                    <p className="text-xs text-muted-foreground">
                      Attention pressure: {attentionBreaches.join(", ")}
                    </p>
                  ) : null}
                </div>

                {pendingApprovals.length > 0 ? (
                  <div className="space-y-3">
                    <h3 className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
                      Approvals ({pendingApprovals.length})
                    </h3>
                    {pendingApprovals.map((approval) => (
                      <div
                        key={approval.id}
                        className="surface-instrument space-y-2 rounded-2xl border p-3"
                      >
                        <p className="text-sm font-medium">
                          {(approval.task_prompt || approval.reason).length > 140
                            ? `${(approval.task_prompt || approval.reason).slice(0, 140)}...`
                            : (approval.task_prompt || approval.reason)}
                        </p>
                        <div className="flex flex-wrap items-center gap-2">
                          {approval.task_agent_id ? (
                            <Badge variant="outline" className="text-xs">
                              {approval.task_agent_id}
                            </Badge>
                          ) : null}
                          {approval.task_priority ? (
                            <Badge variant="secondary" className="text-xs">
                              {approval.task_priority}
                            </Badge>
                          ) : null}
                          <Badge variant="outline" className="text-xs">
                            {approval.privilege_class}
                          </Badge>
                          <Badge variant="secondary" className="text-xs">
                            {approval.requested_action}
                          </Badge>
                          {approval.related_run_id ? (
                            <span className="text-xs text-muted-foreground">{approval.related_run_id}</span>
                          ) : null}
                          {approval.requested_at ? (
                            <span className="text-xs text-muted-foreground" data-volatile="true">
                              {formatRelativeTime(new Date(approval.requested_at * 1000).toISOString())}
                            </span>
                          ) : null}
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            onClick={() => void approveMutation.mutateAsync(approval.id)}
                            disabled={approveMutation.isPending || !approval.id}
                          >
                            <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() =>
                              void rejectMutation.mutateAsync({
                                approvalId: approval.id,
                                reason: "Rejected from operator console",
                              })
                            }
                            disabled={rejectMutation.isPending || !approval.id}
                          >
                            <XCircle className="mr-1.5 h-3.5 w-3.5" />
                            Reject
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}

                {pendingApprovals.length === 0 ? (
                  <EmptyState
                    title="Queue clear"
                    description="No approval requests are waiting for operator action."
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
