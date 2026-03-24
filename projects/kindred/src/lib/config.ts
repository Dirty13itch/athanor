/** Kindred configuration — service endpoints */

const vaultHost = process.env.ATHANOR_VAULT_HOST ?? "192.168.1.203";
const devHost = process.env.ATHANOR_DEV_HOST ?? "192.168.1.189";

export const config = {
  litellmUrl: process.env.LITELLM_URL ?? `http://${vaultHost}:4000`,
  litellmKey: process.env.LITELLM_KEY ?? process.env.OPENAI_API_KEY ?? "",
  embeddingUrl: `http://${devHost}:8001`,
  qdrantUrl: process.env.QDRANT_URL ?? `http://${process.env.ATHANOR_NODE1_HOST ?? "192.168.1.244"}:6333`,
} as const;
