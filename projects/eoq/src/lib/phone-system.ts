/**
 * Phone Obsession System — Post-breaking character messaging
 *
 * After a queen's Awakening fires (corruption >= 70), she begins sending
 * obsessive messages, missed calls, and voice notes to the player.
 *
 * Message frequency and content escalate with:
 * - addictionSpeed DNA trait (instant = immediate and relentless)
 * - jealousyType DNA trait (possessive = demanding, competitive = provocative)
 * - corruption level (80+ = explicit obsession, 95+ = complete fixation)
 *
 * From GDD: "Phone v12: Real-time texts, obsession messages"
 */

import type { Character, PhoneMessage, AddictionSpeed, JealousyType } from "@/types/game";

// ---------------------------------------------------------------------------
// Message templates per character archetype + DNA combination
// ---------------------------------------------------------------------------

interface MessageTemplate {
  text: string;
  type: "text" | "missed_call" | "voice_note";
  minCorruption: number;
  /** DNA traits that make this template more likely */
  preferredJealousy?: JealousyType[];
  preferredAddiction?: AddictionSpeed[];
}

/**
 * Generic templates applicable to any queen post-awakening.
 * Character-specific templates should override these via characterId lookup.
 */
const GENERIC_TEMPLATES: MessageTemplate[] = [
  // Early obsession (corruption 70-79)
  {
    text: "Are you busy? I find myself thinking about you.",
    type: "text",
    minCorruption: 70,
  },
  {
    text: "I don't know why I'm sending this.",
    type: "text",
    minCorruption: 70,
  },
  {
    text: "*missed call*",
    type: "missed_call",
    minCorruption: 70,
  },

  // Growing obsession (corruption 75-84)
  {
    text: "I keep replaying what happened. I shouldn't.",
    type: "text",
    minCorruption: 75,
  },
  {
    text: "Where are you?",
    type: "text",
    minCorruption: 75,
    preferredJealousy: ["possessive"],
  },
  {
    text: "Call me when you have time. Or don't. I don't care. *she clearly cares*",
    type: "text",
    minCorruption: 75,
    preferredJealousy: ["competitive"],
  },
  {
    text: "*voice note — breathing, then nothing, then she hangs up*",
    type: "voice_note",
    minCorruption: 78,
  },

  // Deep addiction (corruption 80-89)
  {
    text: "I did something embarrassing today. I thought of you and couldn't focus for an hour.",
    type: "text",
    minCorruption: 80,
  },
  {
    text: "I need to see you. Tonight if possible.",
    type: "text",
    minCorruption: 80,
    preferredAddiction: ["fast", "instant"],
  },
  {
    text: "*3 missed calls*",
    type: "missed_call",
    minCorruption: 80,
    preferredJealousy: ["possessive"],
  },
  {
    text: "You were with someone else today. I know it. Are you?",
    type: "text",
    minCorruption: 82,
    preferredJealousy: ["possessive", "competitive"],
  },
  {
    text: "I hate how much I want this.",
    type: "text",
    minCorruption: 83,
  },

  // Near-total fixation (corruption 90+)
  {
    text: "I woke up thinking about you. I went to sleep thinking about you. This is ridiculous and I don't care anymore.",
    type: "text",
    minCorruption: 90,
  },
  {
    text: "Tell me what to wear today.",
    type: "text",
    minCorruption: 90,
    preferredAddiction: ["instant"],
  },
  {
    text: "*voice note — 47 seconds of silence, then: 'I just wanted to hear if you'd pick up'*",
    type: "voice_note",
    minCorruption: 90,
  },
  {
    text: "I put on the thing you like. I don't know why. You're not even here.",
    type: "text",
    minCorruption: 92,
  },

  // Complete fixation (corruption 95+)
  {
    text: "Everything I do, I'm thinking about whether you'd approve. I didn't ask to be like this.",
    type: "text",
    minCorruption: 95,
  },
  {
    text: "*7 missed calls*",
    type: "missed_call",
    minCorruption: 95,
    preferredJealousy: ["possessive"],
  },
  {
    text: "I'm yours. I've known it for a while. I just needed to say it out loud.",
    type: "text",
    minCorruption: 95,
  },
];

/**
 * Character-specific message templates.
 * These override or supplement generic templates based on character identity.
 */
