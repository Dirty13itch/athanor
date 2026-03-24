/**
 * Client-side API for persistent character memory via Qdrant.
 *
 * All vector operations happen server-side through API routes.
 * This module provides typed convenience wrappers for the game engine.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type MemoryType =
  | "interaction"
  | "choice"
  | "revelation"
  | "combat"
  | "relationship_change";

export interface CharacterMemory {
  id: string;
  characterId: string;
  sessionId: string;
  content: string;
  importance: 1 | 2 | 3 | 4 | 5;
  memoryType: MemoryType;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

export interface RetrievedMemory {
  text: string;
  timestamp: number;
  /** Raw vector similarity score (0-1) */
  score: number;
  /** Score adjusted for recency decay */
  adjustedScore: number;
  importance: number;
  memoryType: string;
  metadata: Record<string, unknown>;
}

export interface RelationshipSummary {
  characterId: string;
  totalInteractions: number;
  averageImportance: number;
  /** Weighted sentiment from recent memories (-1 to 1) */
  sentiment: number;
  /** Time-decayed relationship strength (0-1) */
  strength: number;
  topMemoryTypes: Record<string, number>;
}

// ---------------------------------------------------------------------------
// Memory storage (fire-and-forget safe)
// ---------------------------------------------------------------------------

/**
 * Store a memory about a character interaction.
 * Non-blocking by design -- call without await for fire-and-forget.
 */
export async function storeMemory(
  characterId: string,
  sessionId: string,
  content: string,
  importance: 1 | 2 | 3 | 4 | 5,
  memoryType: MemoryType,
  metadata?: Record<string, unknown>,
): Promise<{ id: string } | null> {
  try {
    const resp = await fetch("/api/memory", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        characterId,
        sessionId,
        content,
        importance,
        memoryType,
        metadata,
      }),
    });

    if (!resp.ok) return null;
    return resp.json();
  } catch {
    // Memory storage is best-effort -- never block gameplay
    return null;
  }
}

// ---------------------------------------------------------------------------
// Memory retrieval
// ---------------------------------------------------------------------------

/**
 * Retrieve relevant memories for a character, ranked by
 * `relevance * recency_weight` where recency decays over days.
 */
export async function retrieveMemories(
  characterId: string,
  query: string,
  limit = 5,
): Promise<RetrievedMemory[]> {
  try {
    const params = new URLSearchParams({
      query,
      limit: String(limit),
    });

    const resp = await fetch(`/api/memory/${encodeURIComponent(characterId)}?${params}`);
    if (!resp.ok) return [];

    const data: { memories: RetrievedMemory[] } = await resp.json();
    return data.memories ?? [];
  } catch {
    return [];
  }
}

// ---------------------------------------------------------------------------
// Relationship scoring
// ---------------------------------------------------------------------------

/**
 * Compute a relationship score for a character from their stored memories.
 * Returns a summary with interaction counts, sentiment, and strength.
 */
export async function getRelationshipScore(
  characterId: string,
): Promise<RelationshipSummary | null> {
  try {
    const params = new URLSearchParams({ summary: "1" });
    const resp = await fetch(`/api/memory/${encodeURIComponent(characterId)}?${params}`);
    if (!resp.ok) return null;

    const data: { summary: RelationshipSummary } = await resp.json();
    return data.summary ?? null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Convenience helpers for the game engine
// ---------------------------------------------------------------------------

/**
 * Store a player choice as a memory for all present characters.
 * Computes importance from the total stat impact of the choice effects.
 */
export function storeChoiceMemory(
  characterIds: string[],
  sessionId: string,
  choiceText: string,
  intent: string,
  sceneName: string,
  totalImpact: number,
  breakingMethod?: string,
): void {
  const importance = impactToImportance(totalImpact);
  const content = `Player chose: "${choiceText}" (intent: ${intent}) in ${sceneName}`;
  const metadata: Record<string, unknown> = {
    intent,
    scene: sceneName,
  };
  if (breakingMethod) {
    metadata.breaking_method = breakingMethod;
  }

  for (const charId of characterIds) {
    // Fire and forget -- no await
    storeMemory(charId, sessionId, content, importance, "choice", metadata);
  }
}

/**
 * Store a scene transition / narrative event as a memory.
 */
export function storeSceneMemory(
  characterIds: string[],
  sessionId: string,
  sceneName: string,
  description: string,
): void {
  const content = `Scene transition to ${sceneName}: ${description}`;
  for (const charId of characterIds) {
    storeMemory(charId, sessionId, content, 2, "interaction", { scene: sceneName });
  }
}

/**
 * Store a revelation or significant plot event.
 */
export function storeRevelation(
  characterIds: string[],
  sessionId: string,
  revelation: string,
  sceneName: string,
): void {
  for (const charId of characterIds) {
    storeMemory(charId, sessionId, revelation, 4, "revelation", { scene: sceneName });
  }
}

/**
 * Format retrieved memories for injection into an LLM prompt.
 */
export function formatMemoriesForPrompt(memories: RetrievedMemory[]): string {
  if (memories.length === 0) return "";

  const lines = memories.map((m) => {
    const age = timeSince(m.timestamp);
    const typeLabel = m.memoryType ? ` [${m.memoryType}]` : "";
    return `- [${age} ago${typeLabel}] ${m.text}`;
  });

  return `LONG-TERM MEMORIES (from past sessions):\n${lines.join("\n")}`;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function impactToImportance(totalImpact: number): 1 | 2 | 3 | 4 | 5 {
  if (totalImpact >= 30) return 5;
  if (totalImpact >= 20) return 4;
  if (totalImpact >= 10) return 3;
  if (totalImpact >= 5) return 2;
  return 1;
}

function timeSince(timestamp: number): string {
  const diffMs = Date.now() - timestamp;
  const minutes = Math.floor(diffMs / 60_000);
  const hours = Math.floor(diffMs / 3_600_000);
  const days = Math.floor(diffMs / 86_400_000);

  if (days > 0) return `${days}d`;
  if (hours > 0) return `${hours}h`;
  if (minutes > 0) return `${minutes}m`;
  return "just now";
}
