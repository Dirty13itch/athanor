/**
 * SoulForge Engine v12 — Procedural Legacy Daughter Generation
 *
 * Generates new characters on demand via DNA inheritance + mutation.
 * Every daughter inherits traits from her mother (council queen) with
 * controlled random variation, producing unique but recognizable lineages.
 *
 * Generation time target: <68 seconds on WORKSHOP (RTX 5090).
 * DNA inheritance: 60% mother, 40% mutation seed + player taste.
 *
 * From GDD: "Every new girl gets diary, voice, physics, secrets, harem role"
 */

import type {
  SexualDNA,
  PersonalityVector,
  LegacyDaughter,
  DesireType,
  GagResponse,
  AddictionSpeed,
  JealousyType,
  AfterCareNeed,
  GroupSexAttitude,
  AwakeningType,
  BlackmailNeed,
} from "@/types/game";

// ---------------------------------------------------------------------------
// Player Taste Seed — influences mutation direction
// ---------------------------------------------------------------------------

/**
 * Player taste descriptor that biases mutation.
 * Maps to specific DNA trait deltas.
 * Examples from GDD: "tall, fake, submissive discovery"
 */
export interface PlayerTaste {
  /** Raw descriptor string (e.g., "tall, fake, submissive discovery") */
  descriptor: string;
  /** Parsed bias values — deltas applied to base DNA */
  exhibitionismBias?: number;       // +/- 0-3
  submissionBias?: number;          // shifts desireType toward responsive
  painBias?: number;                // +/- 0-3
  humiliationBias?: number;         // +/- 0-3
  addictionBias?: "slow" | "fast" | "instant";
  awakeningBias?: AwakeningType;
}

// ---------------------------------------------------------------------------
// DNA Inheritance
// ---------------------------------------------------------------------------

/**
 * Inherit a numeric DNA trait with controlled mutation.
 * 60% from mother value, 40% random variation within ±range.
 */
function inheritNumeric(
  motherValue: number,
  min: number,
  max: number,
  mutationRange: number
): number {
  const base = motherValue * 0.6 + (min + Math.random() * (max - min)) * 0.4;
  const mutation = (Math.random() - 0.5) * 2 * mutationRange;
  return Math.round(Math.max(min, Math.min(max, base + mutation)));
}

/**
 * Inherit a categorical DNA trait.
 * 70% chance to inherit mother's value, 30% chance of adjacent mutation.
 */
function inheritCategorical<T>(motherValue: T, options: T[]): T {
  if (Math.random() < 0.7) return motherValue;
  const idx = options.indexOf(motherValue);
  if (idx < 0) return options[Math.floor(Math.random() * options.length)];
  // Prefer adjacent options (realistic mutation)
  const adjacent = [
    options[Math.max(0, idx - 1)],
    options[Math.min(options.length - 1, idx + 1)],
  ].filter((v, i, arr) => arr.indexOf(v) === i && v !== motherValue);
  return adjacent.length > 0 ? adjacent[Math.floor(Math.random() * adjacent.length)] : motherValue;
}

const DESIRE_TYPES: DesireType[] = ["spontaneous", "responsive", "hybrid", "responsive_switch"];
const GAG_RESPONSES: GagResponse[] = ["fights", "pushes_through", "enjoys", "breaks", "minimal", "legendary_pusher"];
const ADDICTION_SPEEDS: AddictionSpeed[] = ["very_slow", "slow", "normal", "fast", "instant"];
const JEALOUSY_TYPES: JealousyType[] = ["possessive", "competitive", "turns_her_on", "doesnt_care", "none"];
const AFTERCARE_NEEDS: AfterCareNeed[] = ["none", "light", "medium", "heavy", "craves_cuddles_while_crying"];
const GROUP_ATTITUDES: GroupSexAttitude[] = ["hates", "tolerates", "curious", "craves", "initiates"];
const AWAKENING_TYPES: AwakeningType[] = ["always_knew", "total_surprise", "slow_realization", "denial_until_forced"];
const BLACKMAIL_NEEDS: BlackmailNeed[] = ["necessary", "heightens_it", "bored_without", "begs_for_it", "none"];

/**
 * Generate a daughter's DNA from her mother's DNA with mutation.
 * Player taste biases are applied as final adjustments.
 */
