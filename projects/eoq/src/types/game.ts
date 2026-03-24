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
// 19-Trait Sexual DNA System — types defined below in Queen DNA System section
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Struggle Meter (from GDD)
// ---------------------------------------------------------------------------

/**
 * The Struggle Meter tracks moment-to-moment physical/psychological resistance
 * during active scenes. Distinct from long-term Resistance stat.
 *
 * 0   = full surrender (scene ends in full submission)
 * 100 = maximum resistance (scene blocked or fails)
 *
 * The meter depletes when player actions match the character's vulnerability
 * profile and DNA traits. It resets between scenes.
 */
export interface StruggleMeter {
  /** Current value 0-100 */
  current: number;
  /** Whether the meter is active in the current scene */
  active: boolean;
  /**
   * Multiplier applied to depletion based on DNA traits.
   * Calculated from: painTolerance, brake, awakeningType, blackmailNeed.
   */
  resistanceMultiplier: number;
}

/**
 * Compute the struggle resistance multiplier from a character's DNA.
 * Higher = harder to deplete (more struggle before surrender).
 */
export function computeStruggleMultiplier(dna: SexualDNA): number {
  // Base: pain tolerance (high = more resistant). accelBrake is a string, so use painTolerance only.
  const base = (dna.painTolerance / 10) * 0.7;
  // Awakening modifier: denial-until-forced is hardest, always-knew is easiest
  const awakeningMod: Record<AwakeningType, number> = {
    "always-knew": 0.0,
    "total-surprise": 0.1,
    "slow-realization": 0.15,
    "denial-until-forced": 0.3,
  };
  // Blackmail modifier: begs-for-it softens resistance
  const blackmailMod: Record<BlackmailNeed, number> = {
    "begs-for-it": -0.1,
    "heightens-it": -0.05,
    "necessary": 0.1,
    "bored-without-it": 0.05,
    "none": 0.0,
  };
  return Math.max(0.1, Math.min(1.0, base + awakeningMod[dna.awakeningType] + blackmailMod[dna.blackmailNeed]));
}

// ---------------------------------------------------------------------------
// Harem Wars Jealousy Matrix (from GDD Appendix A)
// ---------------------------------------------------------------------------

/**
 * Harem Wars event types — what happens when rival queens collide.
 * Non-lethal; always ends in sexual competition or forced cooperation.
 */
export type HaremWarsEventType =
  | "catfight"            // hair-pulling, slapping, physical confrontation
  | "sabotage_nudes"      // one queen leaks compromising material on another
  | "false_accusation"    // political manipulation within the harem
  | "forced_kiss"         // QTE-style scene, rivals forced together
  | "competition_dance"   // rivalry pole/strip competition
  | "competition_scene";  // sexual competition for player's favor

export interface HaremWarsEvent {
  id: string;
  type: HaremWarsEventType;
  instigatorId: string;
  targetId: string;
  /** Minimum harem rivalry tension required to trigger */
  tensionThreshold: number;
  /** Scene ID where this event can fire */
  sceneId: string;
  /** Dialogue turns for this event */
  turns: DialogueTurn[];
}

/**
 * Rivalry tension between two queens — increases when they share scenes
 * or when player shows favoritism. Drives Harem Wars event triggers.
 */
export interface RivalryTension {
  queenAId: string;
  queenBId: string;
  /** 0-100: 0 = neutral/friendly, 100 = maximum conflict */
  tension: number;
  /** Events already fired between this pair */
  firedEvents: string[];
}

// ---------------------------------------------------------------------------
// Ending System (from GDD — 8 endings per queen)
// ---------------------------------------------------------------------------

/**
 * The 8 possible ending paths for each queen.
 * Determined by corruption level, betrayal threshold, and relationship stats
 * at the time of the final choice sequence.
 */
export type QueenEndingType =
  | "blissful_wife"      // Quits career, eternal devotion
  | "shattered_pet"      // Total psychological submission, mindless bliss
  | "betrayed_rebel"     // Low betrayal threshold triggered; flees but returns
  | "perfect_pet"        // Complete surrender, recruits other queens for player
  | "worship_queen"      // Starts a cult/movement in player's name
  | "harem_empress"      // Leads the other queens as first among servants
  | "eternal_addict"     // Lives entirely for player's attention/touch
  | "legacy_mother";     // Pregnant with player's child, dynasty path

