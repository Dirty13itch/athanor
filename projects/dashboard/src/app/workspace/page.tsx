"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { config } from "@/lib/config";

interface WorkspaceItem {
  id: string;
  source_agent: string;
  content: string;
  priority: string;
  salience: number;
  ttl: number;
  created_at: number;
  metadata: Record<string, unknown>;
}

interface WorkspaceStats {
  total_items: number;
  broadcast_items: number;
  capacity: number;
  utilization: number;
  agents_active: Record<string, number>;
  top_item: WorkspaceItem | null;
  competition_running: boolean;
}

interface RegisteredAgent {
  name: string;
  capabilities: string[];
  type: string;
  subscriptions: string[];
  registered_at: number;
  status: string;
}

const PRIORITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400",
  high: "bg-orange-500/20 text-orange-400",
  normal: "bg-blue-500/20 text-blue-400",
  low: "bg-zinc-500/20 text-zinc-400",
};

const AGENT_COLORS: Record<string, string> = {
  "general-assistant": "bg-blue-500/20 text-blue-400",
  "media-agent": "bg-purple-500/20 text-purple-400",
  "research-agent": "bg-green-500/20 text-green-400",
  "creative-agent": "bg-pink-500/20 text-pink-400",
  "knowledge-agent": "bg-yellow-500/20 text-yellow-400",
  "home-agent": "bg-orange-500/20 text-orange-400",
  "coding-agent": "bg-cyan-500/20 text-cyan-400",
  "stash-agent": "bg-fuchsia-500/20 text-fuchsia-400",
};

export default function WorkspacePage() {
  const [broadcast, setBroadcast] = useState<WorkspaceItem[]>([]);
  const [stats, setStats] = useState<WorkspaceStats | null>(null);
  const [agents, setAgents] = useState<Record<string, RegisteredAgent>>({});
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [broadcastRes, statsRes, agentsRes] = await Promise.all([
        fetch(`${config.agentServer.url}/v1/workspace`),
        fetch(`${config.agentServer.url}/v1/workspace/stats`),
        fetch(`${config.agentServer.url}/v1/agents/registry`),
      ]);

      if (broadcastRes.ok) {
        const data = await broadcastRes.json();
        setBroadcast(data.broadcast || []);
      }
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
      if (agentsRes.ok) {
        const data = await agentsRes.json();
        setAgents(data.agents || {});
      }
      setLastUpdated(new Date());
    } catch {
      // Silent fail — data will show stale
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 5000);
    return () => clearInterval(id);
  }, [fetchData]);

  const agentCount = Object.keys(agents).length;
  const totalTools = Object.values(agents).reduce(
    (sum, a) => sum + a.capabilities.length,
    0
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Workspace</h1>
          <p className="text-muted-foreground">
            GWT broadcast, agent registry, and competition state
          </p>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <p className="text-xs text-muted-foreground">
              Updated {lastUpdated.toLocaleTimeString()}
            </p>
          )}
          {stats && (
            <Badge
              variant={stats.competition_running ? "default" : "destructive"}
            >
              {stats.competition_running ? "Competition Running" : "Competition Stopped"}
            </Badge>
          )}
        </div>
      </div>

      {loading && (
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-muted-foreground">
              Loading workspace...
            </p>
          </CardContent>
        </Card>
      )}

      {/* Stats overview */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardContent className="py-4">
              <p className="text-xs text-muted-foreground uppercase tracking-wider">
                Broadcast Items
              </p>
              <p className="text-2xl font-bold">
                {stats.broadcast_items}{" "}
                <span className="text-sm font-normal text-muted-foreground">
                  / {stats.capacity}
                </span>
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-4">
              <p className="text-xs text-muted-foreground uppercase tracking-wider">
                Utilization
              </p>
              <p className="text-2xl font-bold">
                {(stats.utilization * 100).toFixed(0)}%
              </p>
              <div className="mt-1 h-1.5 rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{ width: `${stats.utilization * 100}%` }}
                />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-4">
              <p className="text-xs text-muted-foreground uppercase tracking-wider">
                Agents Registered
              </p>
              <p className="text-2xl font-bold">{agentCount}</p>
              <p className="text-xs text-muted-foreground">
                {totalTools} tools total
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-4">
              <p className="text-xs text-muted-foreground uppercase tracking-wider">
                Total Candidates
              </p>
              <p className="text-2xl font-bold">{stats.total_items}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Current broadcast */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
          Current Broadcast (Top {stats?.capacity ?? 7} by Salience)
        </h2>
        {broadcast.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center">
              <p className="text-sm text-muted-foreground">
                No items in broadcast. Post events via{" "}
                <code className="text-xs">POST /v1/events</code> or{" "}
                <code className="text-xs">POST /v1/workspace</code>.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {broadcast.map((item, idx) => (
              <Card key={item.id}>
                <CardContent className="py-3">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 pt-1">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                        {idx + 1}
                      </div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge
                          className={
                            AGENT_COLORS[item.source_agent] ||
                            "bg-muted text-foreground"
                          }
                        >
                          {item.source_agent}
                        </Badge>
                        <Badge
                          className={
                            PRIORITY_COLORS[item.priority] ||
                            "bg-muted text-foreground"
                          }
                        >
                          {item.priority}
                        </Badge>
                        <span className="text-xs font-mono text-muted-foreground">
                          salience: {item.salience.toFixed(2)}
                        </span>
                        <span className="ml-auto text-xs text-muted-foreground">
                          TTL: {item.ttl}s
                        </span>
                      </div>
                      <p className="text-sm text-foreground">{item.content}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Agent registry */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
          Agent Registry
        </h2>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          {Object.values(agents).map((agent) => (
            <Card key={agent.name}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm">
                    {formatAgentName(agent.name)}
                  </CardTitle>
                  <Badge
                    variant={agent.type === "proactive" ? "default" : "outline"}
                    className="text-xs"
                  >
                    {agent.type}
                  </Badge>
                </div>
                <p className="text-xs font-mono text-muted-foreground">
                  {agent.name}
                </p>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-1">
                  {agent.capabilities.map((cap) => (
                    <Badge
                      key={cap}
                      variant="outline"
                      className="text-xs font-mono"
                    >
                      {cap}
                    </Badge>
                  ))}
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  Registered{" "}
                  {formatTimestamp(
                    new Date(agent.registered_at * 1000).toISOString()
                  )}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

function formatAgentName(name: string): string {
  return name
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function formatTimestamp(ts: string): string {
  try {
    const date = new Date(ts);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);

    if (diffMin < 1) return "just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffMin < 1440) return `${Math.floor(diffMin / 60)}h ago`;
    return date.toLocaleDateString();
  } catch {
    return ts;
  }
}
