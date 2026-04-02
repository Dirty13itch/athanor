"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, CircleDashed, RefreshCcw, Target, TimerReset } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { formatRelativeTime } from "@/lib/format";
import { requestJson, postJson } from "@/features/workforce/helpers";

type TodoStatus = "all" | "open" | "ready" | "blocked" | "delegated" | "waiting" | "done" | "cancelled" | "someday";

interface OperatorTodo {
  id: string;
  title: string;
  description: string;
  category: string;
  scope_type: string;
  scope_id: string;
  priority: number;
  status: Exclude<TodoStatus, "all">;
  energy_class: string;
  created_at: number;
  updated_at: number;
  completed_at: number;
}

interface OperatorSummary {
  todos?: {
    total?: number;
    by_status?: Record<string, number>;
  };
}

const STATUS_FILTERS: TodoStatus[] = ["open", "ready", "blocked", "waiting", "done", "someday", "all"];

export function TodosConsole() {
  const [status, setStatus] = useState<TodoStatus>("open");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const todosQuery = useQuery({
    queryKey: ["operator-todos", status],
    queryFn: async (): Promise<OperatorTodo[]> => {
      const query = status === "all" ? "" : `?status=${encodeURIComponent(status)}`;
      const data = await requestJson(`/api/operator/todos${query}`);
      return (data?.todos ?? data ?? []) as OperatorTodo[];
    },
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });

  const summaryQuery = useQuery({
    queryKey: ["operator-work-summary"],
    queryFn: async (): Promise<OperatorSummary> => {
      const data = await requestJson("/api/operator/summary");
      return (data ?? {}) as OperatorSummary;
    },
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });

  async function handleAction(action: string, run: () => Promise<void>) {
    setBusy(action);
    setFeedback(null);
    try {
      await run();
      await Promise.all([todosQuery.refetch(), summaryQuery.refetch()]);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Request failed.");
    } finally {
      setBusy(null);
    }
  }

  if (todosQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Operator Work" title="Todos" description="The operator todo list failed to load." attentionHref="/todos" />
        <ErrorPanel description={todosQuery.error instanceof Error ? todosQuery.error.message : "Failed to load operator todos."} />
      </div>
    );
  }

  const todos = todosQuery.data ?? [];
  const summary = summaryQuery.data?.todos;
  const byStatus = summary?.by_status ?? {};

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Operator Work"
        title="Todos"
        description="Finite operator work, distinct from the workforce task queue."
        attentionHref="/todos"
        actions={
          <Button variant="outline" onClick={() => void Promise.all([todosQuery.refetch(), summaryQuery.refetch()])} disabled={todosQuery.isFetching || summaryQuery.isFetching}>
            <RefreshCcw className={`mr-2 h-4 w-4 ${todosQuery.isFetching || summaryQuery.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Visible todos" value={`${todos.length}`} detail="Current filtered todo list." icon={<Target className="h-5 w-5" />} />
          <StatCard label="Ready" value={`${byStatus.ready ?? 0}`} detail={`${byStatus.blocked ?? 0} blocked items need follow-through.`} icon={<CheckCircle2 className="h-5 w-5" />} />
          <StatCard label="Open" value={`${byStatus.open ?? 0}`} detail={`${byStatus.waiting ?? 0} waiting on outside motion.`} icon={<CircleDashed className="h-5 w-5" />} />
          <StatCard label="Done" value={`${byStatus.done ?? 0}`} detail={`${byStatus.someday ?? 0} parked for later.`} icon={<TimerReset className="h-5 w-5" />} />
        </div>
      </PageHeader>

      {feedback ? <ErrorPanel title="Todo feedback" description={feedback} /> : null}

      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Capture operator todo</CardTitle>
          <CardDescription>This is Shaun work, not agent background work.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Review the next migration packet" />
          <textarea
            rows={3}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Optional detail or acceptance note."
            className="surface-instrument w-full rounded-xl border px-3 py-2 text-sm outline-none transition focus:border-primary"
          />
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={() =>
                void handleAction("create", async () => {
                  await postJson("/api/operator/todos", {
                    title: title.trim(),
                    description: description.trim(),
                    category: "ops",
                    scope_type: "global",
                    scope_id: "athanor",
                    priority: 3,
                    energy_class: "focused",
                  });
                  setTitle("");
                  setDescription("");
                })
              }
              disabled={busy === "create" || !title.trim()}
            >
              Add todo
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="text-lg">Todo lane</CardTitle>
          <CardDescription>Use status transitions to keep operator work explicit and finite.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {STATUS_FILTERS.map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setStatus(value)}
                className={`rounded-full border px-3 py-1 text-xs transition ${
                  status === value
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border/70 text-muted-foreground hover:bg-accent"
                }`}
              >
                {value}
              </button>
            ))}
          </div>

          {todos.length > 0 ? (
            <div className="space-y-3">
              {todos.map((todo) => (
                <div key={todo.id} className="surface-tile rounded-2xl border p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{todo.status}</Badge>
                    <Badge variant="secondary">{todo.category}</Badge>
                    <span className="text-xs text-muted-foreground">{`P${todo.priority} · ${todo.energy_class}`}</span>
                  </div>
                  <p className="mt-3 font-medium">{todo.title}</p>
                  {todo.description ? <p className="mt-2 text-sm text-muted-foreground">{todo.description}</p> : null}
                  <p className="mt-3 text-xs text-muted-foreground">{formatRelativeTime(new Date(todo.updated_at * 1000).toISOString())}</p>
                  {todo.status !== "done" && todo.status !== "cancelled" ? (
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void handleAction(`ready:${todo.id}`, () => postJson(`/api/operator/todos/${todo.id}/transition`, { status: "ready" }))}
                        disabled={busy === `ready:${todo.id}`}
                      >
                        Ready
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void handleAction(`blocked:${todo.id}`, () => postJson(`/api/operator/todos/${todo.id}/transition`, { status: "blocked" }))}
                        disabled={busy === `blocked:${todo.id}`}
                      >
                        Blocked
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => void handleAction(`done:${todo.id}`, () => postJson(`/api/operator/todos/${todo.id}/transition`, { status: "done" }))}
                        disabled={busy === `done:${todo.id}`}
                      >
                        Done
                      </Button>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No todos in this view" description="Capture one or change the current filter." className="py-10" />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
