/**
 * Legacy Daughters System — Generational Mechanics
 *
 * When a queen is fully broken (resistance 0, corruption > 70),
 * she may produce an heir. The daughter inherits a mix of the
 * mother's traits, modified by how she was broken and the player's
 * relationship with the mother.
 *
 * Daughters enter the council as new queens with unique personalities
 * shaped by their mother's trauma and the player's legacy.
 */

import type {
  Queen,
  QueenArchetype,
  PersonalityVector,
  EmotionalProfile,
  SexualDNA,
  PhysicalBlueprint,
  StripperArc,
  BreakingMethod,
} from "@/types/game";

export interface LegacyDaughter {
  /** Generated from mother's name */
  name: string;
  /** Mother's queen ID */
  motherId: string;
  /** How many generations from original queen */
  generation: number;
  /** What broke the mother — shapes daughter's personality */
  motherBreakingMethod: BreakingMethod | null;
  /** How the daughter feels about her heritage */
  heritageAttitude: "proud" | "ashamed" | "defiant" | "accepting" | "vengeful";
}

/** Name generation patterns for daughters */
const NAME_PREFIXES: Record<QueenArchetype, string[]> = {
  ice: ["Elsa", "Freya", "Ingrid", "Astrid", "Sigrid"],
  fire: ["Ember", "Phoenix", "Blaze", "Cinder", "Flame"],
  warrior: ["Valka", "Brienne", "Athena", "Hilda", "Astarte"],
  sorceress: ["Morgana", "Circe", "Hex", "Raven", "Luna"],
  priestess: ["Grace", "Faith", "Hope", "Trinity", "Eden"],
  scholar: ["Sage", "Iris", "Cleo", "Ada", "Hypatia"],
  merchant: ["Goldie", "Sterling", "Jade", "Ruby", "Pearl"],
  innocent: ["Dawn", "Lily", "Rose", "Dove", "Blossom"],
  defiant: ["Rebel", "Storm", "Riot", "Fury", "Tempest"],
  seductress: ["Venus", "Siren", "Desire", "Lux", "Charm"],
  shadow: ["Shade", "Whisper", "Veil", "Nyx", "Umbra"],
  sun: ["Aurora", "Soleil", "Daya", "Helia", "Radiance"],
};

/**
 * Determine if a broken queen can produce a legacy daughter.
 * Requirements: resistance 0, corruption > 70, relationship trust > 50.
 */
export function canProduceDaughter(queen: Queen): boolean {
  return (
    queen.resistance === 0 &&
    queen.corruption > 70 &&
    queen.relationship.trust > 50
  );
}

/**
 * Generate a legacy daughter from a broken queen.
 * The daughter's traits are a mutation of the mother's,
 * shaped by how she was broken.
 */
export function generateDaughter(
  mother: Queen,
  breakingMethod: BreakingMethod | null,
  generation: number,
): Queen {
  const archetype = mutateArchetype(mother.archetype, breakingMethod);
  const name = generateDaughterName(mother.archetype, generation);
  const id = `legacy-${mother.id}-g${generation}`;

  // Personality mutation — daughters react against or amplify their mother's traits
  const heritageRoll = Math.random();
  const heritageAttitude: LegacyDaughter["heritageAttitude"] =
    heritageRoll < 0.2 ? "vengeful" :
    heritageRoll < 0.4 ? "defiant" :
    heritageRoll < 0.6 ? "ashamed" :
    heritageRoll < 0.8 ? "accepting" : "proud";

  const personality = mutatePerson(mother.personality, heritageAttitude);
  const emotionalProfile = mutateEmotions(mother.emotionalProfile, heritageAttitude);

  // Resistance starts high — daughters learned from their mother's fall
  const baseResistance = heritageAttitude === "vengeful" ? 95 :
    heritageAttitude === "defiant" ? 90 :
    heritageAttitude === "ashamed" ? 70 :
    heritageAttitude === "accepting" ? 50 : 60;

  const daughter: Queen = {
    id,
    name,
    title: `Daughter of ${mother.name}`,
    archetype,
    resistance: baseResistance,
    resistanceCeiling: baseResistance,
    corruption: 0,
    awakeningFired: false,
    vulnerabilities: {
      // Daughters are weak where their mothers were strong
      physical: -(mother.vulnerabilities.physical ?? 0) * 0.5 + Math.random() * 0.4,
      psychological: Math.min(1, (mother.vulnerabilities.psychological ?? 0) + 0.2),
      magical: (mother.vulnerabilities.magical ?? 0) * 0.8,
      social: (mother.vulnerabilities.social ?? 0) * 0.7 + 0.1,
    },
    personality,
    relationship: { trust: 0, affection: 0, respect: 15, desire: 0, fear: 30, memories: [] },
    emotion: { primary: heritageAttitude === "vengeful" ? "hostile" : "guarded", intensity: 0.7 },
    emotionalProfile,
    speechStyle: generateSpeechStyle(archetype, heritageAttitude),
    visualDescription: `Young woman bearing a resemblance to ${mother.name}. ${archetype} archetype, generation ${generation}.`,
    boundaries: generateBoundaries(heritageAttitude),
    // Simplified queen-specific fields
    sexualDNA: mutateSexualDNA(mother.sexualDNA, heritageAttitude),
    physicalBlueprint: mutateBlueprint(mother.physicalBlueprint),
    fluxPrompt: `Young woman, daughter of ${mother.name}, ${archetype} archetype, dark fantasy portrait`,
    stripperArc: {
      club: "Unknown",
      stageName: name,
      quitReason: "Never started — she saw what it did to her mother",
      returnTrigger: "70% corruption — the legacy calls",
      uniqueKink: "Mirror of her mother's but twisted by shame",
    },
    performerReference: mother.performerReference,
    awakening: `The daughter of ${mother.name} discovers she carries the same desires her mother tried to suppress. The realization is devastating — and electric.`,
  };

  return daughter;
}

