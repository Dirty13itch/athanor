"use client";

import { useQuery } from "@tanstack/react-query";
import { Target, Star, ChevronRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import Link from "next/link";

interface Goal {
  id: string;
  text: string;
  agent: string;
  priority: string;
  active: boolean;
}

const priorityStyle = {
  high: "text-amber-400 border-amber-500/30 bg-amber-500/10",
  medium: "text-primary border-primary/30 bg-primary/10",
  normal: "text-muted-foreground border-border bg-background/40",
};

export function GoalsPanel() {
  const { data } = useQuery<{ goals: Goal[] }>({
    queryKey: ["goals-overview"],
    queryFn: () => fetch("/api/workforce/goals").then((r) => r.json()),
    refetchInterval: 120_000,
  });

  const goals = (data?.goals ?? []).filter((g) => g.active);
  const highPriority = goals.filter((g) => g.priority === "high");
  const other = goals.filter((g) => g.priority !== "high");

  return (
    <Card className="surface-panel">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle className="text-base font-semibold">Active Goals</CardTitle>
          <p className="text-xs text-muted-foreground mt-0.5">
            {highPriority.length} high priority · {other.length} other · steering all agent work
          </p>
        </div>
        <Link href="/goals" className="text-xs text-primary hover:underline flex items-center gap-1">
          Manage <ChevronRight className="h-3 w-3" />
        </Link>
      </CardHeader>
      <CardContent className="space-y-2">
        {goals.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-4">No active goals. Add goals to steer the system.</p>
        )}
        {[...highPriority, ...other].map((goal) => (
          <div key={goal.id} className="flex items-start gap-2.5 rounded-xl border border-border/40 bg-background/30 px-3 py-2">
            {goal.priority === "high" ? (
              <Star className="h-3.5 w-3.5 text-amber-400 shrink-0 mt-0.5 fill-amber-400" />
            ) : (
              <Target className="h-3.5 w-3.5 text-muted-foreground shrink-0 mt-0.5" />
            )}
            <div className="min-w-0 flex-1">
              <p className="text-sm leading-snug">{goal.text.length > 100 ? goal.text.slice(0, 100) + "..." : goal.text}</p>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="outline" className={cn("text-[10px]", priorityStyle[goal.priority as keyof typeof priorityStyle] ?? priorityStyle.normal)}>
                  {goal.priority}
                </Badge>
                <span className="text-[10px] text-muted-foreground">{goal.agent}</span>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