export interface QueenEnding {
  type: QueenEndingType;
  /** Display label */
  label: string;
  /** Conditions required (plot flags + stat thresholds) */
  conditions: EndingCondition;
  /** Narrative summary for journal/gallery */
  summary: string;
  /** Scene ID to jump to for this ending */
  sceneId: string;
}

export interface EndingCondition {
  minCorruption?: number;
  maxCorruption?: number;
  minTrust?: number;
  maxTrust?: number;
  minAffection?: number;
  /** Plot flags that must be set */
  requiredFlags?: string[];
  /** Plot flags that must NOT be set */
  blockedFlags?: string[];
  /** Whether betrayal threshold was triggered */
  betrayalTriggered?: boolean;
}

// ---------------------------------------------------------------------------
// Awakening Event (from GDD — fires at 70% corruption)
// ---------------------------------------------------------------------------

/**
 * The Awakening is the pivotal cinematic moment that fires when a queen
 * reaches 70% corruption (corruption >= 70). It is shaped by her
 * AwakeningType DNA trait and represents her permanent personality shift.
 *
 * After the Awakening: resistance resets to a permanently lower ceiling,
 * and new scene options unlock (stripper arc return, obsession phone calls,
 * Legacy path).
 */
export interface AwakeningEvent {
  characterId: string;
  /** Corruption level at which this fires */
  triggerCorruption: number; // default 70
  /** Whether this has already fired for this character */
  fired: boolean;
  /** Cinematic description (used as ComfyUI/Mochi prompt basis) */
  cinematicPrompt: string;
  /** The shift summary (e.g., "Ice queen suit on conference table pole...") */
  shiftDescription: string;
  /** Dialogue turns for the awakening scene */
  turns: DialogueTurn[];
  /** New resistance ceiling post-awakening (0-40 range from GDD) */
  newResistanceCeiling: number;
}

// ---------------------------------------------------------------------------
// Phone Obsession System (from GDD)
// ---------------------------------------------------------------------------

/**
 * Post-breaking phone behavior — queens send messages once obsession sets in.
 * Driven by addictionSpeed and jealousyType DNA traits.
 * Messages unlock progressively as corruption increases past 70.
 */
export interface PhoneMessage {
  characterId: string;
  /** In-game day this message becomes available */
  day: number;
  /** Message content */
  text: string;
  /** Whether this is a missed call vs text */
  type: "text" | "missed_call" | "voice_note";
  /** Minimum corruption required */
  minCorruption: number;
}

// ---------------------------------------------------------------------------
// Stripper Arc — defined below in Queen DNA System section
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// No Mercy Mode (from GDD)
// ---------------------------------------------------------------------------

/**
 * No Mercy Mode is a hidden toggle that switches between:
 * - Default (Blissful): Resistance as foreplay, tears of pleasure, surrender = ecstasy
 * - Dark Mode: Ruthless play, no softening, maximum psychological pressure
 *
 * The mode affects LLM prompt intensity directives and available scene branches.
 */
export type PlayMode = "blissful" | "no_mercy";

// ---------------------------------------------------------------------------
// Legacy Daughters System (from GDD)
// ---------------------------------------------------------------------------

/**
 * Legacy daughters are procedurally generated characters created by SoulForge.
 * They inherit DNA from their mother (one of the 21 council queens) and the player.
 * They know the full history of their mother's breaking — either craving it or fighting it.
 */
