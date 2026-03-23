"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bot, Copy, Download, MessageSquare, Plus, RefreshCcw, Send, Square, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { RichText } from "@/components/rich-text";
import { RoutingContextCard } from "@/components/routing-context-card";
import { StatCard } from "@/components/stat-card";
import { StatusDot } from "@/components/status-dot";
import { getModels } from "@/lib/api";
import {
  type DirectChatSession,
  type ModelsSnapshot,
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

const SUGGESTED_PROMPTS = [
  "Summarize the current Athanor stack and the top operational risks.",
  "Give me a maintenance checklist for the next homelab window.",
  "Compare the likely use cases for the currently available models.",
  "Suggest three ways to improve GPU utilization this week.",
];

function createId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function getModelKey(target: string, modelId: string) {
  return `${target}::${modelId}`;
}

function exportSession(session: DirectChatSession) {
  const blob = new Blob([JSON.stringify(session, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `athanor-chat-${session.id}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function DirectChatConsole({ initialModels }: { initialModels: ModelsSnapshot }) {
  const { getSearchValue, setSearchValue } = useUrlState();
  const sessionId = getSearchValue("session", "");
  const urlModelKey = getSearchValue("model", "");
  const [sessions, setSessions] = usePersistentState<DirectChatSession[]>(STORAGE_KEYS.directChatSessions, []);
  const [promptHistory, setPromptHistory] = usePersistentState<string[]>(STORAGE_KEYS.promptHistory, []);
  const [preferences, setPreferences] = usePersistentState<UiPreferences>(
    STORAGE_KEYS.uiPreferences,
    DEFAULT_UI_PREFERENCES
  );
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [pendingSessionId, setPendingSessionId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const modelsQuery = useQuery({
    queryKey: queryKeys.models,
    queryFn: getModels,
    initialData: initialModels,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [sessions, sessionId, pendingSessionId]);

  const snapshot = modelsQuery.data ?? initialModels;
  const modelKey = urlModelKey || preferences.lastSelectedModelKey || "";
  const resolvedSessionId = sessionId || pendingSessionId || "";
  const activeSession = sessions.find((session) => session.id === resolvedSessionId) ?? null;
  const currentModelKey =
    activeSession ? getModelKey(activeSession.target, activeSession.modelId) : modelKey;
  const selectedModel =
    snapshot.models.find((model) => getModelKey(model.target, model.id) === currentModelKey) ??
    snapshot.models[0] ??
    null;

  function persistSession(nextSession: DirectChatSession) {
    setSessions((current) => {
      const existing = current.filter((session) => session.id !== nextSession.id);
      return [nextSession, ...existing].sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
    });
  }

  function mutateSession(
    targetSessionId: string,
    mutator: (session: DirectChatSession) => DirectChatSession
  ) {
    setSessions((current) => {
      const session = current.find((entry) => entry.id === targetSessionId);
      if (!session) {
        return current;
      }

      const nextSession = mutator(session);
      const existing = current.filter((entry) => entry.id !== targetSessionId);
      return [nextSession, ...existing].sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
    });
  }

  function createSession(model = selectedModel) {
    if (!model) {
      return null;
    }

    const session: DirectChatSession = {
      id: createId("chat"),
      title: `New ${model.id.replace(/^\/models\//, "")} session`,
      modelId: model.id,
      target: model.target,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: [],
    };
    persistSession(session);
    setPendingSessionId(session.id);
    setSearchValue("session", session.id);
    setSearchValue("model", getModelKey(model.target, model.id));
    setPreferences((current) => ({
      ...current,
      lastSelectedModelKey: getModelKey(model.target, model.id),
    }));
    return session;
  }

  async function sendMessage(promptOverride?: string) {
    const content = (promptOverride ?? input).trim();
    if (!content || !selectedModel || isStreaming) {
      return;
    }

    setIsCreatingSession(false);
    setError(null);
    setPromptHistory((current) => [content, ...current.filter((entry) => entry !== content)].slice(0, 10));

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
    };

    const baseSession = activeSession ?? createSession();
    if (!baseSession) {
      return;
    }

    const nextSession: DirectChatSession = {
      ...baseSession,
      title:
        baseSession.messages.length === 0
          ? content.slice(0, 48)
          : baseSession.title,
      modelId: selectedModel.id,
      target: selectedModel.target,
      updatedAt: new Date().toISOString(),
      messages: [...baseSession.messages, userMessage, assistantMessage],
    };
    persistSession(nextSession);
    setPendingSessionId(nextSession.id);
    setSearchValue("session", nextSession.id);

    setInput("");
    setIsStreaming(true);
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target: selectedModel.target,
          model: selectedModel.id,
          messages: nextSession.messages
            .filter((message) => message.id !== assistantMessage.id)
            .map((message) => ({ role: message.role, content: message.content })),
        }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`Chat request failed (${response.status})`);
      }

      let assistantContent = "";
      const toolCalls: Array<{id: string; name: string; args?: Record<string, unknown>; output?: string; durationMs?: number; error?: string; status: "running" | "done" | "error"}> = [];
      await readChatEventStream(response.body, (event) => {
        if (event.type === "assistant_delta") {
          assistantContent += event.content;
          mutateSession(nextSession.id, (current) => ({
            ...current,
            updatedAt: new Date().toISOString(),
            messages: current.messages.map((message) =>
              message.id === assistantMessage.id
                ? { ...message, content: assistantContent }
                : message
            ),
          }));
        }

        if (event.type === "tool_start") {
          toolCalls.push({
            id: event.toolCallId,
            name: event.name,
            args: event.args,
            status: "running"
          });
          // Add tool indicator to assistant content
          assistantContent += `\n\n🔧 **Tool: ${event.name}** (running...)\n`;
          mutateSession(nextSession.id, (current) => ({
            ...current,
            messages: current.messages.map((message) =>
              message.id === assistantMessage.id
                ? { ...message, content: assistantContent }
                : message
            ),
          }));
        }

        if (event.type === "tool_end") {
          const tc = toolCalls.find(t => t.id === event.toolCallId);
          if (tc) {
            tc.status = event.error ? "error" : "done";
            tc.output = event.output;
            tc.durationMs = event.durationMs;
            tc.error = event.error;
          }
          const duration = event.durationMs ? ` (${Math.round(event.durationMs)}ms)` : "";
          const status = event.error ? "❌" : "✅";
          // Replace the running indicator with result
          assistantContent = assistantContent.replace(
            `🔧 **Tool: ${event.name}** (running...)`,
            `${status} **Tool: ${event.name}**${duration}`
          );
          if (event.output && event.output.length < 200) {
            assistantContent += `\n> ${event.output}\n`;
          }
          mutateSession(nextSession.id, (current) => ({
            ...current,
            messages: current.messages.map((message) =>
              message.id === assistantMessage.id
                ? { ...message, content: assistantContent }
                : message
            ),
          }));
        }

        if (event.type === "error") {
          setError(event.message);
        }
      });
    } catch (streamError) {
      if (
        streamError instanceof DOMException &&
        streamError.name === "AbortError"
      ) {
        setError("Generation stopped.");
      } else {
        setError(streamError instanceof Error ? streamError.message : "Chat failed.");
      }
    } finally {
      abortRef.current = null;
      setIsStreaming(false);
    }
  }

  function selectModel(target: string, modelId: string) {
    const nextKey = getModelKey(target, modelId);
    setSearchValue("model", nextKey);
    setPreferences((current) => ({ ...current, lastSelectedModelKey: nextKey }));
    setIsCreatingSession(true);
    setPendingSessionId(null);
  }

  if (modelsQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Inference" title="Direct Chat" description="Model inventory failed to load." />
        <ErrorPanel
          description={
            modelsQuery.error instanceof Error
              ? modelsQuery.error.message
              : "Failed to load model inventory."
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Inference"
        title="Direct Chat"
        description="Persisted model sessions, prompt history, richer transcripts, and normalized stream handling across all inference backends."
        actions={
          <>
            <Button variant="outline" onClick={() => void modelsQuery.refetch()} disabled={modelsQuery.isFetching}>
              <RefreshCcw className={`mr-2 h-4 w-4 ${modelsQuery.isFetching ? "animate-spin" : ""}`} />
              Refresh models
            </Button>
            <Button
              variant="outline"
              onClick={() => activeSession && exportSession(activeSession)}
              disabled={!activeSession}
            >
              <Download className="mr-2 h-4 w-4" />
              Export session
            </Button>
            <Button onClick={() => createSession()}>
              <Plus className="mr-2 h-4 w-4" />
              New session
            </Button>
          </>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Models" value={`${snapshot.models.length}`} detail="Discovered across reachable backends." icon={<Bot className="h-5 w-5" />} />
          <StatCard label="Backends" value={`${snapshot.backends.filter((backend) => backend.reachable).length}/${snapshot.backends.length}`} detail="Reachable inference runtimes." />
          <StatCard label="Sessions" value={`${sessions.length}`} detail="Persisted in this browser." icon={<MessageSquare className="h-5 w-5" />} />
          <StatCard label="Selected model" value={selectedModel ? selectedModel.id.replace(/^\/models\//, "") : "--"} detail={selectedModel ? selectedModel.backend : "Choose a model"} />
        </div>
      </PageHeader>

      <RoutingContextCard
        title="Routing preview"
        description="Preview shared routing and context injection before dispatching a direct prompt."
        defaultAgent="general-assistant"
        defaultPrompt={SUGGESTED_PROMPTS[0]}
      />

      <div className="grid gap-4 xl:grid-cols-[18rem_18rem_1fr]">
        <Card className="surface-panel">
          <CardHeader>
            <CardTitle className="text-lg">Sessions</CardTitle>
            <CardDescription>Start fresh or continue recent work.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {sessions.length > 0 ? (
              sessions.map((session) => (
                <button
                  key={session.id}
                  type="button"
                  onClick={() => {
                    setPendingSessionId(session.id);
                    setSearchValue("session", session.id);
                  }}
                  className={`w-full rounded-2xl border p-4 text-left transition ${
                    resolvedSessionId === session.id
                      ? "surface-hero border"
                      : "surface-instrument border hover:bg-accent/40"
                  }`}
                >
                  <p className="truncate font-medium">{session.title}</p>
                  <p className="mt-1 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    {session.messages.length} messages
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground" data-volatile="true">
                    {formatRelativeTime(session.updatedAt)}
                  </p>
                </button>
              ))
            ) : (
              <EmptyState title="No sessions yet" description="Create a new session to start testing a model." />
            )}
          </CardContent>
        </Card>

        <Card className="surface-panel">
          <CardHeader>
            <CardTitle className="text-lg">Model inventory</CardTitle>
            <CardDescription>Reachability, model choice, and backend routing.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {snapshot.models.map((model) => {
              const modelKey = getModelKey(model.target, model.id);
              const selected = currentModelKey === modelKey;
              return (
                <button
                  key={modelKey}
                  type="button"
                  onClick={() => selectModel(model.target, model.id)}
                  className={`w-full rounded-2xl border p-4 text-left transition ${
                    selected
                      ? "surface-hero border"
                      : "surface-instrument border hover:bg-accent/40"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <StatusDot tone={model.available ? "healthy" : "danger"} />
                        <p className="truncate font-medium">{model.id.replace(/^\/models\//, "")}</p>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{model.backend}</p>
                    </div>
                    {selected ? <Badge className="status-badge" data-tone="info">Active</Badge> : null}
                  </div>
                </button>
              );
            })}
          </CardContent>
        </Card>

        <Card className="surface-hero flex min-h-[42rem] flex-col overflow-hidden">
          <CardHeader className="border-b border-border/70">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle className="text-lg">Conversation</CardTitle>
                <CardDescription>
                  {selectedModel
                    ? `${selectedModel.id.replace(/^\/models\//, "")} on ${selectedModel.backend}`
                    : "Select a model to begin."}
                </CardDescription>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {activeSession ? (
                  <>
                    <Badge variant="outline" className="status-badge" data-tone="info" data-volatile="true">
                      {formatTimestamp(activeSession.updatedAt)}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigator.clipboard.writeText(activeSession.messages.map((message) => `${message.role.toUpperCase()}: ${message.content}`).join("\n\n"))}
                    >
                      <Copy className="mr-2 h-4 w-4" />
                      Copy
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setPendingSessionId(null);
                        setSearchValue("session", null);
                        setSessions((current) =>
                          current.filter((session) => session.id !== activeSession.id)
                        );
                      }}
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Remove
                    </Button>
                  </>
                ) : null}
              </div>
            </div>
          </CardHeader>

          <CardContent className="flex min-h-0 flex-1 flex-col overflow-hidden p-0">
            <ScrollArea className="flex-1 px-4 sm:px-6" ref={scrollRef}>
              <div className="space-y-4 py-4">
                {!activeSession || activeSession.messages.length === 0 ? (
                  <EmptyState
                    title={isCreatingSession ? "Ready for a new session" : "No conversation yet"}
                    description={
                      isCreatingSession
                        ? "You picked a new model. Send the first prompt to open a fresh session on that runtime."
                        : "Choose a model and send a prompt to start a persisted direct-chat session."
                    }
                  />
                ) : (
                  activeSession.messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`max-w-[88%] rounded-2xl px-4 py-3 sm:max-w-[78%] ${
                          message.role === "user"
                            ? "bg-primary text-primary-foreground"
                            : "surface-instrument border text-foreground"
                        }`}
                      >
                        <div className="mb-2 flex items-center justify-between gap-3 text-[11px] uppercase tracking-[0.2em] opacity-70">
                          <span>{message.role === "user" ? "Operator" : "Model"}</span>
                          <span data-volatile="true">{formatRelativeTime(message.createdAt)}</span>
                        </div>
                        {message.role === "assistant" ? (
                          <RichText content={message.content || (isStreaming ? "Streaming..." : "")} />
                        ) : (
                          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                        )}
                      </div>
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
                    className="surface-instrument rounded-full border px-3 py-1.5 text-xs text-muted-foreground transition hover:bg-accent/40 hover:text-foreground"
                    onClick={() => setInput(prompt)}
                  >
                    {prompt}
                  </button>
                ))}
                {promptHistory.slice(0, 3).map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    className="rounded-full border px-3 py-1.5 text-xs transition"
                    style={{
                      borderColor: "color-mix(in oklab, var(--accent-structural) 34%, transparent)",
                      background: "color-mix(in oklab, var(--accent-structural) 12%, transparent)",
                      color: "var(--accent-structural-strong)",
                    }}
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
                  placeholder={selectedModel ? `Message ${selectedModel.id.replace(/^\/models\//, "")}...` : "Select a model first"}
                  disabled={!selectedModel || isStreaming}
                  className="surface-instrument flex-1"
                  autoFocus
                />
                {isStreaming ? (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => abortRef.current?.abort()}
                  >
                    <Square className="mr-2 h-4 w-4" />
                    Stop
                  </Button>
                ) : null}
                <Button type="submit" disabled={!selectedModel || !input.trim() || isStreaming}>
                  <Send className="mr-2 h-4 w-4" />
                  Send
                </Button>
              </form>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
