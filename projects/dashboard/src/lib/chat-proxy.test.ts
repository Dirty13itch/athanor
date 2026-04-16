import { describe, expect, it } from "vitest";
import { buildChatUpstreamHeaders } from "./chat-proxy";

describe("buildChatUpstreamHeaders", () => {
  it("adds LiteLLM auth when routing through the proxy", () => {
    const result = buildChatUpstreamHeaders("litellm-proxy", "secret-key");

    expect(result.error).toBeUndefined();
    expect(result.headers.Authorization).toBe("Bearer secret-key");
  });

  it("fails fast when LiteLLM auth is missing", () => {
    const result = buildChatUpstreamHeaders("litellm-proxy", "");

    expect(result.error).toContain("ATHANOR_LITELLM_API_KEY");
    expect(result.headers.Authorization).toBeUndefined();
  });

  it("keeps direct backend requests unauthenticated", () => {
    const result = buildChatUpstreamHeaders("foundry-coder", "");

    expect(result.error).toBeUndefined();
    expect(result.headers).toEqual({ "Content-Type": "application/json" });
  });
});