const CHARACTER_TEMPLATES: Record<string, MessageTemplate[]> = {
  isolde: [
    {
      text: "This is beneath me. I'm aware of that. *four minutes later* Are you awake?",
      type: "text",
      minCorruption: 70,
    },
    {
      text: "I had three meetings today. I found excuses to mention your name in all of them. I'm disgusted with myself.",
      type: "text",
      minCorruption: 80,
    },
    {
      text: "The court thinks I'm becoming distracted. They're right. I blame you.",
      type: "text",
      minCorruption: 85,
    },
    {
      text: "I've stopped pretending this is anything other than what it is. Tell me when you're coming.",
      type: "text",
      minCorruption: 92,
    },
    {
      text: "*voice note — controlled breathing, then the voice that's not quite the queen's: 'I miss you. Don't make me say it again.'*",
      type: "voice_note",
      minCorruption: 95,
    },
  ],
  mira: [
    {
      text: "So. You broke me a little. Just so you know.",
      type: "text",
      minCorruption: 70,
    },
    {
      text: "I poured someone else's drink tonight and thought of you. Put twice as much in it. Didn't charge them.",
      type: "text",
      minCorruption: 75,
    },
    {
      text: "The regulars keep asking what's gotten into me. I keep saying nothing. They don't believe me. Love, when are you coming back?",
      type: "text",
      minCorruption: 82,
    },
    {
      text: "I made the drink you like. Just left it on the bar. In case.",
      type: "text",
      minCorruption: 88,
    },
    {
      text: "*voice note — tavern background noise, then quiet: 'You're the only secret I don't know how to keep, darling.'*",
      type: "voice_note",
      minCorruption: 94,
    },
  ],
  seraphine: [
    {
      text: "I saw three futures today. You were in all of them. I stopped trying to look away.",
      type: "text",
      minCorruption: 70,
    },
    {
      text: "The orb won't stop showing me you. I'm starting to think that's a message.",
      type: "text",
      minCorruption: 76,
    },
    {
      text: "*missed call* *missed call*",
      type: "missed_call",
      minCorruption: 81,
    },
    {
      text: "In every future I looked for, you came back. I've decided to stop looking and just wait.",
      type: "text",
      minCorruption: 88,
    },
    {
      text: "*voice note — crystalline quality to her voice: 'I dreamed of you. Not a vision. Just a dream. It was the best I've had in years.'*",
      type: "voice_note",
      minCorruption: 93,
    },
  ],
};

// ---------------------------------------------------------------------------
// Message Generation
// ---------------------------------------------------------------------------

/**
 * Select appropriate phone messages for a character based on their current
 * corruption level and DNA traits.
 *
 * Returns messages appropriate for the current game day.
 * Called by the day-advance logic in use-game-engine.
 */
export function generatePhoneMessages(
  character: Character,
  currentDay: number,
  alreadySentMessages: PhoneMessage[]
): PhoneMessage[] {
  if (!character.awakeningFired || character.corruption < 70) return [];
  if (!character.dna) return [];

  const { addictionSpeed, jealousyType } = character.dna;
  const corruption = character.corruption;

  // How many messages per day based on addiction speed
  const messagesPerDay: Record<string, number> = {
    very_slow: 0.3,  // one every ~3 days
    slow: 0.5,       // one every ~2 days
    normal: 1,       // one per day
    fast: 2,         // two per day
    instant: 3,      // three per day at peak
  };

  const targetCount = Math.floor(messagesPerDay[addictionSpeed] * (corruption >= 90 ? 1.5 : 1));
  if (targetCount === 0 && Math.random() > messagesPerDay[addictionSpeed]) return [];

  // Get eligible templates
  const charTemplates = CHARACTER_TEMPLATES[character.id] ?? [];
  const allTemplates = [...charTemplates, ...GENERIC_TEMPLATES];

  const eligible = allTemplates.filter((t) => {
    // Check corruption threshold
    if (corruption < t.minCorruption) return false;
    // Check if already sent (compare text)
    if (alreadySentMessages.some((m) => m.text === t.text)) return false;
    return true;
  });

  // Weight templates by DNA affinity
  const weighted = eligible.map((t) => {
    let weight = 1;
    if (t.preferredJealousy?.includes(jealousyType)) weight += 2;
    if (t.preferredAddiction?.includes(addictionSpeed)) weight += 2;
    // Character-specific templates get 2x weight
    if (CHARACTER_TEMPLATES[character.id]?.includes(t)) weight += 1;
    return { template: t, weight };
  });

  // Select messages by weighted random
  const selected: PhoneMessage[] = [];
  const shuffled = weightedShuffle(weighted);

  for (let i = 0; i < Math.min(targetCount, shuffled.length); i++) {
    const t = shuffled[i].template;
    selected.push({
      characterId: character.id,
      day: currentDay,
      text: t.text,
      type: t.type,
      minCorruption: t.minCorruption,
    });
  }

  return selected;
}

/**
 * Weighted shuffle — higher weight items appear earlier.
 */
function weightedShuffle<T extends { weight: number }>(items: T[]): T[] {
  return [...items]
    .map((item) => ({ item, sort: Math.random() * item.weight }))
    .sort((a, b) => b.sort - a.sort)
    .map((x) => x.item);
}

// ---------------------------------------------------------------------------
// Day Advance Hook
// ---------------------------------------------------------------------------

/**
 * Called when the game advances to a new day.
 * Generates any phone messages due and returns them for the store.
 */
export function advanceDayPhoneMessages(
  characters: Record<string, Character>,
  currentDay: number,
  existingMessages: PhoneMessage[]
): PhoneMessage[] {
  const newMessages: PhoneMessage[] = [];

  for (const char of Object.values(characters)) {
    if (!char.awakeningFired || char.corruption < 70) continue;
    const charExisting = existingMessages.filter((m) => m.characterId === char.id);
    const dayMessages = generatePhoneMessages(char, currentDay, charExisting);
    newMessages.push(...dayMessages);
  }

  return newMessages;
}
