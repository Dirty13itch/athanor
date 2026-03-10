"use client";

import { useRouter } from "next/navigation";
import { startTransition, useState } from "react";

export default function NewInspectionPage() {
  const router = useRouter();
  const [address, setAddress] = useState("");
  const [builder, setBuilder] = useState("");
  const [inspector, setInspector] = useState("Shaun");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch("/api/inspections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address, builder, inspector }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.inspection?.id) {
        throw new Error(payload.error ?? `HTTP ${response.status}`);
      }
      startTransition(() => {
        router.push(`/inspections/${payload.inspection.id}`);
      });
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to create inspection");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">New Inspection</h1>
        <p className="text-muted-foreground">Create a new inspection job</p>
      </div>

      <form className="space-y-4" onSubmit={(event) => void handleSubmit(event)}>
        <div className="space-y-2">
          <label htmlFor="address" className="text-sm font-medium">Property Address</label>
          <input
            id="address"
            type="text"
            value={address}
            onChange={(event) => setAddress(event.target.value)}
            placeholder="1234 Main Street, City, MN 55XXX"
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="builder" className="text-sm font-medium">Builder</label>
          <input
            id="builder"
            type="text"
            value={builder}
            onChange={(event) => setBuilder(event.target.value)}
            placeholder="Builder name"
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label htmlFor="propertyType" className="text-sm font-medium">Property Type</label>
            <select
              id="propertyType"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              defaultValue="single_family"
            >
              <option value="single_family">Single Family</option>
              <option value="townhome">Townhome</option>
              <option value="duplex">Duplex</option>
              <option value="multifamily">Multifamily</option>
            </select>
          </div>
          <div className="space-y-2">
            <label htmlFor="inspector" className="text-sm font-medium">Inspector</label>
            <input
              id="inspector"
              type="text"
              value={inspector}
              onChange={(event) => setInspector(event.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <hr className="border-border" />

        <h2 className="text-lg font-semibold">Test Sections</h2>
        <p className="text-sm text-muted-foreground">These sections will be available after creating the inspection.</p>

        <div className="grid grid-cols-2 gap-3">
          {["Blower Door", "Duct Leakage", "Insulation", "Windows", "HVAC", "Building Envelope"].map((section) => (
            <div key={section} className="rounded-lg border border-border bg-card p-3 text-center text-sm text-muted-foreground">
              {section}
            </div>
          ))}
        </div>

        <button
          type="submit"
          disabled={submitting || !address.trim() || !builder.trim()}
          className="w-full rounded-md bg-primary px-4 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-60"
        >
          {submitting ? "Creating..." : "Create Inspection"}
        </button>
      </form>
    </div>
  );
}
