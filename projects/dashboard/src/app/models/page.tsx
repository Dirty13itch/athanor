import { ModelObservatory } from "@/features/models/model-observatory";
import { config } from "@/lib/config";

export const revalidate = 15;

export default async function ModelsPage() {
  // Maps inference backend IDs to their primary LiteLLM alias.
  // The canonical healthy shared text lane is now the Foundry dolphin runtime;
  // the legacy coordinator endpoint remains visible as degraded lineage only.
  const LITELLM_ALIAS_MAP: Record<string, string> = {
    "foundry-coordinator": "reasoning",
    "foundry-coder": "coding",
    "dev-embedding": "embedding",
    "dev-reranker": "reranker",
  };

  const localModels = config.inferenceBackends
    .filter((b) => b.id !== "litellm-proxy")
    .map((b) => ({
      alias: b.id,
      litellmAlias: LITELLM_ALIAS_MAP[b.id] ?? b.id,
      name: b.primaryModel,
      node: config.nodes.find((n) => n.id === b.nodeId)?.name ?? b.nodeId,
      nodeId: b.nodeId,
      description: b.description,
    }));

  return <ModelObservatory localModels={localModels} />;
}
