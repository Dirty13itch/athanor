"use client";

import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Cloud, Gavel, Shield, Users2 } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { StatusDot } from "@/components/status-dot";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getSystemMap } from "@/lib/api";
import type { SystemMapSnapshot } from "@/lib/contracts";
import { isOperatorSessionLocked, useOperatorSessionStatus } from "@/lib/operator-session";
import { queryKeys } from "@/lib/query-client";

function laneTone(status: string): "healthy" | "warning" {
  return status === "live" ? "healthy" : "warning";
}

function compactLabel(value: string) {
  return value.replace(/_/g, " ");
}

function summarizeRights(snapshot: SystemMapSnapshot) {
  return snapshot.command_rights
    .slice(0, 3)
    .map((entry) => `${entry.subject}: ${entry.can.slice(0, 2).join(", ")}`)
    .join(" | ");
}

export function SystemMapCard() {
  const session = useOperatorSessionStatus();
  const locked = isOperatorSessionLocked(session);
  const systemMapQuery = useQuery({
    queryKey: queryKeys.systemMap,
    queryFn: getSystemMap,
    enabled: !locked,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  if (locked) {
    return (
      <Card className="surface-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Shield className="h-5 w-5 text-primary" />
            Command hierarchy
          </CardTitle>
          <CardDescription>
            Unlock the operator session to inspect the live command hierarchy and governance snapshot.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="Unlock required"
            description="The command-hierarchy snapshot is intentionally hidden until the operator session is unlocked."
            className="py-8"
          />
        </CardContent>
      </Card>
    );
  }

  if (systemMapQuery.isError && !systemMapQuery.data) {
    return (
      <ErrorPanel
        title="Command hierarchy"
        description={
          systemMapQuery.error instanceof Error
            ? systemMapQuery.error.message
            : "Failed to load command hierarchy state."
        }
      />
    );
  }

  const snapshot = systemMapQuery.data;
  if (!snapshot) {
    return (
      <EmptyState
        title="No command hierarchy yet"
        description="The operator-facing system map has not returned a runtime snapshot."
      />
    );
  }

  return (
    <Card className="surface-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Shield className="h-5 w-5 text-primary" />
          Command hierarchy
        </CardTitle>
        <CardDescription>
          Who decides, which meta lane is active, and how Athanor keeps command rights inside the governor.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <Metric
            icon={<Gavel className="h-4 w-4 text-primary" />}
            label="Governor"
            value={snapshot.governor.label}
            detail={snapshot.governor.status.replace(/_/g, " ")}
          />
          <Metric
            icon={<Cloud className="h-4 w-4 text-primary" />}
            label="Meta lanes"
            value={`${snapshot.meta_lanes.length}`}
            detail="frontier + sovereign"
          />
          <Metric
            icon={<Users2 className="h-4 w-4 text-primary" />}
            label="Specialists"
            value={`${snapshot.specialists.length}`}
            detail={`${snapshot.control_stack.length} control-stack layers`}
          />
        </div>

        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Authority order</p>
          <div className="flex flex-wrap items-center gap-2">
            {snapshot.authority_order.map((layer, index) => (
              <div key={layer.id} className="flex items-center gap-2">
                <span className="surface-metric rounded-full border px-3 py-1 text-xs font-medium">
                  {layer.label}
                </span>
                {index < snapshot.authority_order.length - 1 ? (
                  <span className="text-xs text-muted-foreground">-&gt;</span>
                ) : null}
              </div>
            ))}
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          {snapshot.meta_lanes.map((lane) => (
            <div key={lane.id} className="surface-tile rounded-2xl border p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <StatusDot tone={laneTone(lane.status)} className="mt-0.5" />
                    <p className="font-medium">{lane.label}</p>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">lead: {lane.lead}</p>
                </div>
                <Badge variant={lane.cloud_allowed ? "outline" : "secondary"}>
                  {lane.cloud_allowed ? "cloud allowed" : "local only"}
                </Badge>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {lane.default_for.map((policyClass) => (
                  <Badge key={policyClass} variant="secondary">
                    {compactLabel(policyClass)}
                  </Badge>
                ))}
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                {lane.examples.map((example) => (
                  <span key={example} className="rounded-full border border-border/60 px-2 py-1">
                    {compactLabel(example)}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-3 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Control stack</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {snapshot.control_stack.map((layer) => (
                <div key={layer.id} className="surface-metric rounded-xl border px-3 py-2 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium">{layer.label}</p>
                    <Badge variant="outline">{layer.status.replace(/_/g, " ")}</Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{layer.role}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Policy classes</p>
            {snapshot.policy_classes.map((policyClass) => (
              <div key={policyClass.id} className="surface-metric rounded-xl border px-3 py-2 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-medium">{policyClass.label}</p>
                  <Badge variant={policyClass.cloud_allowed ? "outline" : "secondary"}>
                    {policyClass.cloud_allowed ? "frontier allowed" : "sovereign"}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{policyClass.description}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="surface-metric rounded-xl border px-3 py-3 text-sm text-muted-foreground">
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Rights summary</p>
          <p className="mt-2">{summarizeRights(snapshot)}</p>
        </div>

        {snapshot.operational_governance ? (
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Operational governance</p>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <Metric
                icon={<Shield className="h-4 w-4 text-primary" />}
                label="Presence"
                value={compactLabel(snapshot.operational_governance.presence_model.default_state)}
                detail={snapshot.operational_governance.presence_model.status.replace(/_/g, " ")}
              />
              <Metric
                icon={<Cloud className="h-4 w-4 text-primary" />}
                label="Budget"
                value={`${snapshot.operational_governance.economic_governance.reserve_lanes.length} reserve lanes`}
                detail={snapshot.operational_governance.economic_governance.status.replace(/_/g, " ")}
              />
              <Metric
                icon={<Gavel className="h-4 w-4 text-primary" />}
                label="Restore"
                value={`${snapshot.operational_governance.backup_restore.critical_store_count} critical stores`}
                detail={snapshot.operational_governance.backup_restore.drill_status.replace(/_/g, " ")}
              />
              <Metric
                icon={<Users2 className="h-4 w-4 text-primary" />}
                label="Lifecycle"
                value={`${snapshot.operational_governance.data_lifecycle.class_count} classes`}
                detail={`${snapshot.operational_governance.data_lifecycle.sovereign_only_classes.length} local-only`}
              />
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function Metric({
  icon,
  label,
  value,
  detail,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="surface-metric rounded-xl border px-3 py-3">
      <div className="flex items-center gap-2 text-muted-foreground">{icon}</div>
      <p className="mt-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}
