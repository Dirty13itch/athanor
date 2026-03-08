import Link from "next/link";

const quickActions = [
  { href: "/inspections/new", label: "New Inspection", icon: "+" },
  { href: "/reports", label: "View Reports", icon: "R" },
  { href: "/projects", label: "Projects", icon: "P" },
];

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Ulrich Energy</h1>
        <p className="text-muted-foreground">
          HERS Rating & Energy Testing
        </p>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-3 gap-3">
        {quickActions.map((action) => (
          <Link
            key={action.href}
            href={action.href}
            className="flex flex-col items-center gap-2 rounded-lg border border-border bg-card p-4 text-center transition-colors hover:bg-accent tap-highlight"
          >
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground text-lg font-bold">
              {action.icon}
            </span>
            <span className="text-sm font-medium">{action.label}</span>
          </Link>
        ))}
      </div>

      {/* Today\'s Inspections */}
      <section>
        <h2 className="mb-3 text-lg font-semibold">Today&apos;s Inspections</h2>
        <div className="rounded-lg border border-border bg-card p-6 text-center text-muted-foreground">
          No inspections scheduled for today.
        </div>
      </section>

      {/* Recent Reports */}
      <section>
        <h2 className="mb-3 text-lg font-semibold">Recent Reports</h2>
        <div className="space-y-2">
          <div className="flex items-center justify-between rounded-lg border border-border bg-card p-4">
            <div>
              <p className="font-medium">5678 Elm Ave, Plymouth</p>
              <p className="text-sm text-muted-foreground">HERS Index: 52</p>
            </div>
            <span className="rounded-full bg-success/20 px-2 py-0.5 text-xs font-medium text-success">
              Generated
            </span>
          </div>
          <div className="flex items-center justify-between rounded-lg border border-border bg-card p-4">
            <div>
              <p className="font-medium">910 Birch Lane, Eden Prairie</p>
              <p className="text-sm text-muted-foreground">HERS Index: 48</p>
            </div>
            <span className="rounded-full bg-primary/20 px-2 py-0.5 text-xs font-medium text-primary">
              Delivered
            </span>
          </div>
        </div>
      </section>
    </div>
  );
}
