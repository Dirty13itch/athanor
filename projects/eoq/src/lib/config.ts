/** EoBQ configuration - environment variables and service endpoints */

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
const workshopHost = hostEnv("ATHANOR_NODE2_HOST", "192.168.1.225");
const foundryHost = hostEnv("ATHANOR_NODE1_HOST", "192.168.1.244");

export const config = {
  /** LiteLLM proxy URL (server-side only, proxied via API routes) */
  litellmUrl: urlEnv(
    ["ATHANOR_LITELLM_URL", "LITELLM_URL"],
    `http://${vaultHost}:4000`,
  ),
  litellmKey:
    process.env.ATHANOR_LITELLM_API_KEY ||
    process.env.LITELLM_KEY ||
    process.env.OPENAI_API_KEY ||
    "",

  /** ComfyUI URL (server-side only) */
  comfyuiUrl: urlEnv(
    ["ATHANOR_COMFYUI_URL", "COMFYUI_URL"],
    `http://${workshopHost}:8188`,
  ),

  /** Qdrant URL (server-side only, for character memory retrieval) */
  qdrantUrl: urlEnv(
    ["ATHANOR_QDRANT_URL", "QDRANT_URL"],
    `http://${foundryHost}:6333`,
  ),

  /** Model to use for dialogue generation */
  dialogueModel: process.env.DIALOGUE_MODEL || "reasoning",

  /** Temperature for dialogue generation */
  dialogueTemperature: parseFloat(process.env.DIALOGUE_TEMPERATURE || "0.8"),

  /** Max tokens for dialogue response */
  dialogueMaxTokens: parseInt(process.env.DIALOGUE_MAX_TOKENS || "512"),

  /** Speaches TTS URL (FOUNDRY:8200) */
  speachesUrl: urlEnv(
    ["ATHANOR_SPEACHES_URL", "SPEACHES_URL"],
    `http://${foundryHost}:8200`,
  ),
} as const;
