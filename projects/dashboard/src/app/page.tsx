import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { checkAllServices, queryPrometheus } from "@/lib/api";
import { config } from "@/lib/config";

export const revalidate = 30;

async function getGpuUtilByNode(): Promise<Map<string, number>> {
  const byNode = new Map<string, number[]>();
  try {
    const results = await queryPrometheus("DCGM_FI_DEV_GPU_UTIL");
    for (const r of results) {
      const instance = r.metric.instance ?? "";
      let node = instance;
      if (instance.includes("192.168.1.244")) node = "Node 1";
      else if (instance.includes("192.168.1.225")) node = "Node 2";
      const vals = byNode.get(node) ?? [];
      vals.push(parseFloat(r.value[1]));
      byNode.set(node, vals);
    }
  } catch {
    // Prometheus unavailable
  }

  const avgMap = new Map<string, number>();
  for (const [node, vals] of byNode) {
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
    avgMap.set(node, avg);
  }
  return avgMap;
}

interface AgentStatus {
  serverOnline: boolean;
  agents: string[];
}

async function getAgentStatus(): Promise<AgentStatus> {
  try {
    const res = await fetch("http://192.168.1.244:9000/health", {
      signal: AbortSignal.timeout(3000),
      next: { revalidate: 30 },
    });
    if (!res.ok) return { serverOnline: false, agents: [] };
    const data = await res.json();
    return { serverOnline: true, agents: data.agents ?? [] };
  } catch {
    return { serverOnline: false, agents: [] };
  }
}

export default async function DashboardPage() {
  const [services, gpuUtil, agentStatus] = await Promise.all([
    checkAllServices().catch(() => null),
    getGpuUtilByNode(),
    getAgentStatus(),
  ]);

  const healthyCount = services?.filter((s) => s.healthy).length ?? 0;
  const totalCount = services?.length ?? config.services.length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">Athanor homelab overview</p>
      </div>

      {/* Node cards */}
      <div className="grid gap-4 md:grid-cols-3">
        {config.nodes.map((node) => (
          <Card key={node.name}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">{node.name}</CardTitle>
              <CardDescription>{node.ip}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">{node.role}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Service health summary */}
        <Card>
          <CardHeader>
            <CardTitle>Services</CardTitle>
            <CardDescription>
              {healthyCount}/{totalCount} healthy
            </CardDescription>
          </CardHeader>
          <CardContent>
            {services ? (
              <div className="grid gap-2 sm:grid-cols-2">
                {services.map((svc) => (
                  <div
                    key={svc.name}
                    className="flex items-center justify-between rounded-md border border-border p-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{svc.name}</p>
                      <p className="text-xs text-muted-foreground">{svc.node}</p>
                    </div>
                    <Badge variant={svc.healthy ? "default" : "destructive"}>
                      {svc.healthy ? `${svc.latencyMs}ms` : "down"}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Unable to reach services.
              </p>
            )}
          </CardContent>
        </Card>

        {/* GPU Overview */}
        <Card>
          <CardHeader>
            <CardTitle>GPU Overview</CardTitle>
            <CardDescription>Average utilization by node</CardDescription>
          </CardHeader>
          <CardContent>
            {gpuUtil.size > 0 ? (
              <div className="space-y-4">
                {Array.from(gpuUtil.entries()).map(([node, avg]) => (
                  <div key={node}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">{node}</span>
                      <span className="text-sm font-mono text-muted-foreground">
                        {avg.toFixed(0)}%
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          avg > 80
                            ? "bg-red-500"
                            : avg > 50
                              ? "bg-yellow-500"
                              : "bg-green-500"
                        }`}
                        style={{ width: `${Math.min(100, avg)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No GPU metrics available.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Agent Status */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Agents</CardTitle>
              <Badge variant={agentStatus.serverOnline ? "default" : "destructive"}>
                {agentStatus.serverOnline ? "online" : "offline"}
              </Badge>
            </div>
            <CardDescription>LangGraph agents on Node 1:9000</CardDescription>
          </CardHeader>
          <CardContent>
            {agentStatus.serverOnline ? (
              <div className="space-y-2">
                {agentStatus.agents.map((name) => (
                  <div
                    key={name}
                    className="flex items-center justify-between rounded-md border border-border p-3"
                  >
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full bg-green-500" />
                      <span className="text-sm font-medium">
                        {name.split("-").map((w: string) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ")}
                      </span>
                    </div>
                    <a
                      href={`/chat?agent=${name}`}
                      className="text-xs text-primary hover:underline underline-offset-4"
                    >
                      Chat
                    </a>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Agent server unreachable.</p>
            )}
          </CardContent>
        </Card>

        {/* Quick Links */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Links</CardTitle>
            <CardDescription>External service UIs</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 sm:grid-cols-2">
              {QUICK_LINKS.map((link) => (
                <a
                  key={link.name}
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 rounded-md border border-border p-3 text-sm hover:bg-accent transition-colors"
                >
                  <span className="font-medium">{link.name}</span>
                  <span className="ml-auto text-xs text-muted-foreground">{link.node}</span>
                </a>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

const QUICK_LINKS = [
  { name: "Grafana", url: "http://192.168.1.203:3000", node: "VAULT" },
  { name: "Prometheus", url: "http://192.168.1.203:9090", node: "VAULT" },
  { name: "ComfyUI", url: "http://192.168.1.225:8188", node: "Node 2" },
  { name: "Open WebUI", url: "http://192.168.1.225:3000", node: "Node 2" },
  { name: "Plex", url: "http://192.168.1.203:32400/web", node: "VAULT" },
  { name: "Sonarr", url: "http://192.168.1.203:8989", node: "VAULT" },
  { name: "Radarr", url: "http://192.168.1.203:7878", node: "VAULT" },
  { name: "Tautulli", url: "http://192.168.1.203:8181", node: "VAULT" },
] as const;
