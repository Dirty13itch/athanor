"use client";

import { useQuery } from "@tanstack/react-query";
import { Crown, Swords, Heart, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface GameStats {
  totalQueens: number;
  brokenQueens: number;
  averageResistance: number;
  averageCorruption: number;
  totalDialogues: number;
  totalGenerations: number;
  totalMemories: number;
}

function StatBox({ icon: Icon, label, value, color }: {
  icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>;
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border/50 bg-card/50 px-4 py-3">
      <Icon className="h-5 w-5 shrink-0" style={{ color }} />
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-lg font-semibold tabular-nums">{value}</p>
      </div>
    </div>
  );
}

export function GameStatsCard() {
  const { data: queensData } = useQuery<{ queens: Array<{ resistance: number; corruption: number }> }>({
    queryKey: ["eoq", "queens"],
    queryFn: async () => {
      const res = await fetch("/api/eoq/queens");
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
    staleTime: 60_000,
  });

  const { data: dialogueData } = useQuery<{ dialogues: unknown[] }>({
    queryKey: ["eoq", "conversations"],
    queryFn: async () => {
      const res = await fetch("/api/eoq/conversations");
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
    staleTime: 30_000,
  });

  const { data: genData } = useQuery<{ generations: unknown[] }>({
    queryKey: ["eoq", "generations"],
    queryFn: async () => {
      const res = await fetch("/api/eoq/generations");
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
    staleTime: 30_000,
  });

  const queens = queensData?.queens ?? [];
  const stats: GameStats = {
    totalQueens: queens.length,
    brokenQueens: queens.filter((q) => q.resistance === 0).length,
    averageResistance: queens.length > 0
      ? Math.round(queens.reduce((sum, q) => sum + q.resistance, 0) / queens.length)
      : 0,
    averageCorruption: queens.length > 0
      ? Math.round(queens.reduce((sum, q) => sum + q.corruption, 0) / queens.length)
      : 0,
    totalDialogues: dialogueData?.dialogues?.length ?? 0,
    totalGenerations: genData?.generations?.length ?? 0,
    totalMemories: 0,
  };

  return (
    <Card className="surface-panel">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Crown className="h-5 w-5 text-primary" />
          <span style={{ fontFamily: "'Cormorant Garamond', serif" }}>Empire Status</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatBox
            icon={Crown}
            label="Queens"
            value={`${stats.brokenQueens}/${stats.totalQueens} broken`}
            color="oklch(0.55 0.15 300)"
          />
          <StatBox
            icon={Swords}
            label="Avg Resistance"
            value={`${stats.averageResistance}%`}
            color="oklch(0.6 0.15 25)"
          />
          <StatBox
            icon={Heart}
            label="Avg Corruption"
            value={`${stats.averageCorruption}%`}
            color="oklch(0.5 0.2 300)"
          />
          <StatBox
            icon={Zap}
            label="Dialogues"
            value={stats.totalDialogues}
            color="oklch(0.7 0.12 80)"
          />
        </div>
      </CardContent>
    </Card>
  );
}
