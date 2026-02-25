/** Core game types for Empire of Broken Queens */

export interface Character {
  id: string;
  name: string;
  /** Fixed personality traits — never change during gameplay */
  personality: PersonalityVector;
  /** Mutable relationship with the player */
  relationship: RelationshipState;
  /** Current emotional state — changes per interaction */
  emotion: EmotionState;
  /** Character-specific speech patterns and vocabulary */
  speechStyle: string;
  /** Visual reference for portrait generation */
  visualDescription: string;
  /** What this character will and won't do */
  boundaries: string[];
}

export interface PersonalityVector {
  /** 0-1 scales for core traits */
  dominance: number;
  warmth: number;
  cunning: number;
  loyalty: number;
  cruelty: number;
  sensuality: number;
  humor: number;
  ambition: number;
}

export interface RelationshipState {
  trust: number;       // -100 to 100
  affection: number;   // -100 to 100
  respect: number;     // -100 to 100
  desire: number;      // 0 to 100
  fear: number;        // 0 to 100
  /** Key relationship events */
  memories: RelationshipMemory[];
}

export interface RelationshipMemory {
  timestamp: number;
  summary: string;
  emotionalImpact: number;  // -10 to 10
}

export interface EmotionState {
  primary: string;     // "calm" | "angry" | "aroused" | "fearful" | "joyful" | etc.
  intensity: number;   // 0-1
  secondary?: string;
}

export interface WorldState {
  currentScene: SceneDefinition;
  timeOfDay: "dawn" | "morning" | "afternoon" | "dusk" | "evening" | "night";
  day: number;
  plotFlags: Record<string, boolean>;
  inventory: string[];
}

export interface SceneDefinition {
  id: string;
  name: string;
  description: string;
  /** Visual prompt fragment for ComfyUI scene generation */
  visualPrompt: string;
  /** Characters present in this scene */
  presentCharacters: string[];
  /** Available actions/exits */
  exits: SceneExit[];
}

export interface SceneExit {
  label: string;
  targetSceneId: string;
  condition?: string;
}

export interface DialogueTurn {
  speaker: string;      // character id or "narrator" or "player"
  text: string;
  emotion?: EmotionState;
  /** Choices offered to the player after this line */
  choices?: PlayerChoice[];
}

export interface PlayerChoice {
  text: string;
  /** What this choice signals about player intent */
  intent: string;
  /** Effects on relationship/world state */
  effects?: Partial<{
    trust: number;
    affection: number;
    respect: number;
    desire: number;
    fear: number;
    plotFlags: Record<string, boolean>;
  }>;
}

export interface GameSession {
  id: string;
  startedAt: number;
  lastPlayedAt: number;
  worldState: WorldState;
  characters: Record<string, Character>;
  dialogueHistory: DialogueTurn[];
  /** Position in the current narrative arc */
  arcPosition: string;
}

/** Configuration for the LLM dialogue generation pipeline */
export interface DialogueConfig {
  /** LiteLLM model alias */
  model: string;
  /** Max tokens for dialogue response */
  maxTokens: number;
  /** Temperature for generation (lower = more deterministic) */
  temperature: number;
  /** Whether to stream tokens */
  stream: boolean;
}
