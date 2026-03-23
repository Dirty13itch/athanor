"use client";

import { useQuery } from "@tanstack/react-query";
import { GitCommit, Monitor, ChevronRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

interface Commit {
  hash: string;
  author: string;
  message: string;
  when: string;
}

interface Session {
  name: string;
  created: string;
  last_activity: string;
}

export function AgentWorkPanel() {
  const { data: commitData } = useQuery<{ commits: Commit[]; count: number }>({
    queryKey: ["agent-commits"],
    queryFn: () => fetch("/api/governor/commits").then((r) => r.json()),
    refetchInterval: 30_000,
  });

  const { data: sessionData } = useQuery<{ sessions: Session[]; count: number }>({
    queryKey: ["agent-sessions"],
    queryFn: () => fetch("/api/governor/sessions").then((r) => r.json()),
    refetchInterval: 15_000,
  });

  const commits = commitData?.commits ?? [];
  const sessions = sessionData?.sessions ?? [];

  return (
    <Card className="surface-panel">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle className="text-base font-semibold">Agent Output</CardTitle>
          <p className="text-xs text-muted-foreground mt-0.5">
            {sessions.length} agents active · {commits.length} commits last 24h
          </p>
        </div>
        <Link href="/activity" className="text-xs text-primary hover:underline flex items-center gap-1">
          History <ChevronRight className="h-3 w-3" />
        </Link>
      </CardHeader>
      <CardContent className="space-y-3">
        {sessions.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground">Running Now</p>
            {sessions.slice(0, 4).map((s) => (
              <div key={s.name} className="flex items-center gap-2 rounded-lg px-2 py-1.5 bg-primary/5 border border-primary/10">
                <Monitor className="h-3.5 w-3.5 text-primary animate-pulse shrink-0" />
                <span className="text-xs truncate">{s.name.replace("agent-", "").replace("opencode-", "oc/").replace("claude-", "cc/").replace("codex-", "cx/")}</span>
              </div>
            ))}
            {sessions.length > 4 && (
              <p className="text-[10px] text-muted-foreground pl-2">+{sessions.length - 4} more</p>
            )}
          </div>
        )}

        {commits.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground">Recent Commits</p>
            {commits.slice(0, 5).map((c) => (
              <div key={c.hash} className="flex items-start gap-2 rounded-lg px-2 py-1.5 hover:bg-background/40 transition-colors">
                <GitCommit className="h-3.5 w-3.5 text-emerald-400 shrink-0 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <p className="text-xs truncate">{c.message}</p>
                  <p className="text-[10px] text-muted-foreground">
                    <Badge variant="outline" className="text-[9px] mr-1">{c.hash}</Badge>
                    {c.when}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}

        {sessions.length === 0 && commits.length === 0 && (
          <p className="text-xs text-muted-foreground text-center py-3">No agent activity in the last 24 hours.</p>
        )}
      </CardContent>
    </Card>
  );
}
