export function buildChatUpstreamHeaders(
  target: string | undefined,
  litellmApiKey: string
): { headers: Record<string, string>; error?: string } {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (target === "litellm-proxy") {
    if (!litellmApiKey) {
      return {
        headers,
        error: "ATHANOR_LITELLM_API_KEY is required for LiteLLM chat target",
      };
    }

    headers.Authorization = `Bearer ${litellmApiKey}`;
  }

  return { headers };
}
