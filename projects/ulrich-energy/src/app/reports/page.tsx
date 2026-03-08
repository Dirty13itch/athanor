export default function ReportsPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold">Reports</h1>
        <p className="text-sm text-[var(--color-text-muted)]">
          AI-generated energy audit reports
        </p>
      </div>

      <div className="flex flex-col items-center justify-center rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] py-16">
        <p className="mb-2 text-[var(--color-text-muted)]">No reports yet</p>
        <p className="text-sm text-[var(--color-text-muted)]">
          Submit an inspection to generate a report.
        </p>
      </div>
    </div>
  );
}
