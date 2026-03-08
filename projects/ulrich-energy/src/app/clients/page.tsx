export default function ClientsPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Clients</h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            Builders and homeowner contacts
          </p>
        </div>
        <button className="rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-primary-hover)]">
          Add Client
        </button>
      </div>

      <div className="flex flex-col items-center justify-center rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] py-16">
        <p className="mb-2 text-[var(--color-text-muted)]">No clients yet</p>
        <p className="text-sm text-[var(--color-text-muted)]">
          Add builders and homeowners to track relationships.
        </p>
      </div>
    </div>
  );
}