// --- Mutation helpers ---

function mutateArchetype(motherArchetype: QueenArchetype, method: BreakingMethod | null): QueenArchetype {
  // Daughters sometimes shift archetype based on how their mother was broken
  const shifts: Record<string, Record<string, QueenArchetype>> = {
    physical: { warrior: "defiant", ice: "fire", innocent: "warrior" },
    psychological: { scholar: "shadow", defiant: "ice", fire: "sorceress" },
    social: { merchant: "shadow", seductress: "ice", sun: "shadow" },
    magical: { sorceress: "priestess", priestess: "sorceress", shadow: "sun" },
  };

  if (method && shifts[method]?.[motherArchetype]) {
    return shifts[method][motherArchetype];
  }
  return motherArchetype;
}

function generateDaughterName(archetype: QueenArchetype, generation: number): string {
  const names = NAME_PREFIXES[archetype] ?? NAME_PREFIXES.warrior;
  return names[generation % names.length];
}

function mutatePerson(mother: PersonalityVector, attitude: string): PersonalityVector {
  const flip = attitude === "defiant" || attitude === "vengeful";
  const dampen = attitude === "ashamed";
  const m = (v: number) => {
    if (flip) return Math.max(0, Math.min(1, 1 - v + (Math.random() * 0.2 - 0.1)));
    if (dampen) return Math.max(0, Math.min(1, v * 0.7));
    return Math.max(0, Math.min(1, v + (Math.random() * 0.3 - 0.15)));
  };
  return {
    dominance: m(mother.dominance),
    warmth: m(mother.warmth),
    cunning: m(mother.cunning),
    loyalty: m(mother.loyalty),
    cruelty: m(mother.cruelty),
    sensuality: m(mother.sensuality),
    humor: m(mother.humor),
    ambition: m(mother.ambition),
  };
}

function mutateEmotions(mother: EmotionalProfile, attitude: string): EmotionalProfile {
  return {
    fear: attitude === "vengeful" ? 5 : attitude === "ashamed" ? 40 : 20,
    defiance: attitude === "vengeful" ? 90 : attitude === "defiant" ? 80 : 50,
    arousal: 0,
    submission: attitude === "accepting" ? 20 : 0,
    despair: attitude === "ashamed" ? 30 : 5,
  };
}

function generateSpeechStyle(archetype: QueenArchetype, attitude: string): string {
  const styles: Record<string, string> = {
    vengeful: "Cold and precise. Every word is a weapon. She sounds like her mother but sharper, harder, with none of the warmth that was beaten out of the original.",
    defiant: "Loud where her mother was quiet. Aggressive where her mother yielded. Overcompensates for inherited vulnerability with bravado.",
    ashamed: "Quiet, almost apologetic. Speaks in half-sentences. Flinches at her own name. Carries her mother's shame like a physical weight.",
    accepting: "Measured and knowing. She's made peace with what she is. There's a tiredness in her voice that doesn't match her age.",
    proud: "Regal and commanding. She wears her lineage openly. Her mother's strength without the cracks. Not yet tested.",
  };
  return styles[attitude] ?? styles.accepting;
}

function generateBoundaries(attitude: string): string[] {
  const base = ["Will not discuss her mother's breaking without trust > 60"];
  if (attitude === "vengeful") base.push("Will attempt to harm the player if trust < 0");
  if (attitude === "defiant") base.push("Refuses any action her mother was forced into");
  if (attitude === "ashamed") base.push("Cannot maintain eye contact during intimate moments");
  if (attitude === "accepting") base.push("Will not pretend to be stronger than she is");
  return base;
}

function mutateSexualDNA(mother: SexualDNA, attitude: string): SexualDNA {
  return {
    ...mother,
    desireType: attitude === "ashamed" ? "responsive" : mother.desireType,
    awakeningType: "denial-until-forced",
    addictionSpeed: attitude === "accepting" ? "fast" : "slow-burn",
    aftercareNeed: attitude === "ashamed" ? "heavy" : mother.aftercareNeed,
    voiceDNA: `Echoes of ${mother.voiceDNA} but younger, rawer, less controlled`,
  };
}

function mutateBlueprint(mother: PhysicalBlueprint): PhysicalBlueprint {
  return {
    ...mother,
    primeYear: "current",
    implants: "None — natural",
    keyTrait: `Resembles her mother in the eyes and jawline, but younger and untouched`,
  };
}
