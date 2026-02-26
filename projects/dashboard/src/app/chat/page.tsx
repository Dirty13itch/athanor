"use client";

import { Suspense, useState, useRef, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ToolCallCard } from "@/components/tool-call";
import { MessageRenderer } from "@/components/gen-ui/message-renderer";
import { FeedbackButtons } from "@/components/gen-ui/feedback-buttons";
import { VoiceInput } from "@/components/voice-input";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ToolCall {
  runId: string;
  name: string;
  args: Record<string, unknown>;
  result?: string;
  status: "running" | "complete";
}

type ChatItem =
  | { type: "message"; role: "user" | "assistant"; content: string }
  | { type: "tool_call"; data: ToolCall };

interface ModelEntry {
  id: string;
  backend: string;
  backendUrl: string;
}

const AGENT_BACKEND_NAME = "Agents";

const AGENT_SUGGESTIONS: Record<string, string[]> = {
  "general-assistant": [
    "Check all services",
    "Show GPU metrics",
    "What models are loaded?",
    "How much storage is available?",
  ],
  "media-agent": [
    "What's playing on Plex?",
    "Show download queue",
    "Search for a new TV show",
    "What's coming up this week?",
  ],
};

export default function ChatPage() {
  return (
    <Suspense fallback={<ChatLoading />}>
      <ChatContent />
    </Suspense>
  );
}

function ChatLoading() {
  return (
    <div className="flex h-[calc(100vh-3rem)] items-center justify-center">
      <p className="text-sm text-muted-foreground">Loading chat...</p>
    </div>
  );
}

