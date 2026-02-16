"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface ServiceStatus {
  name: string;
  node: string;
  url: string;
  healthy: boolean;
  latencyMs: number | null;
}

export default function ServicesPage() {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchServices = useCallback(async () => {
    try {
      const res = await fetch("/api/services");
      if (!res.ok) throw new Error(`Failed to fetch services (${res.status})`);
      const data: ServiceStatus[] = await res.json();
      setServices(data);
      setError(null);
      setLastUpdated(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to check services");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchServices();
    const id = setInterval(fetchServices, 15000);
    return () => clearInterval(id);
  }, [fetchServices]);

  // Group by node
  const byNode = new Map<string, ServiceStatus[]>();
  for (const svc of services) {
    const group = byNode.get(svc.node) ?? [];
    group.push(svc);
    byNode.set(svc.node, group);
  }

  const healthyCount = services.filter((s) => s.healthy).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Services</h1>
          <p className="text-muted-foreground">Status of all monitored services</p>
        </div>
        <div className="text-right">
          {!loading && (
            <Badge variant="outline">
              {healthyCount}/{services.length} healthy
            </Badge>
          )}
          {lastUpdated && (
            <p className="text-xs text-muted-foreground mt-1">
              Updated {lastUpdated.toLocaleTimeString()}
            </p>
          )}
        </div>
      </div>

      {loading && (
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-muted-foreground">Checking services...</p>
          </CardContent>
        </Card>
      )}

      {error && (
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {Array.from(byNode.entries()).map(([node, svcs]) => (
        <Card key={node}>
          <CardHeader>
            <CardTitle>{node}</CardTitle>
            <CardDescription>
              {svcs.filter((s) => s.healthy).length}/{svcs.length} healthy
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {svcs.map((svc) => (
                <div
                  key={svc.name}
                  className="flex items-center justify-between rounded-md border border-border p-3"
                >
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div
                      className={`h-2.5 w-2.5 rounded-full shrink-0 ${
                        svc.healthy ? "bg-green-500" : "bg-red-500"
                      }`}
                    />
                    <div className="min-w-0">
                      <p className="text-sm font-medium">{svc.name}</p>
                      <p className="truncate text-xs font-mono text-muted-foreground">{svc.url}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {svc.latencyMs !== null && (
                      <span className="text-xs text-muted-foreground">{svc.latencyMs}ms</span>
                    )}
                    <Badge variant={svc.healthy ? "default" : "destructive"}>
                      {svc.healthy ? "healthy" : "unreachable"}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}

      {services.length === 0 && !loading && !error && (
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-muted-foreground">No services configured.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
