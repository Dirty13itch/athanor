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
  coalition: string[];
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

interface AgentSubscription {
  agent_name: string;
  keywords: string[];
  source_filters: string[];
  threshold: number;
  react_prompt_template: string;
}

interface Convention {
  id: string;
  type: string;
  agent: string;
  description: string;
  rule: string;
  source: string;
  occurrences: number;
  status: string;
  created_at: number;
  confirmed_at: number;
}

const CONVENTION_TYPE_COLORS: Record<string, string> = {
  behavior: "bg-blue-500/20 text-blue-400",
  preference: "bg-purple-500/20 text-purple-400",
  schedule: "bg-green-500/20 text-green-400",
  quality: "bg-yellow-500/20 text-yellow-400",
};

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
  const [subscriptions, setSubscriptions] = useState<Record<string, AgentSubscription>>({});
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [endorsing, setEndorsing] = useState<string | null>(null);
  const [conventions, setConventions] = useState<Convention[]>([]);
  const [proposedConventions, setProposedConventions] = useState<Convention[]>([]);
  const [actingOnConvention, setActingOnConvention] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [broadcastRes, statsRes, agentsRes, subsRes, convRes, propConvRes] = await Promise.all([
        fetch(`${config.agentServer.url}/v1/workspace`),
        fetch(`${config.agentServer.url}/v1/workspace/stats`),
        fetch(`${config.agentServer.url}/v1/agents/registry`),
        fetch(`${config.agentServer.url}/v1/workspace/subscriptions`),
        fetch(`${config.agentServer.url}/v1/conventions`),
        fetch(`${config.agentServer.url}/v1/conventions?status=proposed`),
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
      if (subsRes.ok) {
        const data = await subsRes.json();
        setSubscriptions(data.subscriptions || {});
      }
      if (convRes.ok) {
        const data = await convRes.json();
        setConventions(data.conventions || []);
      }
      if (propConvRes.ok) {
        const data = await propConvRes.json();
        setProposedConventions(data.conventions || []);
      }
      setLastUpdated(new Date());
    } catch {
      // Silent fail — data will show stale
    } finally {
      setLoading(false);
    }
  }, []);

  const handleConventionAction = async (conventionId: string, action: "confirm" | "reject") => {
    setActingOnConvention(conventionId);
    try {
      await fetch(`${config.agentServer.url}/v1/conventions/${conventionId}/${action}`, {
        method: "POST",
      });
      await fetchData();
    } catch { /* silent */ }
    setActingOnConvention(null);
  };

  const handleEndorse = async (itemId: string, agentName: string) => {
    setEndorsing(itemId);
    try {
      await fetch(`${config.agentServer.url}/v1/workspace/${itemId}/endorse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agent_name: agentName }),
      });
      await fetchData();
    } catch { /* silent */ }
    setEndorsing(null);
  };

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
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
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
                        {item.coalition?.length > 0 && (
                          <span className="text-xs font-mono text-amber-400">
                            coalition: {item.coalition.join(", ")}
                          </span>
                        )}
                        <span className="ml-auto text-xs text-muted-foreground">
                          TTL: {item.ttl}s
                        </span>
                      </div>
                      <p className="text-sm text-foreground">{item.content}</p>
                      <div className="flex items-center gap-1 mt-2">
                        <span className="text-xs text-muted-foreground mr-1">Endorse:</span>
                        {Object.keys(AGENT_COLORS).filter(a => a !== item.source_agent && !item.coalition?.includes(a)).slice(0, 4).map(agent => (
                          <button
                            key={agent}
                            onClick={() => handleEndorse(item.id, agent)}
                            disabled={endorsing === item.id}
                            className="rounded border border-border px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors disabled:opacity-50"
                          >
                            {agent.split("-")[0]}
                          </button>
                        ))}
                      </div>
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
      {/* Convention Library — proposed conventions needing action */}
      {proposedConventions.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-amber-400 uppercase tracking-wider">
            Proposed Conventions ({proposedConventions.length})
          </h2>
          <div className="space-y-2">
            {proposedConventions.map((conv) => (
              <Card key={conv.id} className="border-amber-500/30">
                <CardContent className="py-3">
                  <div className="flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <Badge className={CONVENTION_TYPE_COLORS[conv.type] || "bg-muted text-foreground"}>
                          {conv.type}
                        </Badge>
                        <Badge className={AGENT_COLORS[conv.agent] || "bg-muted text-foreground"}>
                          {conv.agent}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {conv.occurrences}x &middot; {conv.source}
                        </span>
                      </div>
                      <p className="text-sm text-foreground mb-1">{conv.description}</p>
                      <p className="text-xs text-muted-foreground font-mono">{conv.rule}</p>
                    </div>
                    <div className="flex gap-1 flex-shrink-0">
                      <button
                        onClick={() => handleConventionAction(conv.id, "confirm")}
                        disabled={actingOnConvention === conv.id}
                        className="rounded border border-green-500/50 px-2 py-1 text-xs text-green-400 hover:bg-green-500/20 transition-colors disabled:opacity-50"
                      >
                        Confirm
                      </button>
                      <button
                        onClick={() => handleConventionAction(conv.id, "reject")}
                        disabled={actingOnConvention === conv.id}
                        className="rounded border border-red-500/50 px-2 py-1 text-xs text-red-400 hover:bg-red-500/20 transition-colors disabled:opacity-50"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Convention Library — confirmed conventions */}
      {conventions.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            Active Conventions ({conventions.length})
          </h2>
          <div className="grid gap-3 md:grid-cols-2">
            {conventions.map((conv) => (
              <Card key={conv.id}>
                <CardContent className="py-3">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <Badge className={CONVENTION_TYPE_COLORS[conv.type] || "bg-muted text-foreground"}>
                      {conv.type}
                    </Badge>
                    <Badge className={AGENT_COLORS[conv.agent] || "bg-muted text-foreground"}>
                      {conv.agent}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {conv.occurrences}x
                    </span>
                  </div>
                  <p className="text-sm text-foreground mb-1">{conv.description}</p>
                  <p className="text-xs text-muted-foreground font-mono">{conv.rule}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Phase 3: Agent Subscriptions */}
      {Object.keys(subscriptions).length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            Agent Subscriptions (Phase 3)
          </h2>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {Object.values(subscriptions).map((sub) => (
              <Card key={sub.agent_name}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">
                    {formatAgentName(sub.agent_name)}
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">
                    Threshold: {sub.threshold} &middot;{" "}
                    {sub.keywords.length} keywords
                  </p>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-1 mb-2">
                    {sub.keywords.slice(0, 8).map((kw) => (
                      <Badge key={kw} variant="outline" className="text-xs">
                        {kw}
                      </Badge>
                    ))}
                    {sub.keywords.length > 8 && (
                      <Badge variant="outline" className="text-xs text-muted-foreground">
                        +{sub.keywords.length - 8} more
                      </Badge>
                    )}
                  </div>
                  {sub.source_filters.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      <span className="text-xs text-muted-foreground">Sources:</span>
                      {sub.source_filters.map((src) => (
                        <Badge key={src} className="bg-green-500/20 text-green-400 text-xs">
                          {src}
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
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