export function inheritDNA(motherDNA: SexualDNA, taste?: PlayerTaste): SexualDNA {
  const base: SexualDNA = {
    desireType: inheritCategorical(motherDNA.desireType, DESIRE_TYPES),
    accelerator: inheritNumeric(motherDNA.accelerator, 1, 10, 2),
    brake: inheritNumeric(motherDNA.brake, 1, 10, 2),
    painTolerance: inheritNumeric(motherDNA.painTolerance, 1, 10, 2),
    humiliationEnjoyment: inheritNumeric(motherDNA.humiliationEnjoyment, 1, 10, 2),
    exhibitionismLevel: inheritNumeric(motherDNA.exhibitionismLevel, 1, 10, 2),
    gagResponse: inheritCategorical(motherDNA.gagResponse, GAG_RESPONSES),
    moaningStyle: mutateMoaningStyle(motherDNA.moaningStyle),
    tearTrigger: mutateTearTrigger(motherDNA.tearTrigger),
    orgasmStyle: mutateOrgasmStyle(motherDNA.orgasmStyle),
    awakeningType: inheritCategorical(motherDNA.awakeningType, AWAKENING_TYPES),
    blackmailNeed: inheritCategorical(motherDNA.blackmailNeed, BLACKMAIL_NEEDS),
    addictionSpeed: inheritCategorical(motherDNA.addictionSpeed, ADDICTION_SPEEDS),
    jealousyType: inheritCategorical(motherDNA.jealousyType, JEALOUSY_TYPES),
    afterCareNeed: inheritCategorical(motherDNA.afterCareNeed, AFTERCARE_NEEDS),
    switchPotential: inheritNumeric(motherDNA.switchPotential, 1, 10, 2),
    groupSexAttitude: inheritCategorical(motherDNA.groupSexAttitude, GROUP_ATTITUDES),
    roleplayAffinity: mutateRoleplayAffinity(motherDNA.roleplayAffinity),
    betrayalThreshold: inheritNumeric(motherDNA.betrayalThreshold, 1, 10, 2),
    voiceDNA: mutateVoiceDNA(motherDNA.voiceDNA),
  };

  // Apply player taste biases
  if (taste) {
    if (taste.exhibitionismBias) {
      base.exhibitionismLevel = Math.max(1, Math.min(10, base.exhibitionismLevel + taste.exhibitionismBias));
    }
    if (taste.painBias) {
      base.painTolerance = Math.max(1, Math.min(10, base.painTolerance + taste.painBias));
    }
    if (taste.humiliationBias) {
      base.humiliationEnjoyment = Math.max(1, Math.min(10, base.humiliationEnjoyment + taste.humiliationBias));
    }
    if (taste.addictionBias) {
      base.addictionSpeed = taste.addictionBias;
    }
    if (taste.awakeningBias) {
      base.awakeningType = taste.awakeningBias;
    }
    if (taste.submissionBias) {
      // Push toward responsive desire type if submission is desired
      if (taste.submissionBias > 0) {
        base.desireType = "responsive";
        base.brake = Math.min(10, base.brake + 1);
      }
    }
  }

  return base;
}

// ---------------------------------------------------------------------------
// Personality Inheritance
// ---------------------------------------------------------------------------

/**
 * Inherit personality vector from mother with mutation.
 * Daughters resemble their mothers but are distinct individuals.
 */
export function inheritPersonality(motherPersonality: PersonalityVector): PersonalityVector {
  const inherit = (v: number) => inheritNumeric(v * 10, 0, 10, 1.5) / 10;
  return {
    dominance: inherit(motherPersonality.dominance),
    warmth: inherit(motherPersonality.warmth),
    cunning: inherit(motherPersonality.cunning),
    loyalty: inherit(motherPersonality.loyalty),
    cruelty: inherit(motherPersonality.cruelty),
    sensuality: inherit(motherPersonality.sensuality),
    humor: inherit(motherPersonality.humor),
    ambition: inherit(motherPersonality.ambition),
  };
}

// ---------------------------------------------------------------------------
// Name Generation
// ---------------------------------------------------------------------------

/**
 * Generate a daughter's name.
 * Daughters often have names thematically related to their mother
 * but distinct — shorter, harder, or a regional variant.
 */
const DAUGHTER_NAME_POOL = [
  "Livia", "Vanya", "Sera", "Kira", "Nyx", "Adra", "Sable", "Eira",
  "Maeve", "Cass", "Lyra", "Zara", "Ione", "Petra", "Maris", "Ela",
  "Thea", "Cira", "Vela", "Ryn", "Sora", "Asha", "Nell", "Tamsin",
  "Bryn", "Lira", "Wren", "Nora", "Vex", "Alis", "Sage", "Kael",
  "Devi", "Runa", "Skye", "Lorne", "Rhea", "Isla", "Faye", "Vesna",
];

