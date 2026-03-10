"use client";

import Link from "next/link";
import { useApiData } from "@/hooks/use-api-data";
import type { InspectionListItem } from "@/types/inspection";
import type { ReportListItem } from "@/types/report";

const quickActions = [
  { href: "/inspections/new", label: "New Inspection", icon: "+" },
  { href: "/reports", label: "View Reports", icon: "R" },
  { href: "/projects", label: "Projects", icon: "P" },
];

type AnalyticsResponse = {
  data?: {
    total_inspections: number;
    avg_hers_index: number | null;
    revenue: { estimated_this_month: number };
  };
};

export default function DashboardPage() {
  const analytics = useApiData<AnalyticsResponse>("/api/analytics/dashboard", {});
  const inspections = useApiData<{ inspections: InspectionListItem[] }>("/api/inspections", {
    inspections: [],
  });
  const reports = useApiData<{ reports: ReportListItem[] }>("/api/reports", { reports: [] });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Ulrich Energy</h1>
        <p className="text-muted-foreground">HERS Rating & Energy Testing</p>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {quickActions.map((action) => (
          <Link
            key={action.href}
            href={action.href}
            className="flex flex-col items-center gap-2 rounded-lg border border-border bg-card p-4 text-center transition-colors hover:bg-accent tap-highlight"
          >
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-lg font-bold text-primary-foreground">
              {action.icon}
            </span>
            <span className="text-sm font-medium">{action.label}</span>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Open Inspections" value={`${analytics.data.data?.total_inspections ?? inspections.data.inspections.length}`} />
        <StatCard
          label="Avg HERS"
          value={analytics.data.data?.avg_hers_index ? analytics.data.data.avg_hers_index.toFixed(1) : "--"}
        />
        <StatCard
          label="This Month"
          value={`$${analytics.data.data?.revenue.estimated_this_month ?? 0}`}
        />
      </div>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Recent Inspections</h2>
        <div className="space-y-2">
          {inspections.data.inspections.slice(0, 3).map((inspection) => (
            <Link
              key={inspection.id}
              href={`/inspections/${inspection.id}`}
              className="flex items-center justify-between rounded-lg border border-border bg-card p-4 transition-colors hover:bg-accent"
            >
              <div>
                <p className="font-medium">{inspection.address}</p>
                <p className="text-sm text-muted-foreground">{inspection.builder}</p>
              </div>
              <span className="rounded-full bg-primary/15 px-2 py-1 text-xs font-medium text-primary">
                {inspection.status}
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Recent Reports</h2>
        <div className="space-y-2">
          {reports.data.reports.slice(0, 3).map((report) => (
            <Link
              key={report.id}
              href={`/reports/${report.id}`}
              className="flex items-center justify-between rounded-lg border border-border bg-card p-4 transition-colors hover:bg-accent"
            >
              <div>
                <p className="font-medium">{report.address}</p>
                <p className="text-sm text-muted-foreground">
                  HERS Index: {report.hersIndex ?? "--"}
                </p>
              </div>
              <span className="rounded-full bg-success/20 px-2 py-0.5 text-xs font-medium text-success">
                {report.status}
              </span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
    </div>
  );
}