export interface LegacyDaughter {
  id: string;
  name: string;
  /** Council queen this daughter descends from */
  motherId: string;
  /** 19-trait DNA — inherited and mutated from mother's DNA */
  dna: SexualDNA;
  /** Inherited personality vector (blended from mother + random mutation) */
  personality: PersonalityVector;
  /** Whether she craves the same breaking path or fights it harder */
  inheritedPath: "craves" | "fights";
  /** Generation number (1 = direct daughter, 2 = granddaughter, etc.) */
  generation: number;
  /** Visual description for portrait generation */
  visualDescription: string;
  /** SoulForge generation timestamp */
  generatedAt: number;
  /** Whether she has been introduced in the narrative */
  introduced: boolean;
}

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
  /** Maximum resistance ceiling — lowered permanently after Awakening */
  resistanceCeiling: number;
  /** Corruption level (0-100, starts low) */
  corruption: number;
  /** What breaking methods are most/least effective (-1 to 1 scale) */
  vulnerabilities: Partial<Record<BreakingMethod, number>>;
  /** Title or role for display */
  title?: string;
  /**
   * 19-trait Sexual DNA — present for council queens and SoulForge daughters.
   * Optional for non-queen characters (Kael, Vaelis etc. don't have it).
   */
  dna?: SexualDNA;
  /** Active struggle meter for this character (present during intimate scenes) */
  struggleMeter?: StruggleMeter;
  /** Whether the Awakening event has fired for this character */
  awakeningFired: boolean;
  /** Stripper arc state */
  stripperArc?: StripperArc;
  /** Which ending path this character is currently tracking toward */
  currentEndingPath?: QueenEndingType;
  /** Harem role post-breaking */
  haremRole?: "first_queen" | "rivalry_instigator" | "devotee" | "recruiter" | "empress";
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
  /** Play mode — blissful (default) or no_mercy (hidden toggle) */
  playMode: PlayMode;
  /** Active rivalry tensions between queens */
  rivalryTensions: RivalryTension[];
  /** Pending phone messages from obsessing queens */
  pendingPhoneMessages: PhoneMessage[];
  /** Legacy daughters that have been generated */
  legacyDaughters: LegacyDaughter[];
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
// Queen DNA System (19-trait sexual personality matrix)
// ---------------------------------------------------------------------------

export type DesireType = "responsive" | "spontaneous" | "hybrid";

export type GaggingResponse =
  | "fights"
  | "pushes-through"
  | "enjoys"
  | "breaks"
  | "minimal"
  | "legendary-pusher";

export type AwakeningType =
  | "always-knew"
  | "total-surprise"
  | "slow-realization"
  | "denial-until-forced";

export type BlackmailNeed =
  | "none"
  | "necessary"
  | "heightens-it"
  | "bored-without-it"
  | "begs-for-it";

export type AddictionSpeed = "very-slow" | "slow-burn" | "normal" | "fast" | "instant";

export type JealousyType =
  | "possessive"
  | "competitive"
  | "turns-her-on"
  | "doesnt-care"
  | "none";

export type AftercareNeed = "none" | "light" | "medium" | "heavy";

export type GroupSexAttitude =
  | "hates"
  | "tolerates"
  | "curious"
  | "craves"
  | "initiates";

/** 19-trait sexual personality DNA — makes every queen unique */
export interface SexualDNA {
  desireType: DesireType;
  accelBrake?: string;
  painTolerance: number;        // 1-10
  humiliationEnjoyment: number; // 1-10
  exhibitionismLevel: number;   // 1-10
  gaggingResponse?: GaggingResponse;
  moaningStyle: string;
  tearTrigger: string;
  orgasmStyle: string;
  awakeningType: AwakeningType;
  blackmailNeed: BlackmailNeed;
  addictionSpeed: AddictionSpeed;
  jealousyType: JealousyType;
  aftercareNeed?: AftercareNeed;
  switchPotential: number;      // 1-10
  groupSexAttitude: GroupSexAttitude;
  roleplayAffinity: string;
  betrayalThreshold: number;    // 1-10
  voiceDNA: string;
}

/** Prime-era physical measurements for Flux prompt generation */
export interface PhysicalBlueprint {
  primeYear: string;
  height: string;
  weight: string;
  measurements: string;
  braCup: string;
  implants: string;
  hair: string;
  eyes: string;
  skin: string;
  tattoos: string;
  bodyType: string;
  faceShape: string;
  keyTrait: string;
}

/** Stripper backstory arc — triggers at 70% corruption */
export interface StripperArc {
  club: string;
  stageName: string;
  quitReason: string;
  returnTrigger: string;
  uniqueKink: string;
}

/** Queen — extends Character with performer DNA system */
export interface Queen extends Character {
  sexualDNA: SexualDNA;
  physicalBlueprint: PhysicalBlueprint;
  fluxPrompt: string;
  stripperArc: StripperArc;
  /** Real performer name for PuLID face reference injection */
  performerReference: string;
  /** Awakening cinematic description */
  awakening: string;
}

// ---------------------------------------------------------------------------
// Player Style Tracking
// ---------------------------------------------------------------------------

/**
 * Tracks the player's behavioral tendencies across choices.
 * Used for adaptive gameplay — "No Mercy Mode" detection, NPC reactions,
 * and tailoring future choice generation.
 */