export function generateDaughterName(motherId: string, generation: number): string {
  // Seed based on motherId + generation for determinism within a session
  const seed = [...motherId].reduce((acc, c) => acc + c.charCodeAt(0), 0) + generation * 137;
  return DAUGHTER_NAME_POOL[seed % DAUGHTER_NAME_POOL.length];
}

// ---------------------------------------------------------------------------
// Visual Description Generation
// ---------------------------------------------------------------------------

/**
 * Generate a daughter's visual description prompt for ComfyUI/Flux.
 * Inherits mother's physical characteristics with generational variation.
 */
export function generateDaughterVisualDescription(
  motherVisualDescription: string,
  generation: number
): string {
  const genLabel = generation === 1 ? "daughter of" : generation === 2 ? "granddaughter of" : `${generation}th generation descendant of`;
  return (
    `${genLabel} the original queen. ` +
    motherVisualDescription
      .replace("Cinematic portrait", "")
      .replace("dark fantasy, 8k, photorealistic", "")
      .trim()
      .replace(/\.\s*$/, "") +
    `. Slightly younger, carries her mother's bearing but with her own fire. ` +
    `Cinematic portrait, dark fantasy, 8k, photorealistic.`
  );
}

// ---------------------------------------------------------------------------
// Full Daughter Generation
// ---------------------------------------------------------------------------

/**
 * Generate a complete Legacy Daughter from a mother character.
 * This is the core SoulForge operation — called when the player
 * activates the Legacy path for a broken queen.
 *
 * @param motherId - Council queen character ID
 * @param motherDNA - Mother's 19-trait DNA
 * @param motherPersonality - Mother's personality vector
 * @param motherVisualDescription - Mother's visual description
 * @param generation - 1 for direct daughter, 2 for granddaughter, etc.
 * @param taste - Optional player taste seed for bias
 * @param inheritedPath - Whether daughter craves or fights the same path
 */
export function forgeDaughter(
  motherId: string,
  motherDNA: SexualDNA,
  motherPersonality: PersonalityVector,
  motherVisualDescription: string,
  generation: number = 1,
  taste?: PlayerTaste,
  inheritedPath?: "craves" | "fights"
): LegacyDaughter {
  const dna = inheritDNA(motherDNA, taste);
  const personality = inheritPersonality(motherPersonality);
  const name = generateDaughterName(motherId, generation);
  const visualDescription = generateDaughterVisualDescription(motherVisualDescription, generation);

  // Default inherited path: daughters who know everything tend to crave it
  // (from GDD: "Legacy daughters know everything and either crave or fight it (ending in harder surrender)")
  const path = inheritedPath ?? (Math.random() < 0.6 ? "craves" : "fights");

  return {
    id: `daughter_${motherId}_gen${generation}_${Date.now()}`,
    name,
    motherId,
    dna,
    personality,
    inheritedPath: path,
    generation,
    visualDescription,
    generatedAt: Date.now(),
    introduced: false,
  };
}

// ---------------------------------------------------------------------------
// ComfyUI Workflow Integration
// ---------------------------------------------------------------------------

/**
 * Build the ComfyUI workflow payload for generating a daughter's portrait.
 * Uses the SoulMerge.json workflow from GDD Appendix F.
 *
 * Sent to WORKSHOP:8188 via /prompt endpoint.
 */
