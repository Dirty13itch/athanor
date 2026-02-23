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
  status: "online" | "offline";
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Agents</h1>
          <p className="text-muted-foreground">
            LangGraph agents running on Node 1
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
              Ensure the agent container is running on Node 1.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {data?.agents.map((agent) => (
          <Card key={agent.name} className="flex flex-col">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{formatAgentName(agent.name)}</CardTitle>
                <Badge
                  variant={agent.status === "online" ? "default" : "destructive"}
                  className="text-xs"
                >
                  {agent.status}
                </Badge>
              </div>
              <CardDescription className="text-xs font-mono text-muted-foreground">
                {agent.name}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-1 flex-col justify-between gap-4">
              <p className="text-sm text-muted-foreground">{agent.description}</p>
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
              <Button
                onClick={() => router.push(`/chat?agent=${agent.name}`)}
                disabled={agent.status !== "online"}
                className="w-full"
              >
                Start Chat
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

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

function formatAgentName(name: string): string {
  return name
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
