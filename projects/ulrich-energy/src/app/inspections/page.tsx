import Link from "next/link";

const statusColors: Record<string, string> = {
  draft: "bg-muted-foreground/20 text-muted-foreground",
  submitted: "bg-warning/20 text-warning",
  reported: "bg-success/20 text-success",
  delivered: "bg-primary/20 text-primary",
};

const mockInspections = [
  { id: "insp-001", address: "1234 Oak Street, Maple Grove", builder: "Lennar Homes", status: "draft", date: "Mar 7" },
  { id: "insp-002", address: "5678 Elm Ave, Plymouth", builder: "Pulte Homes", status: "reported", date: "Mar 5", hers: 52 },
  { id: "insp-003", address: "910 Birch Lane, Eden Prairie", builder: "David Weekley", status: "delivered", date: "Mar 1", hers: 48 },
];

export default function InspectionsPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Inspections</h1>
          <p className="text-muted-foreground">All inspection jobs</p>
        </div>
        <Link
          href="/inspections/new"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          New
        </Link>
      </div>

      <div className="space-y-2">
        {mockInspections.map((insp) => (
          <Link
            key={insp.id}
            href={`/inspections/${insp.id}`}
            className="flex items-center justify-between rounded-lg border border-border bg-card p-4 transition-colors hover:bg-accent tap-highlight"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{insp.address}</p>
              <p className="text-sm text-muted-foreground">{insp.builder} &middot; {insp.date}</p>
            </div>
            <div className="ml-3 flex items-center gap-2">
              {insp.hers !== undefined && (
                <span className="text-sm font-mono font-medium">{insp.hers}</span>
              )}
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[insp.status]}`}>
                {insp.status}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
