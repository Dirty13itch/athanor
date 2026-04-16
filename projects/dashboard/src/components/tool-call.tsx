"use client";

import { getToolRenderer, parseGpuMetrics, parseServiceHealth, parseTaskStatus } from "@/lib/generative-ui";
import { GpuChart } from "@/components/gen-ui/gpu-chart";
import { ServiceGrid } from "@/components/gen-ui/service-grid";
import { TaskCard } from "@/components/gen-ui/task-card";

interface ToolCallProps {
  name: string;
  args: Record<string, unknown>;
  result?: string;
  isExpanded: boolean;
  onToggle: () => void;
}

function ToolResultRenderer({ name, result }: { name: string; result: string }) {
  const renderer = getToolRenderer(name);

  if (renderer === "gpu") {
    const metrics = parseGpuMetrics(result);
    if (metrics) return <GpuChart metrics={metrics} />;
  }

  if (renderer === "services") {
    const services = parseServiceHealth(result);
    if (services) return <ServiceGrid services={services} />;
  }

  if (renderer === "task") {
    const task = parseTaskStatus(result);
    if (task) return <TaskCard task={task} />;
  }

  // Fallback to plain text
  return (
    <pre className="text-xs bg-muted rounded p-2 overflow-x-auto max-h-48 whitespace-pre-wrap">
      {result}
    </pre>
  );
}

export function ToolCallCard({ name, args, result, isExpanded, onToggle }: ToolCallProps) {
  const isRunning = result === undefined;
  const displayName = name.replace(/_/g, " ");

  return (
    <div
      className="my-2 ml-4 border-l-2 border-primary bg-card rounded-r-md px-3 py-2 cursor-pointer select-none"
      onClick={onToggle}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onToggle()}
    >
      <div className="flex items-center gap-2">
        {isRunning ? (
          <span className="inline-block h-2 w-2 rounded-full bg-yellow-500 animate-pulse" />
        ) : (
          <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
        )}
        <span className="text-xs font-medium text-foreground">{displayName}</span>
        {isRunning ? (
          <span className="text-xs text-muted-foreground">Working...</span>
        ) : (
          <span className="text-xs text-muted-foreground">
            {isExpanded ? "▾ collapse" : "▸ expand"}
          </span>
        )}
      </div>
      {!isRunning && !isExpanded && result && (
        <p className="mt-1 text-xs text-muted-foreground truncate max-w-md">
          {result.split("\n")[0]}
        </p>
      )}
      {isExpanded && (
        <div className="mt-2 space-y-2" onClick={(e) => e.stopPropagation()}>
          {Object.keys(args).length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Args</p>
              <pre className="text-xs bg-muted rounded p-2 overflow-x-auto max-h-24">
                {JSON.stringify(args, null, 2)}
              </pre>
            </div>
          )}
          {result && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Result</p>
              <ToolResultRenderer name={name} result={result} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
