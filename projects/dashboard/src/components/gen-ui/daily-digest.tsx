"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface DigestData {
  tasksCompleted: number;
  tasksFailed: number;
  tasksRunning: number;
  agentsOnline: number;
  pendingApprovals: number;
}

export function DailyDigest() {
  const [data, setData] = useState<DigestData | null>(null);

  useEffect(() => {
    let mounted = true;

    async function fetchDigest() {
      const digest: DigestData = {
        tasksCompleted: 0,
        tasksFailed: 0,
        tasksRunning: 0,
        agentsOnline: 0,
        pendingApprovals: 0,
      };

      try {
        const [statsRes, notifRes] = await Promise.all([
          fetch("/api/agents/proxy?path=/v1/tasks/stats", { signal: AbortSignal.timeout(5000) }).catch(() => null),
          fetch("/api/agents/proxy?path=/v1/notifications&status=pending", { signal: AbortSignal.timeout(5000) }).catch(() => null),
        ]);

        if (statsRes?.ok) {
          const stats = await statsRes.json();
          digest.tasksCompleted = stats.completed ?? 0;
          digest.tasksFailed = stats.failed ?? 0;
          digest.tasksRunning = stats.currently_running ?? stats.running ?? 0;
        }

        if (notifRes?.ok) {
          const notifs = await notifRes.json();
          const items = notifs.notifications ?? notifs ?? [];
          digest.pendingApprovals = Array.isArray(items) ? items.length : 0;
        }
      } catch {
        // Best effort
      }

      if (mounted) setData(digest);
    }

    fetchDigest();
    const interval = setInterval(fetchDigest, 60000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  if (!data) return null;

  const hasActivity = data.tasksCompleted > 0 || data.tasksFailed > 0 || data.tasksRunning > 0 || data.pendingApprovals > 0;
  if (!hasActivity) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Today</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-3 text-xs">
          {data.tasksCompleted > 0 && (
            <div className="flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
              <span>{data.tasksCompleted} completed</span>
            </div>
          )}
          {data.tasksRunning > 0 && (
            <div className="flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-full bg-amber animate-pulse" />
              <span>{data.tasksRunning} running</span>
            </div>
          )}
          {data.tasksFailed > 0 && (
            <div className="flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-full bg-red-500" />
              <span>{data.tasksFailed} failed</span>
            </div>
          )}
          {data.pendingApprovals > 0 && (
            <Badge variant="outline" className="text-xs">
              {data.pendingApprovals} pending approval{data.pendingApprovals > 1 ? "s" : ""}
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
