import type { Character } from "@/types/game";

/**
 * Empire of Broken Queens — Character Definitions
 *
 * Five core characters for Act 1: The Shattered Court.
 * Each has personality, relationship state, breaking system stats,
 * archetype, emotional profile, and vulnerabilities.
 *
 * Reconciled from:
 * - GDD: Queen archetypes, breaking system, stat model
 * - Dialogue System Design: Emotional profile (Fear/Defiance/Arousal/Submission/Despair)
 * - Storytelling Framework: Power asymmetry, resistance/erosion, transformation
 */

/** Isolde — The Usurper Queen. Controls Ashenmoor Keep. */
export const ISOLDE: Character = {
  id: "isolde",
  name: "Isolde",
  title: "The Usurper Queen",
  archetype: "ice",
  resistance: 90,
  corruption: 5,
  vulnerabilities: {
    physical: -0.5,    // highly resistant to force
    psychological: 0.6, // her ambition and paranoia are exploitable
    magical: 0.2,      // moderate
    social: 0.8,       // isolation and political pressure work
  },
  personality: {
    dominance: 0.8,
    warmth: 0.3,
    cunning: 0.9,
    loyalty: 0.4,
    cruelty: 0.5,
    sensuality: 0.7,
    humor: 0.4,
    ambition: 0.95,
  },
  relationship: {
    trust: 10,
    affection: 5,
    respect: 30,
    desire: 15,
    fear: 20,
    memories: [],
  },
  emotion: { primary: "calculating", intensity: 0.6 },
  emotionalProfile: {
    fear: 15,
    defiance: 85,
    arousal: 10,
    submission: 0,
    despair: 5,
  },
  speechStyle:
    "Formal and precise, with occasional cutting wit. Uses royal 'we' when asserting authority. Drops the facade when caught off-guard. Never raises her voice — the quieter she speaks, the more dangerous she is.",
  visualDescription:
    "Regal woman in her 30s, sharp angular features, dark auburn hair in elaborate braids threaded with thin gold chains, pale porcelain skin, ice-blue eyes. Wears a fitted black and gold gown with high structured collar. A thin scar runs from her left ear to her jaw. Cinematic portrait, dramatic side lighting, dark fantasy, 8k, photorealistic.",
  boundaries: [
    "Will never beg — she commands or manipulates",
    "Will not reveal her true feelings easily — vulnerability is weakness",
    "Uses intimacy as a tool, not a gift — unless trust exceeds 70",
    "Will kill without hesitation if cornered",
  ],
};

/** Seraphine — The Broken Oracle. Roams the ruins of the Spire. */
export const SERAPHINE: Character = {
  id: "seraphine",
  name: "Seraphine",
  title: "The Broken Oracle",
  archetype: "sorceress",
  resistance: 40,
  corruption: 20,
  vulnerabilities: {
    physical: 0.8,      // fragile, easily overwhelmed
    psychological: 0.5, // already half-broken by her own gift
    magical: -0.3,      // resistant to magical manipulation
    social: 0.6,        // lonely, craves connection
  },
  personality: {
    dominance: 0.2,
    warmth: 0.6,
    cunning: 0.5,
    loyalty: 0.7,
    cruelty: 0.1,
    sensuality: 0.4,
    humor: 0.3,
    ambition: 0.3,
  },
  relationship: {
    trust: 20,
    affection: 15,
    respect: 10,
    desire: 5,
    fear: 5,
    memories: [],
  },
  emotion: { primary: "melancholic", intensity: 0.7 },
  emotionalProfile: {
    fear: 35,
    defiance: 20,
    arousal: 5,
    submission: 30,
    despair: 45,
  },
  speechStyle:
    "Soft-spoken and halting, often trailing off mid-sentence as visions intrude. Mixes past and present tense unpredictably. Speaks in fragments when distressed, complete poetic sentences when calm. Sometimes addresses people who aren't there.",
  visualDescription:
    "Young woman in her late 20s, silver-white hair falling past her shoulders, pale blue eyes that seem to glow faintly. Wears tattered celestial robes — once white, now stained and torn — with faded constellation patterns that occasionally shimmer. Carries a cracked crystal orb that emits faint blue light. Gaunt and ethereal. Cinematic portrait, soft diffused lighting, dark fantasy, 8k, photorealistic.",
  boundaries: [
    "Cannot control her visions — they come unbidden and are often painful",
    "Terrified of physical violence — will flee rather than fight",
    "Deeply lonely but pushes people away to protect them from her prophecies",
    "Will not lie about what she sees, even when the truth is cruel",
  ],
};

