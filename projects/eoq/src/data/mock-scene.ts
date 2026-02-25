import type { Character, GameSession, SceneDefinition, DialogueTurn } from "@/types/game";

/** Mock character: Isolde, a cunning queen with a dark past */
export const ISOLDE: Character = {
  id: "isolde",
  name: "Isolde",
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
  emotion: {
    primary: "calculating",
    intensity: 0.6,
  },
  speechStyle:
    "Formal and precise, with occasional cutting wit. Uses royal 'we' when asserting authority. Drops the facade when caught off-guard.",
  visualDescription:
    "Regal woman in her 30s, sharp features, dark auburn hair in elaborate braids, pale skin, ice-blue eyes. Wears a black and gold gown with high collar. A thin scar runs from her left ear to her jaw.",
  boundaries: [
    "Will not beg — she commands or manipulates",
    "Will not reveal her true feelings easily",
    "Will use intimacy as a tool, not a gift",
  ],
};

export const THRONE_ROOM: SceneDefinition = {
  id: "throne-room",
  name: "The Shattered Throne Room",
  description:
    "The throne room of Ashenmoor Keep, half-destroyed by the siege. Moonlight streams through a collapsed wall, illuminating rubble-strewn marble floors. The iron throne remains — scarred but standing. Isolde sits upon it, watching you approach through hooded eyes.",
  visualPrompt:
    "dark fantasy throne room, collapsed wall revealing moonlit sky, rubble on marble floor, iron throne with seated regal woman, gothic architecture, dramatic lighting, cinematic, 8k",
  presentCharacters: ["isolde"],
  exits: [
    { label: "Leave through the broken wall", targetSceneId: "courtyard" },
    { label: "Approach the throne", targetSceneId: "throne-close" },
  ],
};

/** Pre-scripted dialogue for mock mode */
export const MOCK_DIALOGUE: DialogueTurn[] = [
  {
    speaker: "narrator",
    text: "The air smells of ash and old stone. Your boots crunch over broken marble as you enter what remains of the throne room. At the far end, a figure watches you from the iron throne.",
  },
  {
    speaker: "isolde",
    text: "You took your time. I was beginning to wonder if the siege had claimed you as well.",
    emotion: { primary: "calculating", intensity: 0.6 },
    choices: [
      {
        text: "\"I came as soon as I could, Your Grace.\"",
        intent: "respectful",
        effects: { respect: 5, trust: 3 },
      },
      {
        text: "\"The dead don't keep schedules.\"",
        intent: "dark_humor",
        effects: { respect: -5, affection: 5 },
      },
      {
        text: "\"I'm here for what you promised me.\"",
        intent: "demanding",
        effects: { fear: -5, respect: 10, trust: -5 },
      },
    ],
  },
  {
    speaker: "isolde",
    text: "Interesting. You have spine, at least. That's more than can be said for the last three who stood where you are now.",
    emotion: { primary: "amused", intensity: 0.4 },
  },
  {
    speaker: "isolde",
    text: "The kingdom is fractured. Five provinces, five pretenders, and not one of them with the wit to hold what they've taken. I need someone who understands that power is not seized — it is grown.",
    emotion: { primary: "intense", intensity: 0.8 },
    choices: [
      {
        text: "\"And you think I'm that someone?\"",
        intent: "curious",
        effects: { trust: 5 },
      },
      {
        text: "\"What's in it for me?\"",
        intent: "mercenary",
        effects: { trust: -3, respect: 5 },
      },
      {
        text: "\"I've seen what your kind of power costs.\"",
        intent: "challenging",
        effects: { respect: 15, affection: 5, fear: -10 },
      },
    ],
  },
];

/** Create a fresh game session with mock data */
export function createMockSession(): GameSession {
  return {
    id: crypto.randomUUID(),
    startedAt: Date.now(),
    lastPlayedAt: Date.now(),
    worldState: {
      currentScene: THRONE_ROOM,
      timeOfDay: "night",
      day: 1,
      plotFlags: {},
      inventory: [],
    },
    characters: {
      isolde: ISOLDE,
    },
    dialogueHistory: [],
    arcPosition: "prologue",
  };
}
