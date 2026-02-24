"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface AgentInfo {
  name: string;
  description: string;
  tools: string[];
  type: string;
  schedule?: string;
  status: "online" | "planned" | "offline";
  status_note?: string;
}

interface AgentResponse {
  status: "online" | "offline";
  agents: AgentInfo[];
}

export default function AgentsPage() {
  const [data, setData] = useState<AgentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const router = useRouter();

  const fetchAgents = useCallback(async () => {
    try {
      const res = await fetch("/api/agents");
      if (!res.ok) throw new Error("Failed to fetch");
      const json: AgentResponse = await res.json();
      setData(json);
      setLastUpdated(new Date());
    } catch {
      setData({ status: "offline", agents: [] });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
    const id = setInterval(fetchAgents, 15000);
    return () => clearInterval(id);
  }, [fetchAgents]);

  const onlineAgents = data?.agents.filter((a) => a.status === "online") ?? [];
  const plannedAgents = data?.agents.filter((a) => a.status === "planned") ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Agents</h1>
          <p className="text-muted-foreground">
            LangGraph agents running on Foundry (Node 1)
          </p>
        </div>
        <div className="flex items-center gap-3">
          {data && (
            <Badge variant={data.status === "online" ? "default" : "destructive"}>
              {data.status === "online" ? "Server Online" : "Server Offline"}
            </Badge>
          )}
          {lastUpdated && (
            <span className="text-xs text-muted-foreground">
              {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {loading && (
        <Card>
          <CardContent className="py-6">
            <p className="text-sm text-muted-foreground">Connecting to agent server...</p>
          </CardContent>
        </Card>
      )}

      {data?.status === "offline" && !loading && (
        <Card>
          <CardContent className="py-6">
            <p className="text-sm text-destructive">
              Agent server at 192.168.1.244:9000 is unreachable.
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Ensure the agent container is running on Foundry.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Online agents */}
      {onlineAgents.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Active</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {onlineAgents.map((agent) => (
              <AgentCard key={agent.name} agent={agent} onChat={() => router.push(`/chat?agent=${agent.name}`)} />
            ))}
          </div>
        </div>
      )}

      {/* Planned agents */}
      {plannedAgents.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Coming Soon</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {plannedAgents.map((agent) => (
              <AgentCard key={agent.name} agent={agent} />
            ))}
          </div>
        </div>
      )}

      {data?.agents.length === 0 && data.status === "online" && (
        <Card>
          <CardContent className="py-6">
            <p className="text-sm text-muted-foreground">
              Agent server is online but no agents are registered.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function AgentCard({ agent, onChat }: { agent: AgentInfo; onChat?: () => void }) {
  const isPlanned = agent.status === "planned";

  return (
    <Card className={`flex flex-col ${isPlanned ? "opacity-60" : ""}`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{formatAgentName(agent.name)}</CardTitle>
          <div className="flex items-center gap-1.5">
            <Badge
              variant={agent.type === "proactive" ? "default" : "outline"}
              className="text-xs"
            >
              {agent.type}
            </Badge>
            {isPlanned ? (
              <Badge variant="outline" className="text-xs">Planned</Badge>
            ) : (
              <Badge variant="default" className="text-xs">{agent.status}</Badge>
            )}
          </div>
        </div>
        <CardDescription className="text-xs font-mono text-muted-foreground">
          {agent.name}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col justify-between gap-4">
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">{agent.description}</p>
          {agent.schedule && (
            <p className="text-xs text-muted-foreground">
              Schedule: <span className="font-mono">{agent.schedule}</span>
            </p>
          )}
          {agent.status_note && (
            <p className="text-xs text-yellow-500">
              {agent.status_note}
            </p>
          )}
        </div>
        <div>
          <p className="text-xs font-medium mb-2 text-muted-foreground">Tools</p>
          <div className="flex flex-wrap gap-1">
            {agent.tools.map((tool) => (
              <Badge key={tool} variant="outline" className="text-xs font-mono">
                {tool}
              </Badge>
            ))}
          </div>
        </div>
        {onChat ? (
          <Button
            onClick={onChat}
            disabled={agent.status !== "online"}
            className="w-full"
          >
            Start Chat
          </Button>
        ) : (
          <Button disabled className="w-full">
            Coming Soon
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

function formatAgentName(name: string): string {
  return name
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