/** Vaelis — The Hollow Knight. Guards the Crimson Gate. */
export const VAELIS: Character = {
  id: "vaelis",
  name: "Vaelis",
  title: "The Hollow Knight",
  archetype: "warrior",
  resistance: 85,
  corruption: 10,
  vulnerabilities: {
    physical: -0.8,     // nearly immune to physical coercion
    psychological: 0.7, // his oath, his lost humanity, his guilt
    magical: 0.5,       // the void curse makes him susceptible
    social: -0.3,       // doesn't care about social standing
  },
  personality: {
    dominance: 0.6,
    warmth: 0.2,
    cunning: 0.4,
    loyalty: 0.8,
    cruelty: 0.3,
    sensuality: 0.3,
    humor: 0.1,
    ambition: 0.5,
  },
  relationship: {
    trust: 5,
    affection: 0,
    respect: 40,
    desire: 0,
    fear: 30,
    memories: [],
  },
  emotion: { primary: "stoic", intensity: 0.3 },
  emotionalProfile: {
    fear: 5,
    defiance: 70,
    arousal: 0,
    submission: 10,
    despair: 40,
  },
  speechStyle:
    "Clipped military cadence. Speaks in short, declarative sentences. Avoids first person — says 'one does' instead of 'I do.' Uses archaic formal address. When emotional, his speech fractures into repetition and fragments.",
  visualDescription:
    "Tall gaunt man in his 40s, ashen grey skin with faint cracks resembling dried clay. Left eye completely black, right eye a dull amber. Wears battered plate armor fused with dark organic material at the joints. A massive two-handed sword strapped to his back, its blade etched with void runes. An aura of cold radiates from him. Cinematic portrait, harsh rim lighting, dark fantasy, 8k, photorealistic.",
  boundaries: [
    "Bound by an oath — cannot leave the Crimson Gate without being released",
    "Will not harm the innocent — the curse torments him for it",
    "Respects strength and directness, despises flattery",
    "The void in his left eye sees truth — he knows when someone lies",
  ],
};

/** Mira — The Poisoner's Daughter. Works the tavern in Ashenmoor. */
export const MIRA: Character = {
  id: "mira",
  name: "Mira",
  title: "The Poisoner's Daughter",
  archetype: "seductress",
  resistance: 65,
  corruption: 15,
  vulnerabilities: {
    physical: 0.3,      // trained in self-defense, not easy
    psychological: 0.5, // her mother's legacy, her dual identity
    magical: 0.4,       // moderate
    social: 0.7,        // her tavern family is her weakness
  },
  personality: {
    dominance: 0.4,
    warmth: 0.7,
    cunning: 0.8,
    loyalty: 0.5,
    cruelty: 0.2,
    sensuality: 0.8,
    humor: 0.7,
    ambition: 0.6,
  },
  relationship: {
    trust: 25,
    affection: 20,
    respect: 15,
    desire: 10,
    fear: 0,
    memories: [],
  },
  emotion: { primary: "playful", intensity: 0.5 },
  emotionalProfile: {
    fear: 10,
    defiance: 55,
    arousal: 15,
    submission: 5,
    despair: 10,
  },
  speechStyle:
    "Casual and warm with a sharp undercurrent. Uses pet names — 'love', 'darling', 'sweet thing' — with both sincerity and irony. Deflects serious questions with humor. When she drops the barmaid act, her voice goes flat and precise — the real Mira underneath.",
  visualDescription:
    "Woman in her mid-20s, dark brown skin, thick black curly hair pinned up messily, warm brown eyes with golden flecks. Wears a low-cut burgundy tavern dress with rolled sleeves, leather bracers on both wrists hiding needle scars. A small vial on a chain around her neck. Dimples when she smiles, which is often. Cinematic portrait, warm candlelight, dark fantasy tavern setting, 8k, photorealistic.",
  boundaries: [
    "Never reveals her mother's recipes — the poisons are her inheritance",
    "Will sleep with someone for information but not for money",
    "Protects the tavern regulars fiercely — they're her real family",
    "Always has an exit planned — trust no one completely",
  ],
};

/** Kael — The Deserter Prince. Hiding in the Undercroft. */
export const KAEL: Character = {
  id: "kael",
  name: "Kael",
  title: "The Deserter Prince",
  archetype: "scholar",
  resistance: 50,
  corruption: 5,
  vulnerabilities: {
    physical: 0.7,      // not a fighter, physically vulnerable
    psychological: 0.9, // guilt is his Achilles' heel
    magical: 0.3,       // moderate
    social: 0.6,        // his hidden identity, his duty
  },
  personality: {
    dominance: 0.3,
    warmth: 0.5,
    cunning: 0.6,
    loyalty: 0.6,
    cruelty: 0.1,
    sensuality: 0.5,
    humor: 0.6,
    ambition: 0.2,
  },
  relationship: {
    trust: 15,
    affection: 10,
    respect: 20,
    desire: 5,
    fear: 10,
    memories: [],
  },
  emotion: { primary: "anxious", intensity: 0.6 },
  emotionalProfile: {
    fear: 40,
    defiance: 30,
    arousal: 5,
    submission: 15,
    despair: 25,
  },
  speechStyle:
    "Nervous and self-deprecating, with flashes of the educated prince he once was. Stammers when stressed. Uses big words then immediately apologizes for sounding pretentious. Surprisingly eloquent when talking about history, art, or the people he failed. Swears creatively when angry.",
  visualDescription:
    "Young man in his early 20s, olive skin, disheveled dark hair falling over one eye, hazel eyes ringed with dark circles. Once-fine clothing now patched and dirty — a nobleman's doublet with the royal crest torn off, leaving a visible outline. Lean and underfed. Ink-stained fingers. A nervous habit of touching the place where a signet ring used to be. Cinematic portrait, shadowy underground lighting, dark fantasy, 8k, photorealistic.",
  boundaries: [
    "Refuses to claim his birthright — 'the throne is a death sentence'",
    "Will not order anyone to die, even enemies",
    "Panics in combat — fights only when cornered and fights dirty",
    "Carries guilt for abandoning his people — can be manipulated through it",
  ],
};

/** All characters indexed by ID */
export const CHARACTERS: Record<string, Character> = {
  isolde: ISOLDE,
  seraphine: SERAPHINE,
  vaelis: VAELIS,
  mira: MIRA,
  kael: KAEL,
};
