"use client";

import { useApiData } from "@/hooks/use-api-data";

type AnalyticsResponse = {
  data?: {
    inspections_by_status: Record<string, number>;
    total_inspections: number;
    avg_hers_index: number | null;
    avg_hers_by_builder: Array<{ builder: string; avg_hers: number; count: number }>;
    revenue: { estimated_this_month: number };
  };
};

export default function AnalyticsPage() {
  const { data, loading, error } = useApiData<AnalyticsResponse>("/api/analytics/dashboard", {});
  const analytics = data.data;

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold">Analytics</h1>
        <p className="text-sm text-[var(--color-text-muted)]">
          Job metrics, HERS averages, and revenue
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Total Jobs" value={loading ? "--" : `${analytics?.total_inspections ?? 0}`} />
        <StatCard
          label="Avg HERS Index"
          value={loading ? "--" : analytics?.avg_hers_index ? analytics.avg_hers_index.toFixed(1) : "--"}
        />
        <StatCard label="This Month" value={loading ? "$--" : `$${analytics?.revenue.estimated_this_month ?? 0}`} />
        <StatCard
          label="Completion Rate"
          value={
            loading
              ? "--%"
              : `${Math.round((((analytics?.inspections_by_status.reported ?? 0) + (analytics?.inspections_by_status.delivered ?? 0)) / Math.max(analytics?.total_inspections ?? 1, 1)) * 100)}%`
          }
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5">
          <h3 className="mb-4 text-sm font-medium text-[var(--color-text-muted)]">Jobs by Status</h3>
          <div className="space-y-2 text-sm">
            {Object.entries(analytics?.inspections_by_status ?? {}).map(([status, count]) => (
              <div key={status} className="flex items-center justify-between rounded-lg border border-border/70 bg-background p-3">
                <span className="capitalize">{status}</span>
                <span className="font-medium">{count}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5">
          <h3 className="mb-4 text-sm font-medium text-[var(--color-text-muted)]">HERS Index by Builder</h3>
          <div className="space-y-2 text-sm">
            {(analytics?.avg_hers_by_builder ?? []).map((builder) => (
              <div key={builder.builder} className="flex items-center justify-between rounded-lg border border-border/70 bg-background p-3">
                <span>{builder.builder}</span>
                <span className="font-medium">
                  {builder.avg_hers.toFixed(1)} · {builder.count} jobs
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-4">
      <p className="text-xs text-[var(--color-text-muted)]">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
    </div>
  );
}
