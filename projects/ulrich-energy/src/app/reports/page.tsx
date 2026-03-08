const statusColors: Record<string, string> = {
  draft: "bg-muted-foreground/20 text-muted-foreground",
  generated: "bg-success/20 text-success",
  reviewed: "bg-warning/20 text-warning",
  delivered: "bg-primary/20 text-primary",
};

const mockReports = [
  { id: "rpt-001", address: "5678 Elm Ave, Plymouth", hers: 52, status: "generated", date: "Mar 5" },
  { id: "rpt-002", address: "910 Birch Lane, Eden Prairie", hers: 48, status: "delivered", date: "Mar 1" },
];

export default function ReportsPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Reports</h1>
        <p className="text-muted-foreground">Generated HERS rating reports</p>
      </div>

      <div className="space-y-2">
        {mockReports.map((report) => (
          <div
            key={report.id}
            className="flex items-center justify-between rounded-lg border border-border bg-card p-4"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{report.address}</p>
              <p className="text-sm text-muted-foreground">
                HERS Index: {report.hers} &middot; {report.date}
              </p>
            </div>
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[report.status]}`}>
              {report.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
