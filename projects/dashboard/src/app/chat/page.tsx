"use client";

import { Suspense, useState, useRef, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ModelEntry {
  id: string;
  backend: string;
  backendUrl: string;
}

const AGENT_BACKEND_NAME = "Agents";

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
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [models, setModels] = useState<ModelEntry[]>([]);
  const [selectedModel, setSelectedModel] = useState<ModelEntry | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const searchParams = useSearchParams();

  useEffect(() => {
    fetch("/api/models")
      .then((r) => r.json())
      .then((data) => {
        const m: ModelEntry[] = data.models ?? [];
        setModels(m);

        // Pre-select agent if ?agent= query param is set
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

  useEffect(scrollToBottom, [messages, scrollToBottom]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isStreaming || !selectedModel) return;

    const userMessage: Message = { role: "user", content: input.trim() };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput("");
    setIsStreaming(true);
    setError(null);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: newMessages,
          model: selectedModel.id,
          backendUrl: selectedModel.backendUrl,
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Chat request failed (${res.status}): ${text}`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response stream");

      const decoder = new TextDecoder();
      let assistantContent = "";
      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6).trim();
          if (data === "[DONE]") break;

          try {
            const parsed = JSON.parse(data);
            const delta = parsed.choices?.[0]?.delta?.content;
            if (delta) {
              assistantContent += delta;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: "assistant",
                  content: assistantContent,
                };
                return updated;
              });
            }
          } catch {
            // Skip malformed SSE chunks
          }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chat failed");
    } finally {
      setIsStreaming(false);
    }
  }

  // Group models by type: inference vs agents
  const inferenceModels = models.filter((m) => m.backend !== AGENT_BACKEND_NAME);
  const agentModels = models.filter((m) => m.backend === AGENT_BACKEND_NAME);
  const isAgent = selectedModel?.backend === AGENT_BACKEND_NAME;

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
    <div className="flex h-[calc(100vh-3rem)] flex-col space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Chat</h1>
          <p className="text-muted-foreground">
            {selectedModel
              ? isAgent
                ? `Agent: ${displayModelName(selectedModel)}`
                : `Model: ${displayModelName(selectedModel)}`
              : "Loading models..."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isAgent && (
            <Badge variant="outline" className="text-xs">Agent</Badge>
          )}
          {models.length > 0 && (
            <select
              value={selectedModel ? modelKey(selectedModel) : ""}
              onChange={(e) => {
                const [url, ...idParts] = e.target.value.split("::");
                const id = idParts.join("::");
                const m = models.find((m) => m.backendUrl === url && m.id === id);
                if (m) {
                  setSelectedModel(m);
                  setMessages([]);
                  setError(null);
                }
              }}
              className="rounded-md border border-border bg-background px-3 py-1.5 text-sm"
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
              {messages.length === 0 && (
                <p className="text-center text-sm text-muted-foreground py-8">
                  {isAgent
                    ? `Send a message to ${displayModelName(selectedModel!)}`
                    : selectedModel
                      ? `Send a message to start chatting with ${displayModelName(selectedModel)}`
                      : "Select a model or agent to begin"}
                </p>
              )}
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-2 text-sm whitespace-pre-wrap ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-foreground"
                    }`}
                  >
                    {msg.content}
                    {isStreaming && i === messages.length - 1 && msg.role === "assistant" && (
                      <span className="inline-block w-1.5 h-4 ml-0.5 bg-foreground animate-pulse" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>

          {error && (
            <div className="mx-6 mb-2 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex gap-2 border-t border-border p-4">
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
