import { render } from "@testing-library/react";
import { axe } from "jest-axe";
import { AlertTriangle, Bot } from "lucide-react";
import { describe, expect, it } from "vitest";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";

describe("shared UI accessibility", () => {
  it("renders an accessible empty state", async () => {
    const { container } = render(
      <EmptyState
        title="No sessions yet"
        description="Create a new session to begin testing a model or agent workflow."
        icon={<Bot className="h-5 w-5" />}
        action={<Button>New session</Button>}
      />
    );

    expect(await axe(container)).toHaveNoViolations();
  });

  it("renders an accessible error panel", async () => {
    const { container } = render(
      <ErrorPanel
        title="Service history unavailable"
        description="Prometheus did not return the expected blackbox metrics for the selected window."
      />
    );

    expect(await axe(container)).toHaveNoViolations();
  });

  it("renders an accessible page header", async () => {
    const { container } = render(
      <PageHeader
        eyebrow="Operations"
        title="Command Center"
        description="Cluster posture, incidents, trends, and launch points for the core operator workflows."
        actions={<Button variant="outline">Open incidents</Button>}
      >
        <div className="rounded-2xl border border-border/70 bg-card/70 p-4">
          <AlertTriangle className="h-4 w-4 text-primary" />
        </div>
      </PageHeader>
    );

    expect(await axe(container)).toHaveNoViolations();
  });
});
