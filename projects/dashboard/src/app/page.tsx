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

export default async function DashboardPage() {
  let services;
  try {
    services = await checkAllServices();
  } catch {
    services = null;
  }

  const healthyCount = services?.filter((s) => s.healthy).length ?? 0;
  const totalCount = services?.length ?? config.services.length;

  const gpuUtil = await getGpuUtilByNode();

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

      {/* Quick links */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Grafana</CardTitle>
          </CardHeader>
          <CardContent>
            <a
              href="http://192.168.1.203:3000"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary underline-offset-4 hover:underline"
            >
              Open Grafana dashboards
            </a>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Prometheus</CardTitle>
          </CardHeader>
          <CardContent>
            <a
              href="http://192.168.1.203:9090"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary underline-offset-4 hover:underline"
            >
              Open Prometheus UI
            </a>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
