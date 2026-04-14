import { describe, expect, it } from "vitest";
import { config } from "./config";
import { getOverviewSnapshot } from "./dashboard-data";
import {
  getFixtureGpuSnapshot,
  getFixtureModelsSnapshot,
  getFixtureOverviewSnapshot,
  getFixtureServicesSnapshot,
  getFixtureWorkforceSnapshot,
} from "./dashboard-fixtures";

describe("dashboard fixtures", () => {
  it("keeps fixture services aligned with the canonical dashboard service registry", () => {
    const fixtureIds = getFixtureServicesSnapshot().services.map((service) => service.id);
    expect(fixtureIds).toEqual(config.services.map((service) => service.id));
    expect(fixtureIds).toContain("foundry-coder");
    expect(fixtureIds).toContain("dev-embedding");
    expect(fixtureIds).toContain("dev-reranker");
  });

  it("exposes shared health contract details for core services in fixture mode", () => {
    const fixture = getFixtureServicesSnapshot();
    const byId = new Map(fixture.services.map((service) => [service.id, service]));

    const agentServer = byId.get("agent-server");
    expect(agentServer?.authClass).toBe("admin");
    expect(agentServer?.actionsAllowed).toContain("tasks.approve");
    expect(agentServer?.dependencies?.some((dependency) => dependency.id === "redis")).toBe(true);
    expect(agentServer?.healthSnapshot?.service).toBe("agent-server");

    const litellm = byId.get("litellm-proxy");
    expect(litellm?.authClass).toBe("operator");
    expect(litellm?.healthSnapshot?.dependencies.length).toBeGreaterThan(0);
  });

  it("keeps warning and degraded service counts aligned with fixture state", () => {
    const services = getFixtureServicesSnapshot();
    const overview = getFixtureOverviewSnapshot();

    expect(services.summary.warning).toBe(0);
    expect(services.summary.degraded).toBe(2);
    expect(overview.summary.warningServices).toBe(0);
    expect(overview.summary.degradedServices).toBe(2);
  });

  it("keeps fixture node summaries aligned with per-service state counts", () => {
    const services = getFixtureServicesSnapshot();
    const overview = getFixtureOverviewSnapshot();

    for (const node of overview.nodes) {
      const nodeServices = services.services.filter((service) => service.nodeId === node.id);
      expect(node.totalServices).toBe(nodeServices.length);
      expect(node.healthyServices).toBe(nodeServices.filter((service) => service.state === "healthy").length);
      expect(node.warningServices).toBe(nodeServices.filter((service) => service.state === "warning").length);
      expect(node.degradedServices).toBe(
        nodeServices.filter((service) => !["healthy", "warning"].includes(service.state)).length
      );
    }
  });

  it("keeps fixture inference backends aligned with the frozen slot map", () => {
    const fixture = getFixtureModelsSnapshot();
    expect(fixture.backends.map((backend) => backend.id)).toEqual(
      config.inferenceBackends.map((backend) => backend.id)
    );
    for (const backend of fixture.backends) {
      expect(fixture.models.some((model) => model.backendId === backend.id)).toBe(true);
    }
  });

  it("keeps projects, roster, and DEV coverage aligned across fixture mode", () => {
    const overview = getFixtureOverviewSnapshot();
    const workforce = getFixtureWorkforceSnapshot();
    const gpu = getFixtureGpuSnapshot();

    expect(overview.projects.map((project) => project.id)).toEqual(
      config.projectRegistry.map((project) => project.id)
    );
    expect(workforce.projects.map((project) => project.id)).toEqual(
      config.projectRegistry.map((project) => project.id)
    );
    expect(workforce.agents.map((agent) => agent.id)).toEqual([
      "general-assistant",
      "media-agent",
      "home-agent",
      "creative-agent",
      "research-agent",
      "knowledge-agent",
      "coding-agent",
      "stash-agent",
      "data-curator",
    ]);
    expect(overview.nodes.some((node) => node.id === "dev")).toBe(true);
    expect(gpu.nodes.some((node) => node.nodeId === "dev")).toBe(true);
  });

  it("keeps fixture launch surfaces aligned with the canonical front door", () => {
    const overview = getFixtureOverviewSnapshot();

    expect(config.frontDoor.label).toBe("Athanor Command Center");
    expect(config.frontDoor.canonicalUrl).toBe("https://athanor.local/");
    expect(config.frontDoor.runtimeUrl).toBe("http://dev.athanor.local:3001/");
    expect(overview.externalTools).toEqual(config.externalTools);
    expect(overview.externalTools.every((tool) => !tool.url.includes("192.168.1."))).toBe(true);
    expect(overview.externalTools.some((tool) => tool.id === "grafana")).toBe(true);
    expect(overview.externalTools.some((tool) => tool.id === "eoq")).toBe(true);
  });

  it("serves command-center overview data from fixture mode without proxy-only routes", async () => {
    const env = process.env as Record<string, string | undefined>;
    const previousFixtureMode = env.DASHBOARD_FIXTURE_MODE;
    env.DASHBOARD_FIXTURE_MODE = "1";

    try {
      const overview = await getOverviewSnapshot();
      const services = getFixtureServicesSnapshot();

      expect(overview.summary.totalServices).toBe(services.summary.total);
      expect(overview.summary.warningServices).toBe(services.summary.warning);
      expect(overview.summary.degradedServices).toBe(services.summary.degraded);
      expect(overview.alerts.map((alert) => alert.id)).toEqual(
        expect.arrayContaining(["speaches-outage", "gpu-hotspot"])
      );
      expect(overview.projects.map((project) => project.id)).toEqual(
        config.projectRegistry.map((project) => project.id)
      );
      expect(overview.externalTools).toEqual(config.externalTools);
    } finally {
      if (previousFixtureMode === undefined) {
        delete env.DASHBOARD_FIXTURE_MODE;
      } else {
        env.DASHBOARD_FIXTURE_MODE = previousFixtureMode;
      }
    }
  });
});
