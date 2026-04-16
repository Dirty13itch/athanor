"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { extractTaskResidueSummary } from "@/lib/task-residue";

interface DigestData {
  tasksCompleted: number;
  actionableFailures: number;
  tasksRunning: number;
  pendingApprovals: number;
  staleLeases: number;
}

export function DailyDigest() {
  const [data, setData] = useState<DigestData | null>(null);

  useEffect(() => {
    let mounted = true;

    async function fetchDigest() {
      const digest: DigestData = {
        tasksCompleted: 0,
        actionableFailures: 0,
        tasksRunning: 0,
        pendingApprovals: 0,
        staleLeases: 0,
      };

      try {
        const operatorRes = await fetch("/api/operator/summary", {
          signal: AbortSignal.timeout(5000),
        }).catch(() => null);

        if (operatorRes?.ok) {
          const operator = await operatorRes.json();
          const taskSummary = extractTaskResidueSummary(operator?.tasks);
          digest.tasksCompleted = taskSummary.completed;
          digest.actionableFailures = taskSummary.failed_actionable;
          digest.tasksRunning = taskSummary.currently_running;
          digest.pendingApprovals = operator?.approvals?.by_status?.pending ?? 0;
          digest.staleLeases = taskSummary.stale_lease;
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

  const hasActivity =
    data.tasksCompleted > 0 ||
    data.actionableFailures > 0 ||
    data.tasksRunning > 0 ||
    data.pendingApprovals > 0 ||
    data.staleLeases > 0;
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
              <span className="inline-block h-2 w-2 rounded-full bg-primary animate-pulse" />
              <span>{data.tasksRunning} running</span>
            </div>
          )}
          {data.actionableFailures > 0 && (
            <div className="flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-full bg-red-500" />
              <span>{data.actionableFailures} actionable failures</span>
            </div>
          )}
          {data.pendingApprovals > 0 && (
            <Badge variant="outline" className="text-xs">
              {data.pendingApprovals} pending approval{data.pendingApprovals > 1 ? "s" : ""}
            </Badge>
          )}
          {data.staleLeases > 0 && (
            <Badge variant="outline" className="text-xs">
              {data.staleLeases} stale lease{data.staleLeases > 1 ? "s" : ""}
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
