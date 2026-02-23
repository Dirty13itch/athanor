"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

// --- Types ---

interface AgentInfo {
  id: string;
  name: string;
  description: string;
  tools: string[];
  status: "ready" | "unavailable";
  icon: string;
}

interface ToolCall {
  id: string;
  name: string;
  args?: Record<string, unknown>;
  output?: string;
  duration_ms?: number;
  status: "running" | "done" | "error";
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCall[];
}

// --- Icons ---

function TerminalIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <polyline points="4 17 10 11 4 5" />
      <line x1="12" x2="20" y1="19" y2="19" />
    </svg>
  );
}

function FilmIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <rect width="18" height="18" x="3" y="3" rx="2" />
      <path d="M7 3v18" /><path d="M17 3v18" /><path d="M3 7h4" /><path d="M3 11h4" /><path d="M3 15h4" /><path d="M17 7h4" /><path d="M17 11h4" /><path d="M17 15h4" />
    </svg>
  );
}

function HomeIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8" />
      <path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
    </svg>
  );
}

function WrenchIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  );
}

function ChevronDownIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

function SpinnerIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={cn("animate-spin", className)}>
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

const ICON_MAP: Record<string, React.FC<{ className?: string }>> = {
  terminal: TerminalIcon,
  film: FilmIcon,
  home: HomeIcon,
};

// --- Tool Call Card ---

function ToolCallCard({ tool }: { tool: ToolCall }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="rounded-md border border-border/50 bg-secondary/30 text-sm cursor-pointer transition-colors hover:bg-secondary/50"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center gap-2 px-3 py-2">
        {tool.status === "running" ? (
          <SpinnerIcon className="h-3.5 w-3.5 text-primary shrink-0" />
        ) : (
          <WrenchIcon className="h-3.5 w-3.5 text-primary shrink-0" />
        )}
        <span className="font-mono text-xs text-foreground/80">{tool.name}</span>
        {tool.args && Object.keys(tool.args).length > 0 && (
          <span className="font-mono text-xs text-muted-foreground truncate">
            {Object.entries(tool.args)
              .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
              .join(", ")}
          </span>
        )}
        <div className="ml-auto flex items-center gap-2">
          {tool.duration_ms !== undefined && (
            <span className="text-xs text-muted-foreground tabular-nums">{tool.duration_ms}ms</span>
          )}
          {tool.status === "done" && (
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0 bg-emerald-500/10 text-emerald-400 border-0">
              ok
            </Badge>
          )}
          {tool.status === "error" && (
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0 bg-destructive/10 text-destructive border-0">
              err
            </Badge>
          )}
          <ChevronDownIcon
            className={cn(
              "h-3.5 w-3.5 text-muted-foreground transition-transform",
              expanded && "rotate-180"
            )}
          />
        </div>
      </div>
      {expanded && tool.output && (
        <div className="border-t border-border/30 px-3 py-2">
          <pre className="text-xs text-muted-foreground whitespace-pre-wrap font-mono leading-relaxed max-h-60 overflow-y-auto">
            {tool.output}
          </pre>
        </div>
      )}
    </div>
  );
}

// --- Agent Card ---

