function hostEnv(key: string, fallback: string): string {
  return process.env[key]?.trim() || fallback;
}

function urlEnv(keys: string[], fallback: string): string {
  for (const key of keys) {
    const value = process.env[key]?.trim();
    if (value) {
      return value.replace(/\/+$/, "");
    }
  }
  return fallback;
}

const vaultHost = hostEnv("ATHANOR_VAULT_HOST", "192.168.1.203");

export const config = {
  litellm: {
    url: urlEnv(
      ["ATHANOR_LITELLM_URL", "LITELLM_URL"],
      `http://${vaultHost}:4000`,
    ),
  },
  api: {
    baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "",
  },
} as const;