export interface PlayerStyle {
  /** Mercy vs cruelty tendency (0=cruel, 100=merciful) */
  mercyScore: number;
  /** Seduction/charm usage frequency (0-100) */
  seductionScore: number;
  /** Psychological manipulation frequency (0-100) */
  manipulationScore: number;
  /** Physical force/intimidation frequency (0-100) */
  dominanceScore: number;
  /** Diplomatic/relationship-building frequency (0-100) */
  diplomacyScore: number;
  /** Total choices made (for weighted averaging) */
  totalChoices: number;
}

export const DEFAULT_PLAYER_STYLE: PlayerStyle = {
  mercyScore: 50,
  seductionScore: 0,
  manipulationScore: 0,
  dominanceScore: 0,
  diplomacyScore: 0,
  totalChoices: 0,
};

/**
 * Classify a choice and return style deltas.
 * Positive mercyScore = merciful, negative = cruel.
 */
export function classifyChoiceStyle(choice: PlayerChoice): Partial<PlayerStyle> {
  const deltas: Partial<PlayerStyle> = {};
  const intent = choice.intent?.toLowerCase() ?? "";
  const method = choice.breakingMethod;

  // Mercy/cruelty from effects
  const eff = choice.effects;
  if (eff) {
    const resistanceDelta = eff.resistance ?? 0;
    const corruptionDelta = eff.corruption ?? 0;
    if (resistanceDelta < -10 || corruptionDelta > 5) deltas.mercyScore = -15;
    else if (resistanceDelta < 0) deltas.mercyScore = -5;

    if ((eff.trust ?? 0) > 5 && resistanceDelta >= 0) deltas.mercyScore = 10;
    if ((eff.affection ?? 0) > 10 && resistanceDelta >= 0) deltas.mercyScore = 5;
  }

  // Intent classification
  if (/compassion|tender|comfort|protective|honest|empathetic/i.test(intent)) {
    deltas.mercyScore = (deltas.mercyScore ?? 0) + 10;
    deltas.diplomacyScore = 10;
  }
  if (/manipulat|probing|knowing|transactional|calculating/i.test(intent)) {
    deltas.manipulationScore = 15;
    deltas.mercyScore = (deltas.mercyScore ?? 0) - 5;
  }
  if (/seduc|desire|charm|playful/i.test(intent)) {
    deltas.seductionScore = 15;
  }
  if (/aggressive|intimidat|demanding|challenge|confrontat|ruthless/i.test(intent)) {
    deltas.dominanceScore = 15;
    deltas.mercyScore = (deltas.mercyScore ?? 0) - 10;
  }
  if (/diplomat|cautious|respectful|loyal|inspiring|hopeful/i.test(intent)) {
    deltas.diplomacyScore = (deltas.diplomacyScore ?? 0) + 10;
    deltas.mercyScore = (deltas.mercyScore ?? 0) + 5;
  }

  // Breaking method
  if (method === "physical") deltas.dominanceScore = (deltas.dominanceScore ?? 0) + 10;
  if (method === "psychological") deltas.manipulationScore = (deltas.manipulationScore ?? 0) + 10;
  if (method === "social") deltas.seductionScore = (deltas.seductionScore ?? 0) + 5;

  return deltas;
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
  /** Tracks player behavioral tendencies across choices */
  playerStyle: PlayerStyle;
  /** No Mercy Mode — unlocked when mercyScore drops below 20 after 10+ choices */
  noMercyUnlocked: boolean;
  /** Whether No Mercy Mode is actively enabled by the player */
  noMercyActive: boolean;
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

// ---------------------------------------------------------------------------
// Ending Resolution
// ---------------------------------------------------------------------------

/**
 * Determine which ending path a character is tracking toward.
 * Called after each significant choice to update currentEndingPath.
 *
 * Priority (highest to lowest): betrayed_rebel, legacy_mother, shattered_pet,
 * worship_queen, harem_empress, perfect_pet, eternal_addict, blissful_wife.
 */
export function resolveEndingPath(
  character: Character,
  flags: Record<string, boolean>
): QueenEndingType {
  const { corruption, resistance, relationship, dna } = character;
  const { trust, affection, desire } = relationship;

  // Betrayal path: betrayal threshold exceeded
  const betrayalFlag = flags[`betrayed_${character.id}`];
  if (betrayalFlag) return "betrayed_rebel";

  // Legacy path: pregnancy flag or legacy desire active
  if (flags[`legacy_path_${character.id}`] && corruption >= 80) return "legacy_mother";

  // Shattered pet: total corruption with low trust
  if (corruption >= 95 && resistance === 0 && trust < 30) return "shattered_pet";

  // Worship queen: high corruption + high affection + cult flag
  if (flags[`worship_path_${character.id}`] && corruption >= 80 && affection >= 60) return "worship_queen";

  // Harem empress: first queen broken, leads others
  if (flags[`harem_empress_${character.id}`] && corruption >= 70) return "harem_empress";

  // Perfect pet: high corruption, recruits others
  if (corruption >= 80 && trust >= 50 && dna && dna.groupSexAttitude !== "hates") return "perfect_pet";

  // Eternal addict: high addiction speed + high desire
  if (
    corruption >= 60 &&
    desire >= 70 &&
    dna &&
    (dna.addictionSpeed === "instant" || dna.addictionSpeed === "fast")
  ) return "eternal_addict";

  // Blissful wife: high trust + high affection + moderate corruption
  if (trust >= 70 && affection >= 70 && corruption >= 50) return "blissful_wife";

  // Default: wherever corruption is pointing
  if (corruption >= 60) return "perfect_pet";
  return "blissful_wife";
}

// ---------------------------------------------------------------------------
// Awakening Trigger Check
// ---------------------------------------------------------------------------

/**
 * Check whether a character's Awakening should fire.
 * Returns true if corruption >= 70 and awakening has not yet fired.
 */
export function shouldFireAwakening(character: Character): boolean {
  return character.corruption >= 70 && !character.awakeningFired;
}

// ---------------------------------------------------------------------------
// Harem Wars Trigger Check
// ---------------------------------------------------------------------------

/**
 * Check whether a Harem Wars event should trigger between two queens.
 * Returns true if rivalry tension >= threshold and event hasn't fired.
 */
export function shouldTriggerHaremWars(
  tension: RivalryTension,
  event: HaremWarsEvent
): boolean {
  return (
    tension.tension >= event.tensionThreshold &&
    !tension.firedEvents.includes(event.id)
  );
}

/**
 * Compute rivalry tension increase when player interacts with one queen
 * while another is in the scene or aware of the interaction.
 * Based on jealousyType DNA of the witnessing queen.
 */
export function computeRivalryTensionIncrease(
  witnessJealousyType: JealousyType,
  playerActionIntensity: number // 1-10
): number {
  const multipliers: Record<JealousyType, number> = {
    "possessive": 2.0,
    "competitive": 1.5,
    "turns-her-on": -0.5,  // actually reduces tension, she enjoys it
    "doesnt-care": 0.1,
    "none": 0.0,
  };
  return Math.round(playerActionIntensity * multipliers[witnessJealousyType]);
}

// ---------------------------------------------------------------------------
// DNA Prompt Fragment Builder
// ---------------------------------------------------------------------------

/**
 * Build a compact DNA context string for the LLM system prompt.
 * Summarizes the most behaviorally relevant traits without overwhelming context.
 */
export function buildDNAPromptFragment(dna: SexualDNA): string {
  return [
    `Desire: ${dna.desireType}`,
    `Arousal ramp: ${dna.accelBrake ?? "unknown"}`,
    `Pain tolerance: ${dna.painTolerance}/10`,
    `Humiliation enjoyment: ${dna.humiliationEnjoyment}/10`,
    `Exhibitionism: ${dna.exhibitionismLevel}/10`,
    `Gagging: ${dna.gaggingResponse ?? "unknown"}`,
    `Moaning: ${dna.moaningStyle}`,
    `Tears from: ${dna.tearTrigger}`,
    `Orgasm: ${dna.orgasmStyle}`,
    `Awakening type: ${dna.awakeningType}`,
    `Blackmail need: ${dna.blackmailNeed}`,
    `Addiction speed: ${dna.addictionSpeed}`,
    `Jealousy: ${dna.jealousyType}`,
    `Aftercare: ${dna.aftercareNeed ?? "unknown"}`,
    `Switch potential: ${dna.switchPotential}/10`,
    `Group scenes: ${dna.groupSexAttitude}`,
    `Roleplay fantasy: ${dna.roleplayAffinity}`,
    `Betrayal threshold: ${dna.betrayalThreshold}/10`,
    `Voice: ${dna.voiceDNA}`,
  ].join(" | ");
}