function AgentCard({
  agent,
  selected,
  onClick,
}: {
  agent: AgentInfo;
  selected: boolean;
  onClick: () => void;
}) {
  const IconComponent = ICON_MAP[agent.icon] ?? TerminalIcon;
  const isReady = agent.status === "ready";

  return (
    <Card
      className={cn(
        "cursor-pointer transition-all hover:bg-accent/50",
        selected && "ring-1 ring-primary bg-accent/30",
        !isReady && "opacity-50"
      )}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className={cn(
            "rounded-md p-2",
            selected ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground"
          )}>
            <IconComponent className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold truncate">{agent.name}</h3>
              <span
                className={cn(
                  "h-2 w-2 rounded-full shrink-0",
                  isReady ? "bg-emerald-500" : "bg-muted-foreground/40"
                )}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
              {agent.description}
            </p>
            <div className="mt-2">
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                {agent.tools.length} tools
              </Badge>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// --- Main Page ---

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<AgentInfo | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Fetch agents
  useEffect(() => {
    fetch("/api/agents")
      .then((r) => r.json())
      .then((data) => {
        const a: AgentInfo[] = data.agents ?? [];
        setAgents(a);
      })
      .catch(() => {});
  }, []);

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, []);

  useEffect(scrollToBottom, [messages, scrollToBottom]);

  function selectAgent(agent: AgentInfo) {
    if (agent.status !== "ready") return;
    setSelectedAgent(agent);
    setMessages([]);
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isStreaming || !selectedAgent) return;

    const userMessage: ChatMessage = { role: "user", content: input.trim() };
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
          messages: newMessages.map((m) => ({
            role: m.role,
            content: m.content,
          })),
          model: selectedAgent.id,
          backendUrl: "http://192.168.1.244:9000",
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Request failed (${res.status}): ${text}`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response stream");

      const decoder = new TextDecoder();
      let assistantContent = "";
      const toolCalls: ToolCall[] = [];

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "", toolCalls: [] },
      ]);

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

            // Handle tool events (future — when backend streams them)
            if (parsed.type === "tool_start") {
              toolCalls.push({
                id: `tool-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                name: parsed.name,
                args: parsed.args,
                status: "running",
              });
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: "assistant",
                  content: assistantContent,
                  toolCalls: [...toolCalls],
                };
                return updated;
              });
              continue;
            }

            if (parsed.type === "tool_end") {
              const tc = toolCalls.find(
                (t) => t.name === parsed.name && t.status === "running"
              );
              if (tc) {
                tc.status = parsed.error ? "error" : "done";
                tc.output = parsed.output;
                tc.duration_ms = parsed.duration_ms;
              }
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: "assistant",
                  content: assistantContent,
                  toolCalls: [...toolCalls],
                };
                return updated;
              });
              continue;
            }

            // Standard OpenAI chunk
            const delta = parsed.choices?.[0]?.delta?.content;
            if (delta) {
              assistantContent += delta;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: "assistant",
                  content: assistantContent,
                  toolCalls: [...toolCalls],
                };
                return updated;
              });
            }
          } catch {
            // skip malformed chunks
          }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setIsStreaming(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-3rem)] flex-col gap-4">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Agents</h1>
        <p className="text-muted-foreground text-sm">
          {selectedAgent
            ? `Talking to ${selectedAgent.name}`
            : "Select an agent to start a conversation"}
        </p>
      </div>

      {/* Agent Hub Cards */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {agents.map((agent) => (
          <AgentCard
            key={agent.id}
            agent={agent}
            selected={selectedAgent?.id === agent.id}
            onClick={() => selectAgent(agent)}
          />
        ))}
        {agents.length === 0 && (
          <Card className="col-span-full">
            <CardContent className="p-8 text-center text-muted-foreground text-sm">
              Loading agents...
            </CardContent>
          </Card>
        )}
      </div>

      {/* Chat Area */}
      {selectedAgent && (
        <Card className="flex flex-1 flex-col overflow-hidden">
          <CardHeader className="pb-2 border-b border-border/50">
            <div className="flex items-center gap-2">
              <CardTitle className="text-sm font-medium">
                Conversation
              </CardTitle>
              {selectedAgent.tools.length > 0 && (
                <span className="text-xs text-muted-foreground">
                  {selectedAgent.tools.length} tools available
                </span>
              )}
            </div>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col overflow-hidden p-0">
            <ScrollArea className="flex-1 px-6" ref={scrollRef}>
              <div className="space-y-4 py-4">
                {messages.length === 0 && (
                  <div className="py-12 text-center">
                    <p className="text-sm text-muted-foreground">
                      Send a message to start chatting with{" "}
                      {selectedAgent.name}.
                    </p>
                    <div className="mt-4 flex flex-wrap justify-center gap-2">
                      {selectedAgent.id === "general-assistant" && (
                        <>
                          <SuggestionChip
                            text="How are the GPUs doing?"
                            onClick={(t) => setInput(t)}
                          />
                          <SuggestionChip
                            text="Check service health"
                            onClick={(t) => setInput(t)}
                          />
                          <SuggestionChip
                            text="What models are loaded?"
                            onClick={(t) => setInput(t)}
                          />
                        </>
                      )}
                      {selectedAgent.id === "media-agent" && (
                        <>
                          <SuggestionChip
                            text="What's playing on Plex?"
                            onClick={(t) => setInput(t)}
                          />
                          <SuggestionChip
                            text="Search for Severance"
                            onClick={(t) => setInput(t)}
                          />
                          <SuggestionChip
                            text="Show my watch history"
                            onClick={(t) => setInput(t)}
                          />
                        </>
                      )}
                      {selectedAgent.id === "home-agent" && (
                        <>
                          <SuggestionChip
                            text="What lights are on?"
                            onClick={(t) => setInput(t)}
                          />
                          <SuggestionChip
                            text="Set living room to 75%"
                            onClick={(t) => setInput(t)}
                          />
                        </>
                      )}
                    </div>
                  </div>
                )}

                {messages.map((msg, i) => (
                  <div key={i}>
                    {msg.role === "user" ? (
                      <div className="flex justify-end">
                        <div className="max-w-[80%] rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm whitespace-pre-wrap">
                          {msg.content}
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-col gap-2 max-w-[85%]">
                        {/* Tool calls */}
                        {msg.toolCalls?.map((tool) => (
                          <ToolCallCard key={tool.id} tool={tool} />
                        ))}
                        {/* Assistant text */}
                        {msg.content && (
                          <div className="rounded-lg bg-muted text-foreground px-4 py-2 text-sm whitespace-pre-wrap">
                            {msg.content}
                            {isStreaming &&
                              i === messages.length - 1 && (
                                <span className="inline-block w-1.5 h-4 ml-0.5 bg-foreground animate-pulse" />
                              )}
                          </div>
                        )}
                        {/* Streaming with no content yet */}
                        {!msg.content &&
                          isStreaming &&
                          i === messages.length - 1 &&
                          (!msg.toolCalls || msg.toolCalls.length === 0) && (
                            <div className="rounded-lg bg-muted text-foreground px-4 py-2 text-sm">
                              <span className="inline-block w-1.5 h-4 bg-foreground animate-pulse" />
                            </div>
                          )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>

            {error && (
              <div className="mx-6 mb-2 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            )}

            <form
              onSubmit={handleSubmit}
              className="flex gap-2 border-t border-border p-4"
            >
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={`Message ${selectedAgent.name}...`}
                disabled={isStreaming}
                className="flex-1"
                autoFocus
              />
              <Button
                type="submit"
                disabled={isStreaming || !input.trim()}
              >
                {isStreaming ? "..." : "Send"}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Empty state when no agent selected */}
      {!selectedAgent && agents.length > 0 && (
        <Card className="flex flex-1 items-center justify-center">
          <CardContent className="text-center text-muted-foreground text-sm py-16">
            <WrenchIcon className="h-8 w-8 mx-auto mb-3 opacity-30" />
            <p>Select an agent above to begin</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// --- Suggestion Chip ---

function SuggestionChip({
  text,
  onClick,
}: {
  text: string;
  onClick: (text: string) => void;
}) {
  return (
    <button
      className="rounded-full border border-border/50 bg-secondary/30 px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
      onClick={() => onClick(text)}
      type="button"
    >
      {text}
    </button>
  );
}
