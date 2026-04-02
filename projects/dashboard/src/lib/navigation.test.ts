import { describe, expect, it } from "vitest";
import { getCompatibilityRoutes, getRouteFamiliesWithRoutes, getRouteLabel, getPrimaryRoutes } from "@/lib/navigation";

describe("navigation", () => {
  it("exposes first-class operator work routes", () => {
    const families = getRouteFamiliesWithRoutes();
    const operateRoutes = families.find((family) => family.id === "operate")?.routes ?? [];
    const hrefs = operateRoutes.map((route) => route.href);

    expect(hrefs).toContain("/ideas");
    expect(hrefs).toContain("/inbox");
    expect(hrefs).toContain("/todos");
    expect(hrefs).toContain("/backlog");
    expect(hrefs).toContain("/runs");
    expect(hrefs).not.toContain("/tasks");
    expect(hrefs).not.toContain("/goals");
    expect(hrefs).not.toContain("/notifications");
    expect(hrefs).not.toContain("/workplanner");
    expect(hrefs).not.toContain("/workforce");
    expect(getRouteLabel("/ideas")).toBe("Ideas");
    expect(getRouteLabel("/inbox")).toBe("Inbox");
    expect(getRouteLabel("/todos")).toBe("Todos");
    expect(getRouteLabel("/backlog")).toBe("Backlog");
    expect(getRouteLabel("/runs")).toBe("Runs");
  });

  it("keeps the quick-access primary set focused", () => {
    const primaryHrefs = getPrimaryRoutes().map((route) => route.href);

    expect(primaryHrefs).not.toContain("/ideas");
    expect(primaryHrefs).not.toContain("/inbox");
    expect(primaryHrefs).not.toContain("/todos");
    expect(primaryHrefs).not.toContain("/backlog");
    expect(primaryHrefs).not.toContain("/runs");
    expect(primaryHrefs).not.toContain("/tasks");
    expect(primaryHrefs).not.toContain("/workplanner");
  });

  it("exposes compatibility redirects and shells explicitly", () => {
    const compatibilityHrefs = getCompatibilityRoutes().map((route) => route.href);

    expect(compatibilityHrefs).toEqual(
      expect.arrayContaining(["/tasks", "/goals", "/notifications", "/workplanner", "/workforce"])
    );
  });
});