export function buildSoulForgeComfyPayload(
  daughter: LegacyDaughter,
  motherLoraPath: string
): Record<string, unknown> {
  return {
    prompt: {
      // Node 1: Load mother LoRA
      "1": {
        class_type: "LoraLoader",
        inputs: {
          lora_name: motherLoraPath,
          strength_model: 0.7,   // 70% mother resemblance
          strength_clip: 0.7,
        },
      },
      // Node 2: CLIP text encode — daughter visual description
      "2": {
        class_type: "CLIPTextEncode",
        inputs: {
          text: `hyperreal 4K cinematic ${daughter.visualDescription}`,
          clip: ["1", 1],
        },
      },
      // Node 3: Negative prompt
      "3": {
        class_type: "CLIPTextEncode",
        inputs: {
          text: "ugly, deformed, blurry, low quality, cartoon, anime, duplicate, watermark, text",
          clip: ["1", 1],
        },
      },
      // Node 4: KSampler
      "4": {
        class_type: "KSampler",
        inputs: {
          model: ["1", 0],
          positive: ["2", 0],
          negative: ["3", 0],
          latent_image: ["5", 0],
          seed: Math.floor(Math.random() * 2 ** 32),
          steps: 30,
          cfg: 7.0,
          sampler_name: "dpmpp_2m",
          scheduler: "karras",
          denoise: 1.0,
        },
      },
      // Node 5: Empty latent (1024x1024 portrait)
      "5": {
        class_type: "EmptyLatentImage",
        inputs: { width: 1024, height: 1024, batch_size: 1 },
      },
      // Node 6: VAE Decode
      "6": {
        class_type: "VAEDecode",
        inputs: { samples: ["4", 0], vae: ["7", 0] },
      },
      // Node 7: VAE Loader
      "7": {
        class_type: "VAELoader",
        inputs: { vae_name: "ae.safetensors" },
      },
      // Node 8: Save image
      "8": {
        class_type: "SaveImage",
        inputs: {
          images: ["6", 0],
          filename_prefix: `soulforge_${daughter.id}`,
        },
      },
    },
  };
}

// ---------------------------------------------------------------------------
// String mutation helpers
// ---------------------------------------------------------------------------

const MOANING_VARIANTS = [
  "breathy → sharp gasp", "low hum → desperate keening", "silent → sudden burst",
  "controlled → wild abandon", "quiet whimpers → loud moans", "reluctant sounds → eager cries",
  "stifled → explosive", "rhythmic sighs → breathless shuddering",
];

const TEAR_VARIANTS = [
  "pleasure overload", "being truly seen", "surrender colliding with pride",
  "the moment control slips completely", "humiliation fusing with desire",
  "realizing she wants this", "being broken gently", "being broken hard",
];

const ORGASM_VARIANTS = [
  "hard to reach — requires surrender", "easy multiple — she's been holding back",
  "single intense — leaves her stunned", "squirter — can't hide it",
  "dissociative — she loses herself entirely", "pain-adjacent — needs the edge",
  "addictive — each one harder to stop than the last",
];

const ROLEPLAY_MUTATIONS: Record<string, string[]> = {
  "Corporate": ["Office power reversal", "CEO brought to her knees", "Board meeting surrender"],
  "Royal": ["Royalty taken", "Queen serving her king", "The throne knelt before"],
  "Medical": ["Doctor/patient reversal", "Operating theater surrender", "The healer healed"],
  "Stage": ["Performer claimed", "Stage lights and submission", "Pole dance confession"],
  "Secretary": ["Secretary gone feral", "After-hours office", "Desk surface surrender"],
};

function mutateMoaningStyle(mother: string): string {
  if (Math.random() < 0.4) {
    return MOANING_VARIANTS[Math.floor(Math.random() * MOANING_VARIANTS.length)];
  }
  return mother;
}

function mutateTearTrigger(mother: string): string {
  if (Math.random() < 0.3) {
    return TEAR_VARIANTS[Math.floor(Math.random() * TEAR_VARIANTS.length)];
  }
  return mother;
}

function mutateOrgasmStyle(mother: string): string {
  if (Math.random() < 0.35) {
    return ORGASM_VARIANTS[Math.floor(Math.random() * ORGASM_VARIANTS.length)];
  }
  return mother;
}

function mutateRoleplayAffinity(mother: string): string {
  // Find matching category for similar-but-different mutation
  for (const [key, variants] of Object.entries(ROLEPLAY_MUTATIONS)) {
    if (mother.toLowerCase().includes(key.toLowerCase())) {
      if (Math.random() < 0.4) {
        return variants[Math.floor(Math.random() * variants.length)];
      }
    }
  }
  return mother;
}

function mutateVoiceDNA(mother: string): string {
  // Keep accent but vary the specific characteristics
  if (Math.random() < 0.3) {
    const suffixes = [
      "voice catches on 'please'",
      "goes quiet right before surrendering",
      "laughs when overwhelmed",
      "accent thickens under pressure",
      "whispers when she means it most",
    ];
    const base = mother.split(",")[0]; // Keep accent
    return `${base}, ${suffixes[Math.floor(Math.random() * suffixes.length)]}`;
  }
  return mother;
}