function ChatContent() {
  const [chatItems, setChatItems] = useState<ChatItem[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [models, setModels] = useState<ModelEntry[]>([]);
  const [selectedModel, setSelectedModel] = useState<ModelEntry | null>(null);
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);
  const searchParams = useSearchParams();

  useEffect(() => {
    fetch("/api/models")
      .then((r) => r.json())
      .then((data) => {
        const m: ModelEntry[] = data.models ?? [];
        setModels(m);

        const agentParam = searchParams.get("agent");
        if (agentParam) {
          const agentModel = m.find(
            (model) => model.id === agentParam && model.backend === AGENT_BACKEND_NAME
          );
          if (agentModel) {
            setSelectedModel(agentModel);
            return;
          }
        }
        if (m.length > 0) setSelectedModel(m[0]);
      })
      .catch(() => {});
  }, [searchParams]);

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, []);

  useEffect(scrollToBottom, [chatItems, scrollToBottom]);

  function toggleTool(runId: string) {
    setExpandedTools((prev) => {
      const next = new Set(prev);
      if (next.has(runId)) next.delete(runId);
      else next.add(runId);
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isStreaming || !selectedModel) return;
    sendMessage(input.trim());
  }

  function handleVoiceTranscript(text: string) {
    sendMessage(text);
  }

  async function sendMessage(text: string) {
    const userItem: ChatItem = { type: "message", role: "user", content: text };

    // Build messages array from existing chat items (messages only)
    const allMessages: Message[] = [];
    for (const item of chatItems) {
      if (item.type === "message") {
        allMessages.push({ role: item.role, content: item.content });
      }
    }
    allMessages.push({ role: "user", content: text });

    setChatItems((prev) => [...prev, userItem]);
    setInput("");
    setIsStreaming(true);
    setError(null);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: allMessages,
          model: selectedModel!.id,
          backendUrl: selectedModel!.backendUrl,
        }),
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Chat request failed (${res.status}): ${errText}`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response stream");

      const decoder = new TextDecoder();
      let assistantContent = "";
      let hasAssistantMsg = false;
      let buffer = "";
      let currentEventType = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          if (trimmed.startsWith("event: ")) {
            currentEventType = trimmed.slice(7).trim();
            continue;
          }

          if (!trimmed.startsWith("data: ")) continue;
          const data = trimmed.slice(6).trim();
          if (data === "[DONE]") break;

          try {
            if (currentEventType === "tool_start") {
              const parsed = JSON.parse(data);
              const toolCall: ToolCall = {
                runId: parsed.run_id ?? crypto.randomUUID(),
                name: parsed.name ?? "unknown",
                args: parsed.args ?? {},
                status: "running",
              };
              setChatItems((prev) => [...prev, { type: "tool_call", data: toolCall }]);
              currentEventType = "";
              continue;
            }

            if (currentEventType === "tool_end") {
              const parsed = JSON.parse(data);
              const runId = parsed.run_id ?? "";
              setChatItems((prev) =>
                prev.map((item) => {
                  if (item.type === "tool_call" && item.data.runId === runId) {
                    return {
                      ...item,
                      data: { ...item.data, result: parsed.result, status: "complete" as const },
                    };
                  }
                  return item;
                })
              );
              currentEventType = "";
              continue;
            }

            const parsed = JSON.parse(data);
            const delta = parsed.choices?.[0]?.delta?.content;
            if (delta) {
              assistantContent += delta;
              if (!hasAssistantMsg) {
                hasAssistantMsg = true;
                setChatItems((prev) => [
                  ...prev,
                  { type: "message", role: "assistant", content: assistantContent },
                ]);
              } else {
                setChatItems((prev) => {
                  const updated = [...prev];
                  for (let i = updated.length - 1; i >= 0; i--) {
                    const it = updated[i];
                    if (it.type === "message" && it.role === "assistant") {
                      updated[i] = { type: "message", role: "assistant", content: assistantContent };
                      break;
                    }
                  }
                  return updated;
                });
              }
            }
            currentEventType = "";
          } catch {
            currentEventType = "";
          }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chat failed");
    } finally {
      setIsStreaming(false);
    }
  }

  const inferenceModels = models.filter((m) => m.backend !== AGENT_BACKEND_NAME);
  const agentModels = models.filter((m) => m.backend === AGENT_BACKEND_NAME);
  const isAgent = selectedModel?.backend === AGENT_BACKEND_NAME;
  const suggestions = isAgent ? AGENT_SUGGESTIONS[selectedModel!.id] ?? [] : [];

  function displayModelName(m: ModelEntry): string {
    if (m.backend === AGENT_BACKEND_NAME) {
      return m.id.split("-").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
    }
    const short = m.id.replace(/^\/models\//, "");
    return `${short} (${m.backend})`;
  }

  function modelKey(m: ModelEntry): string {
    return `${m.backendUrl}::${m.id}`;
  }

  return (
    <div className="flex h-[calc(100vh-5rem)] flex-col space-y-3 md:h-[calc(100vh-3rem)] md:space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <h1 className="text-xl font-bold tracking-tight md:text-2xl">Chat</h1>
          <p className="truncate text-xs text-muted-foreground md:text-sm">
            {selectedModel
              ? isAgent
                ? `Agent: ${displayModelName(selectedModel)}`
                : `Model: ${displayModelName(selectedModel)}`
              : "Loading models..."}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {isAgent && <Badge variant="outline" className="hidden text-xs sm:inline-flex">Agent</Badge>}
          {models.length > 0 && (
            <select
              value={selectedModel ? modelKey(selectedModel) : ""}
              onChange={(e) => {
                const [url, ...idParts] = e.target.value.split("::");
                const id = idParts.join("::");
                const m = models.find((m) => m.backendUrl === url && m.id === id);
                if (m) {
                  setSelectedModel(m);
                  setChatItems([]);
                  setError(null);
                  setExpandedTools(new Set());
                }
              }}
              className="max-w-[160px] rounded-md border border-border bg-background px-2 py-1.5 text-xs md:max-w-none md:px-3 md:text-sm"
              disabled={isStreaming}
            >
              {inferenceModels.length > 0 && (
                <optgroup label="Inference">
                  {inferenceModels.map((m) => (
                    <option key={modelKey(m)} value={modelKey(m)}>
                      {displayModelName(m)}
                    </option>
                  ))}
                </optgroup>
              )}
              {agentModels.length > 0 && (
                <optgroup label="Agents">
                  {agentModels.map((m) => (
                    <option key={modelKey(m)} value={modelKey(m)}>
                      {displayModelName(m)}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
          )}
        </div>
      </div>

      <Card className="flex flex-1 flex-col overflow-hidden">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Conversation</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col overflow-hidden p-0">
          <ScrollArea className="flex-1 px-6" ref={scrollRef}>
            <div className="space-y-4 py-4">
              {chatItems.length === 0 && (
                <div className="py-8 text-center space-y-4">
                  <p className="text-sm text-muted-foreground">
                    {isAgent
                      ? `Send a message to ${displayModelName(selectedModel!)}`
                      : selectedModel
                        ? `Send a message to start chatting with ${displayModelName(selectedModel)}`
                        : "Select a model or agent to begin"}
                  </p>
                  {suggestions.length > 0 && (
                    <div className="flex flex-wrap justify-center gap-2">
                      {suggestions.map((s) => (
                        <button
                          key={s}
                          onClick={() => sendMessage(s)}
                          disabled={isStreaming}
                          className="rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {chatItems.map((item, i) => {
                if (item.type === "tool_call") {
                  return (
                    <ToolCallCard
                      key={`tool-${item.data.runId}`}
                      name={item.data.name}
                      args={item.data.args}
                      result={item.data.result}
                      isExpanded={expandedTools.has(item.data.runId)}
                      onToggle={() => toggleTool(item.data.runId)}
                    />
                  );
                }
                const isLastAssistant = isStreaming && i === chatItems.length - 1 && item.role === "assistant";
                return (
                  <div
                    key={i}
                    className={`flex ${item.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div className={item.role === "user" ? "max-w-[90%] md:max-w-[80%]" : "max-w-[90%] md:max-w-[80%]"}>
                      <div
                        className={`rounded-lg px-3 py-2 text-sm whitespace-pre-wrap md:px-4 ${
                          item.role === "user"
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted text-foreground"
                        }`}
                      >
                        <MessageRenderer content={item.content} role={item.role} />
                        {isLastAssistant && (
                          <span className="inline-block w-1.5 h-4 ml-0.5 bg-foreground animate-pulse" />
                        )}
                      </div>
                      {item.role === "assistant" && !isLastAssistant && (
                        <FeedbackButtons
                          messageContent={item.content}
                          agent={isAgent ? selectedModel?.id : undefined}
                        />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </ScrollArea>

          {error && (
            <div className="mx-6 mb-2 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex gap-2 border-t border-border p-4">
            <VoiceInput onTranscript={handleVoiceTranscript} disabled={isStreaming} />
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={isAgent ? `Ask ${displayModelName(selectedModel!)}...` : "Type a message..."}
              disabled={isStreaming}
              className="flex-1"
              autoFocus
            />
            <Button type="submit" disabled={isStreaming || !input.trim() || !selectedModel}>
              {isStreaming ? "..." : "Send"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
