"use client";

import Link from "next/link";
import { useApiData } from "@/hooks/use-api-data";
import type { Project } from "@/types/project";

export default function ProjectsPage() {
  const { data, loading, error } = useApiData<{ projects: Project[] }>("/api/projects", {
    projects: [],
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Projects</h1>
          <p className="text-muted-foreground">Clients and project tracking</p>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
          Loading projects...
        </div>
      ) : (
        <div className="space-y-2">
          {data.projects.map((project) => (
            <Link
              key={project.id}
              href={`/inspections?projectId=${project.id}`}
              className="block rounded-lg border border-border bg-card p-4 transition-colors hover:bg-accent tap-highlight"
            >
              <div className="flex items-center justify-between">
                <p className="font-medium">{project.name}</p>
                <span className="rounded-full bg-success/20 px-2 py-0.5 text-xs font-medium text-success">
                  {project.status}
                </span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                {project.client?.name ?? "No client"} · {project.address.city}, {project.address.state} · {project.inspectionCount} inspection{project.inspectionCount !== 1 ? "s" : ""}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
