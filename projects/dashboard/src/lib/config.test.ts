import { describe, expect, it } from "vitest";
import {
  config,
  getNodeNameFromInstance,
  getProjectById,
  joinUrl,
  resolveChatModel,
  resolveChatTarget,
} from "./config";

describe("config helpers", () => {
  it("joins base urls and paths safely", () => {
    expect(joinUrl("http://example.com/", "/v1/models")).toBe("http://example.com/v1/models");
    expect(joinUrl("http://example.com", "health")).toBe("http://example.com/health");
  });

  it("resolves known chat targets and rejects unknown ones", () => {
    expect(resolveChatTarget("agent-server")).not.toBeNull();
    expect(resolveChatTarget("node1-vllm")).not.toBeNull();
    expect(resolveChatTarget("missing-target")).toBeNull();
  });

  it("maps node instances back to configured names", () => {
    expect(getNodeNameFromInstance("http://192.168.1.244:9400")).toBe("Foundry");
    expect(getNodeNameFromInstance("http://192.168.1.225:9400")).toBe("Workshop");
    expect(getNodeNameFromInstance("http://192.168.1.189:9400")).toBe("DEV");
  });

  it("provides backend-aware chat model fallbacks", () => {
    expect(resolveChatModel("agent-server", undefined)).toBe("general-assistant");
    expect(resolveChatModel("litellm-proxy", "default")).toBe("reasoning");
    expect(resolveChatModel("foundry-coder", undefined)).toBe("dolphin3-r1-24b");
    expect(resolveChatModel("foundry-coordinator", "custom-model")).toBe("/models/custom-model");
  });

  it("keeps the fallback project registry aligned with active and scaffolded tenants", () => {
    expect(getProjectById("athanor")?.firstClass).toBe(true);
    expect(getProjectById("eoq")?.firstClass).toBe(true);
    expect(getProjectById("ulrich-energy")?.kind).toBe("scaffold");
  });

  it("uses registry-backed canonical front-door and launchpad URLs", () => {
    expect(config.frontDoor.canonicalUrl).toBe("https://athanor.local/");
    expect(config.frontDoor.runtimeUrl).toBe("http://dev.athanor.local:3001/");
    expect(config.externalTools.length).toBeGreaterThan(10);
    expect(config.externalTools.every((tool) => !tool.url.includes("192.168.1."))).toBe(true);
    const workshopOpenWebUi = config.externalTools.find((tool) => tool.id === "workshop_open_webui");
    expect(workshopOpenWebUi?.runtimeUrl).toBe("http://192.168.1.225:3000/");
    expect(workshopOpenWebUi?.runtimeState).toMatch(/reachable|unreachable|http_error|not_probed/);
    expect(getProjectById("eoq")?.externalUrl).toMatch(/^http:\/\/interface\.athanor\.local:3002\/?$/);
    expect(getProjectById("ulrich-energy")?.externalUrl).toMatch(/^http:\/\/interface\.athanor\.local:3003\/?$/);
    expect(getProjectById("media")?.externalUrl).toBe("http://vault.athanor.local:32400/web");
  });
});
