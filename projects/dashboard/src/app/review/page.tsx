"use client";

import { useEffect, useEffectEvent, useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FeedbackButtons } from "@/components/gen-ui/feedback-buttons";

interface TaskStep {
  index: number;
  type: string;
  tool_name?: string;
  tool_input?: Record<string, unknown>;
  tool_output?: string;
  content?: string;
  timestamp: number;
}

interface Task {
  id: string;
  agent: string;
  prompt: string;
  priority: string;
  status: string;
  result: string;
  error: string;
  steps: TaskStep[];
  created_at: number;
  started_at: number;
  completed_at: number;
  metadata: Record<string, unknown>;
}

const FILE_TOOLS = new Set(["read_file", "write_file", "search_files", "list_directory", "run_command"]);

function formatTime(unix: number): string {
  if (!unix) return "";
  return new Date(unix * 1000).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  return `${(seconds / 60).toFixed(1)}min`;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
      className="px-2 py-0.5 text-[10px] border border-border rounded hover:bg-muted transition-colors"
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function isDiffContent(text: string): boolean {
  const lines = text.split("\n").slice(0, 10);
  return lines.some(
    (l) =>
      l.startsWith("diff --git") ||
      l.startsWith("--- a/") ||
      l.startsWith("+++ b/") ||
      l.startsWith("@@")
  );
}

function DiffBlock({ content }: { content: string }) {
  const lines = content.split("\n");
  return (
    <div className="rounded border border-border overflow-hidden text-xs font-mono">
      <div className="flex items-center justify-between bg-muted/50 px-3 py-1.5 border-b border-border">
        <span className="text-muted-foreground">diff</span>
        <CopyButton text={content} />
      </div>
      <pre className="p-0 m-0 overflow-x-auto max-h-96 overflow-y-auto">
        {lines.map((line, i) => {
          let cls = "px-3 py-0 leading-5 ";
          if (line.startsWith("+") && !line.startsWith("+++")) {
            cls += "bg-green-500/10 text-green-400";
          } else if (line.startsWith("-") && !line.startsWith("---")) {
            cls += "bg-red-500/10 text-red-400";
          } else if (line.startsWith("@@")) {
            cls += "bg-blue-500/10 text-blue-400";
          } else if (line.startsWith("diff ") || line.startsWith("---") || line.startsWith("+++")) {
            cls += "bg-muted/30 text-muted-foreground font-semibold";
          } else {
            cls += "text-muted-foreground";
          }
          return (
            <div key={i} className={cls}>
              {line || "\u00A0"}
            </div>
          );
        })}
      </pre>
    </div>
  );
}

function CodeBlock({ content, filename }: { content: string; filename?: string }) {
  const lines = content.split("\n");
  return (
    <div className="rounded border border-border overflow-hidden text-xs font-mono">
      <div className="flex items-center justify-between bg-muted/50 px-3 py-1.5 border-b border-border">
        <span className="text-muted-foreground">{filename || "output"}</span>
        <CopyButton text={content} />
      </div>
      <pre className="p-0 m-0 overflow-x-auto max-h-96 overflow-y-auto">
        {lines.map((line, i) => (
          <div key={i} className="flex">
            <span className="select-none text-muted-foreground/40 text-right w-8 pr-2 flex-shrink-0">
              {i + 1}
            </span>
            <span className="px-2 py-0 leading-5">{line || "\u00A0"}</span>
          </div>
        ))}
      </pre>
    </div>
  );
}

function StepDetail({ step }: { step: TaskStep }) {
  const toolName = step.tool_name || step.type;
  const input = step.tool_input || {};
  const output = step.tool_output || step.content || "";

  // Extract filename from tool input
  const filename =
    (input.path as string) || (input.file_path as string) || (input.filename as string) || undefined;

  // For write_file, show what was written
  const fileContent = (input.content as string) || "";

  // Parse tool_output — it comes as "content='...' name='...' tool_call_id='...'"
  let cleanOutput = output;
  const contentMatch = output.match(/^content='([\s\S]*?)'\s+name=/);
  if (contentMatch) {
    cleanOutput = contentMatch[1];
  }

  const isFileOp = FILE_TOOLS.has(toolName);
  const hasDiff = isDiffContent(cleanOutput);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="text-[10px]">
          {toolName}
        </Badge>
        {filename && (
          <span className="text-xs text-muted-foreground font-mono">{filename}</span>
        )}
      </div>

      {/* Tool input for file operations */}
      {toolName === "write_file" && fileContent.length > 0 && (
        <CodeBlock content={fileContent} filename={filename} />
      )}

      {toolName === "run_command" && typeof input.command === "string" && (
        <div className="text-xs font-mono bg-muted/30 rounded px-3 py-1.5 text-muted-foreground">
          $ {input.command}
        </div>
      )}

      {/* Tool output */}
      {cleanOutput && (
        hasDiff ? (
          <DiffBlock content={cleanOutput} />
        ) : isFileOp && cleanOutput.length > 100 ? (
          <CodeBlock content={cleanOutput} filename={filename} />
        ) : (
          <div className="text-xs bg-muted/30 rounded px-3 py-2 whitespace-pre-wrap max-h-48 overflow-y-auto text-muted-foreground">
            {cleanOutput}
          </div>
        )
      )}
    </div>
  );
}

