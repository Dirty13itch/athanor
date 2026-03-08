import Link from "next/link";

export default function InspectionsPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Inspections</h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            HERS rating jobs and field data entry
          </p>
        </div>
        <Link
          href="/inspections?action=new"
          className="rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-primary-hover)]"
        >
          New Inspection
        </Link>
      </div>

      {/* Status filter tabs */}
      <div className="mb-4 flex gap-1 rounded-lg bg-[var(--color-bg-card)] p-1">
        {["All", "Draft", "Submitted", "Reported", "Delivered"].map((tab) => (
          <button
            key={tab}
            className="rounded-md px-3 py-1.5 text-sm text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-elevated)] hover:text-[var(--color-text)] data-[active=true]:bg-[var(--color-bg-elevated)] data-[active=true]:text-[var(--color-text)]"
            data-active={tab === "All"}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Empty state */}
      <div className="flex flex-col items-center justify-center rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] py-16">
        <p className="mb-2 text-[var(--color-text-muted)]">
          No inspections yet
        </p>
        <p className="text-sm text-[var(--color-text-muted)]">
          Create your first inspection to get started.
        </p>
      </div>
    </div>
  );
}
