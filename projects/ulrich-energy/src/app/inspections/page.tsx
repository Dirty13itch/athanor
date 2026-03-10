import { Suspense } from "react";
import { InspectionsPageClient } from "./page-client";

export default function InspectionsPage() {
  return (
    <Suspense
      fallback={
        <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
          Loading inspections...
        </div>
      }
    >
      <InspectionsPageClient />
    </Suspense>
  );
}
