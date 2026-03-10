import { describe, expect, it } from "vitest";
import { config } from "./config";
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
    expect(fixtureIds).toContain("foundry-coordinator");
    expect(fixtureIds).toContain("foundry-utility");
    expect(fixtureIds).toContain("workshop-worker");
    expect(fixtureIds).toContain("dev-embedding");
    expect(fixtureIds).toContain("dev-reranker");
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
});
