import "server-only";

import { config } from "@/lib/config";

export interface ServerConfig {
  litellmApiKey: string;
  neo4j: {
    user: string;
    password: string;
  };
}

export const serverConfig: ServerConfig = {
  litellmApiKey: process.env.ATHANOR_LITELLM_API_KEY?.trim() || "",
  neo4j: {
    user: process.env.ATHANOR_NEO4J_USER?.trim() || "neo4j",
    password: process.env.ATHANOR_NEO4J_PASSWORD?.trim() || "",
  },
};

export function getNeo4jAuthHeader(): string | null {
  if (!serverConfig.neo4j.password) {
    return null;
  }

  return `Basic ${Buffer.from(
    `${serverConfig.neo4j.user}:${serverConfig.neo4j.password}`
  ).toString("base64")}`;
}

export function hasNeo4jCredentials(): boolean {
  return Boolean(serverConfig.neo4j.password);
}

export function hasLitellmApiKey(): boolean {
  return Boolean(serverConfig.litellmApiKey);
}

export function getRequiredServiceWarnings() {
  const warnings: string[] = [];

  if (!serverConfig.litellmApiKey) {
    warnings.push("ATHANOR_LITELLM_API_KEY is not set");
  }

  if (!serverConfig.neo4j.password) {
    warnings.push("ATHANOR_NEO4J_PASSWORD is not set");
  }

  if (!config.homeAssistant.url) {
    warnings.push("ATHANOR_HOME_ASSISTANT_URL is not set");
  }

  return warnings;
}
