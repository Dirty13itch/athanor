"use client";

import { useApiData } from "@/hooks/use-api-data";
import type { Client } from "@/types";

export default function ClientsPage() {
  const { data, loading, error } = useApiData<{ data: Client[] }>("/api/clients", { data: [] });

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Clients</h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            Builders and homeowner contacts
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-6 text-sm text-[var(--color-text-muted)]">
          Loading clients...
        </div>
      ) : data.data.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] py-16">
          <p className="mb-2 text-[var(--color-text-muted)]">No clients yet</p>
          <p className="text-sm text-[var(--color-text-muted)]">
            Add builders and homeowners to track relationships.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {data.data.map((client) => (
            <div key={client.id} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-card)] p-4">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="font-medium">{client.name}</p>
                  <p className="text-sm text-[var(--color-text-muted)]">
                    {client.company ?? "Independent"} · {client.email ?? "No email"}
                  </p>
                </div>
                <p className="text-sm text-[var(--color-text-muted)]">{client.phone ?? "No phone"}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
