export default function AnalyticsPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold">Analytics</h1>
        <p className="text-sm text-[var(--color-text-muted)]">
          Job metrics, HERS averages, and revenue
        </p>
      </div>

      {/* Stat cards */}
      <div className="mb-6 grid gap-4 grid-cols-2 sm:grid-cols-4">
        <StatCard label="Total Jobs" value="--" />
        <StatCard label="Avg HERS Index" value="--" />
        <StatCard label="This Month" value="$--" />
        <StatCard label="Completion Rate" value="--%" />
      </div>

      {/* Placeholder chart areas */}
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5">
          <h3 className="mb-4 text-sm font-medium text-[var(--color-text-muted)]">
            Jobs by Status
          </h3>
          <div className="flex h-40 items-center justify-center text-sm text-[var(--color-text-muted)]">
            Chart placeholder
          </div>
        </div>
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5">
          <h3 className="mb-4 text-sm font-medium text-[var(--color-text-muted)]">
            HERS Index by Builder
          </h3>
          <div className="flex h-40 items-center justify-center text-sm text-[var(--color-text-muted)]">
            Chart placeholder
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
