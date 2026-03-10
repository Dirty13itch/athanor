"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface OutputFile {
  path: string;
  size_bytes: number;
  modified: number;
}

interface FileContent {
  path: string;
  content: string;
  size_bytes: number;
  is_text: boolean;
}

function timeAgo(ts: number): string {
  const ms = Date.now() - ts * 1000;
  const min = Math.floor(ms / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  return `${Math.floor(hr / 24)}d ago`;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fileIcon(path: string): string {
  if (path.endsWith(".json")) return "{}";
  if (path.endsWith(".md")) return "#";
  if (path.endsWith(".py")) return "py";
  if (path.endsWith(".tsx") || path.endsWith(".ts")) return "ts";
  if (path.endsWith(".js") || path.endsWith(".jsx")) return "js";
  if (path.endsWith(".png") || path.endsWith(".jpg") || path.endsWith(".webp")) return "img";
  return "f";
}

function fileCategory(path: string): string {
  if (path.includes("characters")) return "character";
  if (path.includes("scenes")) return "scene";
  if (path.includes("components")) return "component";
  if (path.includes("test")) return "test";
  if (path.includes("research")) return "research";
  return "output";
}

const CATEGORY_COLORS: Record<string, string> = {
  character: "bg-pink-500/20 text-pink-400",
  scene: "bg-purple-500/20 text-purple-400",
  component: "bg-blue-500/20 text-blue-400",
  test: "bg-green-500/20 text-green-400",
  research: "bg-cyan-500/20 text-cyan-400",
  output: "bg-zinc-500/20 text-zinc-400",
};

export default function OutputsPage() {
  const [files, setFiles] = useState<OutputFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState<FileContent | null>(null);
  const [loadingContent, setLoadingContent] = useState(false);
  const [feedbackSent, setFeedbackSent] = useState<Record<string, string>>({});

  const fetchFiles = useCallback(async () => {
    try {
      const res = await fetch("/api/outputs", {
        signal: AbortSignal.timeout(5000),
      });
      if (res.ok) {
        const data = await res.json();
        setFiles(data.outputs ?? []);
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFiles();
    const id = setInterval(fetchFiles, 30000);
    return () => clearInterval(id);
  }, [fetchFiles]);

  async function loadFile(path: string) {
    setLoadingContent(true);
    try {
      const encodedPath = path.split("/").map(encodeURIComponent).join("/");
      const res = await fetch(`/api/outputs/${encodedPath}`, { signal: AbortSignal.timeout(5000) });
      if (res.ok) {
        setSelectedFile(await res.json());
      }
    } catch {
      // silent
    } finally {
      setLoadingContent(false);
    }
  }

  async function sendFeedback(path: string, type: "positive" | "negative") {
    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          feedback_type: type,
          message_content: `Agent output: ${path}`,
          agent: "system",
        }),
        signal: AbortSignal.timeout(5000),
      });
      setFeedbackSent((prev) => ({ ...prev, [path]: type }));
    } catch {
      // silent
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight md:text-2xl">
          Agent Outputs
        </h1>
        <p className="text-xs text-muted-foreground md:text-sm">
          Files produced by autonomous agent tasks
        </p>
      </div>

      {loading ? (
        <Card>
          <CardContent className="py-4">
            <div className="h-4 w-40 animate-pulse rounded bg-muted" />
          </CardContent>
        </Card>
      ) : files.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-sm text-muted-foreground">
              No outputs yet. Agents write to /output when executing tasks.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {/* File list */}
          <div className="space-y-2">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              Files ({files.length})
            </h2>
            {files.map((file) => {
              const category = fileCategory(file.path);
              const isSelected = selectedFile?.path === file.path;
              return (
                <button
                  key={file.path}
                  onClick={() => loadFile(file.path)}
                  className={`w-full text-left rounded-lg border p-3 transition-colors hover:bg-accent/50 ${
                    isSelected
                      ? "border-primary bg-accent/30"
                      : "border-border"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded bg-muted text-[10px] font-mono font-bold">
                      {fileIcon(file.path)}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium truncate">
                        {file.path.split("/").pop()}
                      </p>
                      <p className="text-[10px] text-muted-foreground font-mono truncate">
                        {file.path}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1 shrink-0">
                      <Badge
                        className={`text-[10px] px-1.5 py-0 ${CATEGORY_COLORS[category] ?? CATEGORY_COLORS.output}`}
                      >
                        {category}
                      </Badge>
                      <span className="text-[10px] text-muted-foreground">
                        {formatSize(file.size_bytes)} · {timeAgo(file.modified)}
                      </span>
                    </div>
                  </div>
                  {/* Feedback */}
                  <div className="flex items-center gap-2 mt-2">
                    {feedbackSent[file.path] ? (
                      <span className="text-[10px] text-green-400">
                        Feedback sent
                      </span>
                    ) : (
                      <>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            sendFeedback(file.path, "positive");
                          }}
                          className="rounded px-2 py-0.5 text-[10px] border border-border hover:bg-green-500/10 hover:text-green-400 transition-colors"
                        >
                          Good
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            sendFeedback(file.path, "negative");
                          }}
                          className="rounded px-2 py-0.5 text-[10px] border border-border hover:bg-red-500/10 hover:text-red-400 transition-colors"
                        >
                          Redo
                        </button>
                      </>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {/* File preview */}
          <div className="space-y-2">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              Preview
            </h2>
            <Card className="min-h-[400px]">
              {loadingContent ? (
                <CardContent className="py-8 text-center">
                  <p className="text-sm text-muted-foreground">Loading...</p>
                </CardContent>
              ) : selectedFile ? (
                <>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-mono">
                      {selectedFile.path.split("/").pop()}
                    </CardTitle>
                    <p className="text-[10px] text-muted-foreground">
                      {formatSize(selectedFile.size_bytes)}
                    </p>
                  </CardHeader>
                  <CardContent>
                    {selectedFile.is_text ? (
                      <pre className="whitespace-pre-wrap break-words text-xs font-mono text-muted-foreground leading-relaxed max-h-[70vh] overflow-y-auto">
                        {selectedFile.content}
                      </pre>
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        Binary file — preview not available
                      </p>
                    )}
                  </CardContent>
                </>
              ) : (
                <CardContent className="py-8 text-center">
                  <p className="text-sm text-muted-foreground">
                    Select a file to preview its contents
                  </p>
                </CardContent>
              )}
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