export default function ReviewPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);
  const [agentFilter, setAgentFilter] = useState("coding-agent");

  const fetchTasks = useEffectEvent(async () => {
    try {
      const params = new URLSearchParams({ limit: "30" });
      if (agentFilter) params.set("agent", agentFilter);
      const res = await fetch(`/api/workforce/tasks?${params}`);
      if (res.ok) {
        const data = await res.json();
        // Sort by most recent first, prefer completed tasks with steps
        const sorted = (data.tasks || []).sort((a: Task, b: Task) => {
          // Prioritize tasks with file-related steps
          const aHasFiles = a.steps.some((s) => FILE_TOOLS.has(s.tool_name || ""));
          const bHasFiles = b.steps.some((s) => FILE_TOOLS.has(s.tool_name || ""));
          if (aHasFiles !== bHasFiles) return bHasFiles ? 1 : -1;
          return b.created_at - a.created_at;
        });
        setTasks(sorted);
      }
    } catch (e) {
      console.error("Failed to fetch tasks:", e);
    }
  });

  useEffect(() => {
    void fetchTasks();
    const id = setInterval(() => {
      void fetchTasks();
    }, 10000);
    return () => clearInterval(id);
  }, [agentFilter]);

  const hasFileSteps = (task: Task) =>
    task.steps.some((s) => FILE_TOOLS.has(s.tool_name || ""));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Code Review</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Layer 5 — review agent file operations and diffs
        </p>
      </div>

      {/* Filter */}
      <div className="flex gap-3 items-center">
        <select
          value={agentFilter}
          onChange={(e) => setAgentFilter(e.target.value)}
          className="px-3 py-1.5 bg-background border rounded-md text-sm"
        >
          <option value="">All Agents</option>
          <option value="coding-agent">coding-agent</option>
          <option value="general-assistant">general-assistant</option>
          <option value="research-agent">research-agent</option>
        </select>
        <span className="text-xs text-muted-foreground">
          {tasks.length} task{tasks.length !== 1 ? "s" : ""}
          {tasks.filter(hasFileSteps).length > 0 &&
            ` (${tasks.filter(hasFileSteps).length} with file ops)`}
        </span>
      </div>

      {/* Task List */}
      <div className="space-y-4">
        {tasks.length === 0 && (
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              No tasks found for this agent.
            </CardContent>
          </Card>
        )}

        {tasks.map((task) => {
          const isExpanded = expandedTask === task.id;
          const fileSteps = task.steps.filter((s) => FILE_TOOLS.has(s.tool_name || ""));
          const duration =
            task.completed_at && task.started_at
              ? task.completed_at - task.started_at
              : 0;

          return (
            <Card
              key={task.id}
              className="hover:border-primary/30 transition-colors"
            >
              <CardHeader
                className="cursor-pointer pb-2"
                onClick={() => setExpandedTask(isExpanded ? null : task.id)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge
                        className={
                          task.status === "completed"
                            ? "bg-green-500/20 text-green-400"
                            : task.status === "running"
                            ? "bg-blue-500/20 text-blue-400"
                            : task.status === "failed"
                            ? "bg-red-500/20 text-red-400"
                            : "bg-zinc-500/20 text-zinc-400"
                        }
                      >
                        {task.status}
                      </Badge>
                      <span className="text-xs font-mono text-muted-foreground">
                        {task.id}
                      </span>
                      {fileSteps.length > 0 && (
                        <Badge variant="outline" className="text-[10px]">
                          {fileSteps.length} file op{fileSteps.length !== 1 ? "s" : ""}
                        </Badge>
                      )}
                    </div>
                    <CardTitle className="text-sm font-normal mt-2 line-clamp-2">
                      {task.prompt}
                    </CardTitle>
                  </div>
                  <div className="text-right text-xs text-muted-foreground whitespace-nowrap">
                    <div>{formatTime(task.created_at)}</div>
                    {duration > 0 && <div>{formatDuration(duration)}</div>}
                  </div>
                </div>
              </CardHeader>

              {isExpanded && (
                <CardContent className="pt-0 space-y-4">
                  {/* Result */}
                  {task.result && (
                    <div>
                      <div className="text-xs font-medium text-muted-foreground mb-1.5">
                        Result
                      </div>
                      <div className="text-sm bg-muted/30 rounded p-3 whitespace-pre-wrap max-h-48 overflow-y-auto">
                        {task.result}
                      </div>
                      <FeedbackButtons
                        messageContent={`Task ${task.id}: ${task.result.substring(0, 300)}`}
                        agent={task.agent}
                      />
                    </div>
                  )}

                  {/* Error */}
                  {task.error && (
                    <div>
                      <div className="text-xs font-medium text-red-400 mb-1.5">
                        Error
                      </div>
                      <pre className="text-xs bg-red-500/10 rounded p-3 whitespace-pre-wrap">
                        {task.error}
                      </pre>
                    </div>
                  )}

                  {/* Steps with enhanced rendering */}
                  {task.steps.length > 0 && (
                    <div>
                      <div className="text-xs font-medium text-muted-foreground mb-2">
                        Execution Trace ({task.steps.length} step{task.steps.length !== 1 ? "s" : ""})
                      </div>
                      <div className="space-y-3 border-l-2 border-border pl-4">
                        {task.steps.map((step, i) => (
                          <div key={i} className="relative">
                            <div className="absolute -left-[calc(1rem+5px)] top-1 w-2 h-2 rounded-full bg-border" />
                            <div className="text-[10px] text-muted-foreground mb-1">
                              Step {step.index + 1}
                              {step.timestamp > 0 &&
                                ` — ${new Date(step.timestamp * 1000).toLocaleTimeString("en-US", { hour12: false })}`}
                            </div>
                            <StepDetail step={step} />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
