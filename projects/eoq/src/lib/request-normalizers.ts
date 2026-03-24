import {
  DEFAULT_EMOTIONAL_PROFILE,
  type BreakingMethod,
  type Character,
  type ContentIntensity,
  type DialogueTurn,
  type EmotionState,
  type QueenArchetype,
  type RelationshipMemory,
  type WorldState,
} from "@/types/game";

type ParseSuccess<T> = { ok: true; data: T };
type ParseFailure = { ok: false; error: string };
type ParseResult<T> = ParseSuccess<T> | ParseFailure;

const DEFAULT_PERSONALITY: Character["personality"] = {
  dominance: 0.5,
  warmth: 0.5,
  cunning: 0.5,
  loyalty: 0.5,
  cruelty: 0.2,
  sensuality: 0.5,
  humor: 0.3,
  ambition: 0.5,
};

const DEFAULT_RELATIONSHIP: Character["relationship"] = {
  trust: 0,
  affection: 0,
  respect: 0,
  desire: 0,
  fear: 0,
  memories: [],
};

const DEFAULT_EMOTION: EmotionState = {
  primary: "guarded",
  intensity: 0.4,
};

const VALID_ARCHETYPES = new Set<QueenArchetype>([
  "warrior",
  "sorceress",
  "priestess",
  "scholar",
  "merchant",
  "innocent",
  "defiant",
  "seductress",
  "ice",
  "fire",
  "shadow",
  "sun",
]);

const VALID_BREAKING_METHODS = new Set<BreakingMethod>([
  "physical",
  "psychological",
  "magical",
  "social",
]);

const VALID_TIMES = new Set<WorldState["timeOfDay"]>([
  "dawn",
  "morning",
  "afternoon",
  "dusk",
  "evening",
  "night",
]);

type ChatRequestData = {
  character: Character;
  worldState: WorldState;
  recentHistory: DialogueTurn[];
  playerInput: string;
  /** Additional characters present in multi-queen scenes */
  otherCharacters?: Character[];
};

type ChoicesRequestData = {
  character: Character;
  worldState: WorldState;
  recentHistory: DialogueTurn[];
};

