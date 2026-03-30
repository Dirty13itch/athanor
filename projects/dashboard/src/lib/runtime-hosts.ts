import { config } from "@/lib/config";

function firstEnv(names: string[]): string | null {
  for (const name of names) {
    const value = process.env[name]?.trim();
    if (value) {
      return value.replace(/\/+$/, "");
    }
  }

  return null;
}

function nodeIp(nodeId: string): string {
  return config.nodes.find((node) => node.id === nodeId)?.ip ?? "";
}

function nodeBaseUrl(nodeId: string, port: number): string {
  return `http://${nodeIp(nodeId)}:${port}`;
}

export function getSentinelBaseUrl(): string {
  return firstEnv(["ATHANOR_SENTINEL_URL"]) ?? nodeBaseUrl("dev", 8770);
}

export function getBrainAdvisorBaseUrl(): string {
  return firstEnv(["ATHANOR_BRAIN_ADVISOR_URL", "ATHANOR_BRAIN_URL"]) ?? nodeBaseUrl("dev", 8780);
}

export function getQualityGateBaseUrl(): string {
  return firstEnv(["ATHANOR_QUALITY_GATE_URL"]) ?? nodeBaseUrl("dev", 8790);
}

export function getWhisperBaseUrl(): string {
  return firstEnv(["ATHANOR_STT_URL", "ATHANOR_WHISPER_URL"]) ?? nodeBaseUrl("node1", 10300);
}

export function getTerminalBridgeBaseUrl(): string {
  return firstEnv(["ATHANOR_WS_PTY_BRIDGE_URL", "NEXT_PUBLIC_WS_PTY_BRIDGE_URL"]) ?? nodeBaseUrl("node2", 3100);
}

export function getWorkshopDockerProxyUrl(): string | null {
  return firstEnv(["ATHANOR_WORKSHOP_DOCKER_PROXY", "ATHANOR_NODE2_DOCKER_PROXY"]);
}

export function getFoundryDockerProxyUrl(): string {
  return firstEnv(["ATHANOR_FOUNDRY_DOCKER_PROXY"]) ?? nodeBaseUrl("node1", 2375);
}

export function getVaultDockerProxyUrl(): string {
  return firstEnv(["ATHANOR_VAULT_DOCKER_PROXY"]) ?? nodeBaseUrl("vault", 2375);
}
