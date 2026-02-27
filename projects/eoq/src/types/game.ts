/** Core game types for Empire of Broken Queens */

// ---------------------------------------------------------------------------
// Breaking System (from GDD)
// ---------------------------------------------------------------------------

/**
 * Breaking stage — derived from resistance level.
 * As resistance drops, the character progresses through these stages.
 * Players can choose NOT to break characters, pursuing trust/respect instead.
 */
export type BreakingStage =
  | "defiant"     // resistance 80-100 — hostile, unyielding
  | "struggling"  // resistance 60-79  — cracks showing, moments of doubt
  | "conflicted"  // resistance 40-59  — torn between resistance and submission
  | "yielding"    // resistance 20-39  — resistance fading, compliance emerging
  | "surrendered" // resistance 1-19   — broken will, seeks approval
  | "broken";     // resistance 0      — total submission

/** Derive breaking stage from resistance value */
export function getBreakingStage(resistance: number): BreakingStage {
  if (resistance >= 80) return "defiant";
  if (resistance >= 60) return "struggling";
  if (resistance >= 40) return "conflicted";
  if (resistance >= 20) return "yielding";
  if (resistance >= 1) return "surrendered";
  return "broken";
}

/**
 * Queen archetype — informs personality, breaking path, and dialogue style.
 * From the GDD's 12 archetypes.
 */
export type QueenArchetype =
  | "warrior"    // fights physically, high resistance, respects strength
  | "sorceress"  // magical power, cunning, dangerous when cornered
  | "priestess"  // faith-driven, moral authority, guilt as weapon
  | "scholar"    // intellectual, detached, curiosity as weakness
  | "merchant"   // pragmatic, transactional, can be bought
  | "innocent"   // naive, easily manipulated, guilt-inducing
  | "defiant"    // pure willpower, breaks hard but breaks completely
  | "seductress" // uses desire as a weapon, high arousal threshold
  | "ice"        // emotionally closed, cold, requires patience
  | "fire"       // passionate, volatile, burns hot in all directions
  | "shadow"     // secretive, paranoid, trust is the key
  | "sun";       // charismatic, beloved, isolation breaks them

/** Breaking method categories — each character has different vulnerabilities */
export type BreakingMethod = "physical" | "psychological" | "magical" | "social";

/** Content intensity level (1-5), controls explicit content thresholds */
export type ContentIntensity = 1 | 2 | 3 | 4 | 5;

// ---------------------------------------------------------------------------
// Emotional System (from Dialogue System Design)
// ---------------------------------------------------------------------------

/**
 * Rich emotional profile — 5 axes that shift during interactions.
 * More nuanced than the simple EmotionState. These drive
 * dialogue branching and breakthrough events.
 */
export interface EmotionalProfile {
  fear: number;       // 0-100 — terror, anxiety, dread
  defiance: number;   // 0-100 — resistance, anger, pride
  arousal: number;    // 0-100 — desire, physical response
  submission: number; // 0-100 — compliance, obedience
  despair: number;    // 0-100 — hopelessness, grief
}

/** Default emotional profile for new characters */
export const DEFAULT_EMOTIONAL_PROFILE: EmotionalProfile = {
  fear: 10,
  defiance: 70,
  arousal: 0,
  submission: 0,
  despair: 5,
};

// ---------------------------------------------------------------------------
// Character System
// ---------------------------------------------------------------------------

export interface Character {
  id: string;
  name: string;
  /** Fixed personality traits — never change during gameplay */
  personality: PersonalityVector;
  /** Mutable relationship with the player */
  relationship: RelationshipState;
  /** Current emotional state — simple label for display and LLM prompting */
  emotion: EmotionState;
  /** Rich emotional profile — drives dialogue branching and breakthroughs */
  emotionalProfile: EmotionalProfile;
  /** Character-specific speech patterns and vocabulary */
  speechStyle: string;
  /** Visual reference for portrait generation */
  visualDescription: string;
  /** What this character will and won't do */
  boundaries: string[];
  /** Queen archetype — informs personality and breaking path */
  archetype: QueenArchetype;
  /** Resistance to the player's influence (0-100, starts high) */
  resistance: number;
  /** Corruption level (0-100, starts low) */
  corruption: number;
  /** What breaking methods are most/least effective (-1 to 1 scale) */
  vulnerabilities: Partial<Record<BreakingMethod, number>>;
  /** Title or role for display */
  title?: string;
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

// ---------------------------------------------------------------------------
// World State
// ---------------------------------------------------------------------------

export interface WorldState {
  currentScene: SceneDefinition;
  timeOfDay: "dawn" | "morning" | "afternoon" | "dusk" | "evening" | "night";
  day: number;
  plotFlags: Record<string, boolean>;
  inventory: string[];
  /** Current content intensity ceiling (player-configurable) */
  contentIntensity: ContentIntensity;
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

// ---------------------------------------------------------------------------
// Dialogue System
// ---------------------------------------------------------------------------

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
  /** Which breaking method this choice represents (if any) */
  breakingMethod?: BreakingMethod;
  /** Effects on relationship/world state */
  effects?: ChoiceEffects;
}

export interface ChoiceEffects {
  trust?: number;
  affection?: number;
  respect?: number;
  desire?: number;
  fear?: number;
  /** Direct resistance change (negative = weaken resistance) */
  resistance?: number;
  /** Direct corruption change (positive = increase corruption) */
  corruption?: number;
  /** Emotional profile shifts */
  emotionalShifts?: Partial<EmotionalProfile>;
  plotFlags?: Record<string, boolean>;
  /** Items to add to player inventory */
  itemGrants?: string[];
}

// ---------------------------------------------------------------------------
// Session
// ---------------------------------------------------------------------------

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
