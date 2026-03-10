import { describe, expect, it } from "vitest";
import { getNodeNameFromInstance, joinUrl, resolveChatTarget } from "./config";

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
});