type NarrateRequestData = {
  worldState: WorldState;
  recentHistory: DialogueTurn[];
  context?: string;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asNumber(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return fallback;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((entry): entry is string => typeof entry === "string");
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function normalizeIntensity(value: unknown): ContentIntensity {
  const parsed = Math.round(asNumber(value, 3));
  if (parsed >= 5) return 5;
  if (parsed >= 4) return 4;
  if (parsed >= 3) return 3;
  if (parsed >= 2) return 2;
  return 1;
}

function normalizeArchetype(value: unknown): QueenArchetype {
  return typeof value === "string" && VALID_ARCHETYPES.has(value as QueenArchetype)
    ? (value as QueenArchetype)
    : "ice";
}

function normalizeTimeOfDay(value: unknown): WorldState["timeOfDay"] {
  return typeof value === "string" && VALID_TIMES.has(value as WorldState["timeOfDay"])
    ? (value as WorldState["timeOfDay"])
    : "night";
}

function normalizePlotFlags(value: unknown): Record<string, boolean> {
  const record = asRecord(value);
  if (!record) {
    return {};
  }

  return Object.entries(record).reduce<Record<string, boolean>>((acc, [key, flag]) => {
    if (typeof flag === "boolean") {
      acc[key] = flag;
    }
    return acc;
  }, {});
}

function normalizeRelationshipMemories(value: unknown): RelationshipMemory[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((entry) => {
      const record = asRecord(entry);
      if (!record) {
        return null;
      }

      return {
        timestamp: asNumber(record.timestamp, Date.now()),
        summary: asString(record.summary, "A moment passed without clear detail."),
        emotionalImpact: asNumber(record.emotionalImpact, 0),
      } satisfies RelationshipMemory;
    })
    .filter((entry): entry is RelationshipMemory => entry !== null);
}

function normalizeEmotion(value: unknown, fallback = DEFAULT_EMOTION): EmotionState {
  const record = asRecord(value);
  if (!record) {
    return fallback;
  }

  return {
    primary: asString(record.primary, fallback.primary),
    intensity: clamp(asNumber(record.intensity, fallback.intensity), 0, 1),
    secondary: typeof record.secondary === "string" ? record.secondary : undefined,
  };
}

function normalizeDialogueTurns(value: unknown): DialogueTurn[] {
  if (!Array.isArray(value)) {
    return [];
  }

  const turns: DialogueTurn[] = [];

  for (const entry of value) {
    const record = asRecord(entry);
    if (!record) {
      continue;
    }

    const speaker = asString(record.speaker);
    const text = asString(record.text);
    if (!speaker || !text) {
      continue;
    }

    turns.push({
      speaker,
      text,
      emotion: record.emotion ? normalizeEmotion(record.emotion) : undefined,
    });
  }

  return turns;
}

function normalizeWorldState(value: unknown): WorldState | null {
  const record = asRecord(value);
  const scene = record ? asRecord(record.currentScene) : null;
  const sceneId = scene ? asString(scene.id) : "";
  const sceneName = scene ? asString(scene.name) : "";

  if (!scene || !sceneId || !sceneName) {
    return null;
  }

  const exits: WorldState["currentScene"]["exits"] = [];
  if (Array.isArray(scene.exits)) {
    for (const entry of scene.exits) {
      const exit = asRecord(entry);
      if (!exit) {
        continue;
      }

      const label = asString(exit.label);
      const targetSceneId = asString(exit.targetSceneId);
      if (!label || !targetSceneId) {
        continue;
      }

      exits.push({
        label,
        targetSceneId,
        condition: typeof exit.condition === "string" ? exit.condition : undefined,
      });
    }
  }

  return {
    currentScene: {
      id: sceneId,
      name: sceneName,
      description: asString(scene.description, `The player stands within ${sceneName}.`),
      visualPrompt: asString(scene.visualPrompt, sceneName),
      presentCharacters: asStringArray(scene.presentCharacters),
      exits,
    },
    timeOfDay: normalizeTimeOfDay(record?.timeOfDay),
    day: Math.max(1, Math.round(asNumber(record?.day, 1))),
    plotFlags: normalizePlotFlags(record?.plotFlags),
    inventory: asStringArray(record?.inventory),
    contentIntensity: normalizeIntensity(record?.contentIntensity),
    playMode: record?.playMode === "no_mercy" ? "no_mercy" : "blissful",
    rivalryTensions: [],       // not needed by API routes
    pendingPhoneMessages: [],  // not needed by API routes
    legacyDaughters: [],       // not needed by API routes
  };
}

function normalizeCharacter(value: unknown): Character | null {
  const record = asRecord(value);
  const id = record ? asString(record.id) : "";
  const name = record ? asString(record.name) : "";

  if (!record || !id || !name) {
    return null;
  }

  const personality = asRecord(record.personality);
  const relationship = asRecord(record.relationship);
  const vulnerabilities = asRecord(record.vulnerabilities);
  const emotionalProfile = asRecord(record.emotionalProfile);

  const normalizedVulnerabilities = vulnerabilities
    ? Object.fromEntries(
        Object.entries(vulnerabilities).filter(
          ([key, entry]) =>
            VALID_BREAKING_METHODS.has(key as BreakingMethod) && typeof entry === "number",
        ),
      )
    : {};

  return {
    id,
    name,
    title: typeof record.title === "string" ? record.title : undefined,
    archetype: normalizeArchetype(record.archetype),
    resistance: clamp(asNumber(record.resistance, 50), 0, 100),
    resistanceCeiling: clamp(asNumber(record.resistanceCeiling, 100), 0, 100),
    corruption: clamp(asNumber(record.corruption, 0), 0, 100),
    awakeningFired: record.awakeningFired === true,
    vulnerabilities: normalizedVulnerabilities,
    personality: {
      dominance: clamp(asNumber(personality?.dominance, DEFAULT_PERSONALITY.dominance), 0, 1),
      warmth: clamp(asNumber(personality?.warmth, DEFAULT_PERSONALITY.warmth), 0, 1),
      cunning: clamp(asNumber(personality?.cunning, DEFAULT_PERSONALITY.cunning), 0, 1),
      loyalty: clamp(asNumber(personality?.loyalty, DEFAULT_PERSONALITY.loyalty), 0, 1),
      cruelty: clamp(asNumber(personality?.cruelty, DEFAULT_PERSONALITY.cruelty), 0, 1),
      sensuality: clamp(asNumber(personality?.sensuality, DEFAULT_PERSONALITY.sensuality), 0, 1),
      humor: clamp(asNumber(personality?.humor, DEFAULT_PERSONALITY.humor), 0, 1),
      ambition: clamp(asNumber(personality?.ambition, DEFAULT_PERSONALITY.ambition), 0, 1),
    },
    relationship: {
      trust: clamp(asNumber(relationship?.trust, DEFAULT_RELATIONSHIP.trust), -100, 100),
      affection: clamp(asNumber(relationship?.affection, DEFAULT_RELATIONSHIP.affection), -100, 100),
      respect: clamp(asNumber(relationship?.respect, DEFAULT_RELATIONSHIP.respect), -100, 100),
      desire: clamp(asNumber(relationship?.desire, DEFAULT_RELATIONSHIP.desire), 0, 100),
      fear: clamp(asNumber(relationship?.fear, DEFAULT_RELATIONSHIP.fear), 0, 100),
      memories: normalizeRelationshipMemories(relationship?.memories),
    },
    emotion: normalizeEmotion(record.emotion),
    emotionalProfile: {
      fear: clamp(asNumber(emotionalProfile?.fear, DEFAULT_EMOTIONAL_PROFILE.fear), 0, 100),
      defiance: clamp(asNumber(emotionalProfile?.defiance, DEFAULT_EMOTIONAL_PROFILE.defiance), 0, 100),
      arousal: clamp(asNumber(emotionalProfile?.arousal, DEFAULT_EMOTIONAL_PROFILE.arousal), 0, 100),
      submission: clamp(asNumber(emotionalProfile?.submission, DEFAULT_EMOTIONAL_PROFILE.submission), 0, 100),
      despair: clamp(asNumber(emotionalProfile?.despair, DEFAULT_EMOTIONAL_PROFILE.despair), 0, 100),
    },
    speechStyle: asString(record.speechStyle, "Measured and deliberate."),
    visualDescription: asString(record.visualDescription, `${name}, dark fantasy portrait.`),
    boundaries: asStringArray(record.boundaries),
    // Pass-through complex optional fields — validated by callers
    dna: typeof record.dna === "object" && record.dna !== null
      ? record.dna as import("@/types/game").SexualDNA
      : undefined,
    stripperArc: typeof record.stripperArc === "object" && record.stripperArc !== null
      ? record.stripperArc as import("@/types/game").StripperArc
      : undefined,
    currentEndingPath: typeof record.currentEndingPath === "string"
      ? record.currentEndingPath as import("@/types/game").QueenEndingType
      : undefined,
    haremRole: typeof record.haremRole === "string"
      ? record.haremRole as import("@/types/game").Character["haremRole"]
      : undefined,
  };
}

function parseJsonBody(raw: unknown): Record<string, unknown> | null {
  return asRecord(raw);
}

export function parseChatRequest(value: unknown): ParseResult<ChatRequestData> {
  const body = parseJsonBody(value);
  const character = normalizeCharacter(body?.character);
  const worldState = normalizeWorldState(body?.worldState);

  if (!character) {
    return { ok: false, error: "character.id and character.name are required." };
  }
  if (!worldState) {
    return { ok: false, error: "worldState.currentScene.id and worldState.currentScene.name are required." };
  }

  // Parse additional characters for multi-queen scenes
  const otherCharacters: Character[] = [];
  if (Array.isArray(body?.otherCharacters)) {
    for (const raw of body.otherCharacters) {
      const c = normalizeCharacter(raw);
      if (c && c.id !== character.id) otherCharacters.push(c);
    }
  }

  return {
    ok: true,
    data: {
      character,
      worldState,
      recentHistory: normalizeDialogueTurns(body?.recentHistory),
      playerInput: asString(body?.playerInput, "[The player approaches in silence.]"),
      ...(otherCharacters.length > 0 ? { otherCharacters } : {}),
    },
  };
}

export function parseChoicesRequest(value: unknown): ParseResult<ChoicesRequestData> {
  const body = parseJsonBody(value);
  const character = normalizeCharacter(body?.character);
  const worldState = normalizeWorldState(body?.worldState);

  if (!character) {
    return { ok: false, error: "character.id and character.name are required." };
  }
  if (!worldState) {
    return { ok: false, error: "worldState.currentScene.id and worldState.currentScene.name are required." };
  }

  return {
    ok: true,
    data: {
      character,
      worldState,
      recentHistory: normalizeDialogueTurns(body?.recentHistory),
    },
  };
}

export function parseNarrateRequest(value: unknown): ParseResult<NarrateRequestData> {
  const body = parseJsonBody(value);
  const worldState = normalizeWorldState(body?.worldState);

  if (!worldState) {
    return { ok: false, error: "worldState.currentScene.id and worldState.currentScene.name are required." };
  }

  return {
    ok: true,
    data: {
      worldState,
      recentHistory: normalizeDialogueTurns(body?.recentHistory),
      context: typeof body?.context === "string" ? body.context : undefined,
    },
  };
}
