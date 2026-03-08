const mockProjects = [
  {
    id: "proj-001",
    name: "Oak Street New Construction",
    client: "Lennar Homes",
    address: "Maple Grove, MN",
    inspections: 1,
    status: "active",
  },
  {
    id: "proj-002",
    name: "Elm Ave Townhome Phase 2",
    client: "Pulte Homes",
    address: "Plymouth, MN",
    inspections: 3,
    status: "active",
  },
];

export default function ProjectsPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Projects</h1>
          <p className="text-muted-foreground">Clients and project tracking</p>
        </div>
        <button className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90">
          New Project
        </button>
      </div>

      <div className="space-y-2">
        {mockProjects.map((project) => (
          <div
            key={project.id}
            className="rounded-lg border border-border bg-card p-4 tap-highlight"
          >
            <div className="flex items-center justify-between">
              <p className="font-medium">{project.name}</p>
              <span className="rounded-full bg-success/20 px-2 py-0.5 text-xs font-medium text-success">
                {project.status}
              </span>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              {project.client} &middot; {project.address} &middot; {project.inspections} inspection{project.inspections !== 1 ? "s" : ""}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
