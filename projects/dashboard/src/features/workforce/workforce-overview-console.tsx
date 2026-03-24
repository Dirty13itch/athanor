"use client";

interface WorkforceOverviewConsoleProps {
  initialSnapshot: Record<string, unknown>;
}

export function WorkforceOverviewConsole({ initialSnapshot }: WorkforceOverviewConsoleProps) {
  const tasks = (initialSnapshot as any)?.tasks ?? [];
  const goals = (initialSnapshot as any)?.goals ?? [];
  const trust = (initialSnapshot as any)?.trust ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Workforce Overview</h1>
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-lg border p-4">
          <h2 className="text-lg font-semibold mb-2">Tasks</h2>
          <p className="text-3xl font-bold">{Array.isArray(tasks) ? tasks.length : 0}</p>
          <p className="text-muted-foreground text-sm">Active tasks</p>
        </div>
        <div className="rounded-lg border p-4">
          <h2 className="text-lg font-semibold mb-2">Goals</h2>
          <p className="text-3xl font-bold">{Array.isArray(goals) ? goals.length : 0}</p>
          <p className="text-muted-foreground text-sm">Strategic goals</p>
        </div>
        <div className="rounded-lg border p-4">
          <h2 className="text-lg font-semibold mb-2">Trust</h2>
          <p className="text-3xl font-bold">{Array.isArray(trust) ? trust.length : 0}</p>
          <p className="text-muted-foreground text-sm">Agent grades</p>
        </div>
      </div>
    </div>
  );
}
