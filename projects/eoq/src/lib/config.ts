/** EoBQ configuration — environment variables and service endpoints */

export const config = {
  /** LiteLLM proxy URL (server-side only, proxied via API routes) */
  litellmUrl: process.env.LITELLM_URL || "http://192.168.1.203:4000",
  litellmKey: process.env.LITELLM_KEY || "sk-athanor-litellm-2026",

  /** ComfyUI URL (server-side only) */
  comfyuiUrl: process.env.COMFYUI_URL || "http://192.168.1.225:8188",

  /** Qdrant URL (server-side only, for character memory retrieval) */
  qdrantUrl: process.env.QDRANT_URL || "http://192.168.1.244:6333",

  /** Model to use for dialogue generation */
  dialogueModel: process.env.DIALOGUE_MODEL || "reasoning",

  /** Temperature for dialogue generation */
  dialogueTemperature: parseFloat(process.env.DIALOGUE_TEMPERATURE || "0.8"),

  /** Max tokens for dialogue response */
  dialogueMaxTokens: parseInt(process.env.DIALOGUE_MAX_TOKENS || "512"),
} as const;
