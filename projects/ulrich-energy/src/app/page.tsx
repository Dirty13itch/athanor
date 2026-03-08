import Link from "next/link";

const workflows = [
  {
    title: "Inspections",
    href: "/inspections",
    description: "Create and manage HERS rating inspections. Enter field data, upload photos, track job status.",
    icon: ClipboardIcon,
    count: null, // Will be dynamic
  },
  {
    title: "Reports",
    href: "/reports",
    description: "Generate AI-powered energy audit reports. Review, edit, and deliver to clients.",
    icon: DocumentIcon,
    count: null,
  },
  {
    title: "Clients",
    href: "/clients",
    description: "Builder and homeowner contacts. Track relationships and job history.",
    icon: UsersIcon,
    count: null,
  },
  {
    title: "Analytics",
    href: "/analytics",
    description: "Dashboard metrics. Jobs by status, HERS averages, failure patterns, revenue.",
    icon: ChartIcon,
    count: null,
  },
];

export default function HomePage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Ulrich Energy</h1>
        <p className="mt-1 text-[var(--color-text-muted)]">
          HERS Rating &amp; Energy Audit Management
        </p>
      </div>

      {/* Quick Actions */}
      <div className="mb-8 flex gap-3">
        <Link
          href="/inspections?action=new"
          className="inline-flex items-center gap-2 rounded-lg bg-[var(--color-primary)] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--color-primary-hover)]"
        >
          <PlusIcon />
          New Inspection
        </Link>
      </div>

      {/* Workflow Cards */}
      <div className="grid gap-4 sm:grid-cols-2">
        {workflows.map((w) => (
          <Link
            key={w.href}
            href={w.href}
            className="group rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5 transition-all hover:border-[var(--color-border-hover)] hover:bg-[var(--color-bg-elevated)]"
          >
            <div className="mb-3 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--color-bg-elevated)] text-[var(--color-primary)] group-hover:bg-[var(--color-primary)]/10">
                <w.icon />
              </div>
              <h2 className="text-lg font-semibold">{w.title}</h2>
            </div>
            <p className="text-sm leading-relaxed text-[var(--color-text-muted)]">
              {w.description}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}

// -- Inline SVG icons (no external deps) --

function PlusIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function ClipboardIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function DocumentIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M9 12h6M9 16h6M17 21H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function UsersIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8zM23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChartIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 20V10M12 20V4M6 20v-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
