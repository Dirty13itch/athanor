/**
 * Harem Wars v6 — Jealousy Matrix and Rival Events
 *
 * When multiple queens are broken (corruption >= 70), they become aware
 * of each other and of the player's attention. Rivalry tension builds
 * based on jealousyType DNA and player behavior.
 *
 * Events are non-lethal and always resolve in sexual competition or
 * forced cooperation (from GDD Appendix A).
 *
 * Event types:
 * - catfight: hair-pulling, slapping, physical confrontation
 * - sabotage_nudes: one queen leaks compromising material on another
 * - false_accusation: political manipulation within the harem
 * - forced_kiss: QTE-style scene, rivals forced together
 * - competition_dance: rivalry pole/strip competition
 * - competition_scene: sexual competition for player's favor
 */

import type {
  Character,
  HaremWarsEvent,
  HaremWarsEventType,
  RivalryTension,
  DialogueTurn,
} from "@/types/game";
import { shouldTriggerHaremWars } from "@/types/game";

// ---------------------------------------------------------------------------
// Event Templates
// ---------------------------------------------------------------------------

/**
 * Build a Harem Wars event from two rival queens.
 * Scene and dialogue vary based on the instigator's archetype and DNA.
 */
export function buildHaremWarsEvent(
  instigator: Character,
  target: Character,
  tension: RivalryTension,
  sceneId: string
): HaremWarsEvent | null {
  // Determine event type based on instigator's DNA and tension level
  const eventType = selectEventType(instigator, tension.tension);
  if (!eventType) return null;

  const turns = buildEventTurns(eventType, instigator, target);
  if (turns.length === 0) return null;

  return {
    id: `haremwars_${instigator.id}_${target.id}_${eventType}_${Date.now()}`,
    type: eventType,
    instigatorId: instigator.id,
    targetId: target.id,
    tensionThreshold: getTensionThreshold(eventType),
    sceneId,
    turns,
  };
}

/**
 * Select the most appropriate event type for this instigator at this tension.
 */
function selectEventType(instigator: Character, tension: number): HaremWarsEventType | null {
  const dna = instigator.dna;
  if (!dna) return null;

  // High tension events
  if (tension >= 80) {
    if (dna.jealousyType === "possessive") return "catfight";
    if (dna.jealousyType === "competitive") return "competition_scene";
    return "forced_kiss";
  }

  // Medium-high tension
  if (tension >= 60) {
    if (dna.jealousyType === "possessive") return "sabotage_nudes";
    if (dna.jealousyType === "competitive") return "competition_dance";
    return "false_accusation";
  }

  // Medium tension
  if (tension >= 40) {
    if (dna.jealousyType === "turns-her-on") return "forced_kiss";
    return "competition_dance";
  }

  return null;
}

function getTensionThreshold(eventType: HaremWarsEventType): number {
  const thresholds: Record<HaremWarsEventType, number> = {
    catfight: 80,
    sabotage_nudes: 60,
    false_accusation: 60,
    forced_kiss: 40,
    competition_dance: 40,
    competition_scene: 60,
  };
  return thresholds[eventType];
}

// ---------------------------------------------------------------------------
// Event Dialogue Builders
// ---------------------------------------------------------------------------

function buildEventTurns(
  type: HaremWarsEventType,
  instigator: Character,
  target: Character
): DialogueTurn[] {
  switch (type) {
    case "catfight":
      return buildCatfightTurns(instigator, target);
    case "competition_dance":
      return buildCompetitionDanceTurns(instigator, target);
    case "competition_scene":
      return buildCompetitionSceneTurns(instigator, target);
    case "forced_kiss":
      return buildForcedKissTurns(instigator, target);
    case "sabotage_nudes":
      return buildSabotageTurns(instigator, target);
    case "false_accusation":
      return buildAccusationTurns(instigator, target);
    default:
      return [];
  }
}

function buildCatfightTurns(instigator: Character, target: Character): DialogueTurn[] {
  return [
    {
      speaker: "narrator",
      text: `*The tension that's been building for days finally snaps. ${instigator.name} moves across the room with purpose — not toward you, toward ${target.name}.*`,
    },
    {
      speaker: instigator.id,
      text: `*She grabs ${target.name}'s arm, voice low and controlled despite everything.* You think I don't see it? The way you position yourself. The way you look at him when you think no one's watching. We need to settle this.`,
      emotion: { primary: "intense", intensity: 0.9 },
    },
    {
      speaker: target.id,
      text: `*${target.name} doesn't pull away. She turns, meets the other woman's eyes. There's a beat of genuine rivalry — real, electric, charged with everything that's been unsaid.* Fine. You want to settle it? Let's settle it.`,
      emotion: { primary: "defiant", intensity: 0.8 },
    },
    {
      speaker: "narrator",
      text: `*They struggle — not gently, not playfully. This is real competition. Real anger. Real hunger. And underneath it all, the awareness that you're watching both of them. The catfight ends the way these things always end in a harem: pressed together, breathless, the anger dissolved into something more complicated.*`,
    },
    {
      speaker: instigator.id,
      text: `*Breathing hard, still not letting go, eyes on you.* ...I hate her. *A beat.* I also see why you keep her around.`,
      emotion: { primary: "conflicted", intensity: 0.7 },
      choices: [
        {
          text: `"You're both exactly what I want. That's the point."`,
          intent: "possessive_reframe",
          effects: { desire: 8, corruption: 5, trust: -3 },
        },
        {
          text: `*Say nothing. Let them figure it out.*`,
          intent: "dominant_silence",
          effects: { respect: 10, desire: 5, corruption: 3 },
        },
        {
          text: `"You're both jealous of something the other doesn't have. Come here."`,
          intent: "redirect_desire",
          effects: { desire: 12, corruption: 8, affection: 5 },
        },
      ],
    },
  ];
}

function buildCompetitionDanceTurns(instigator: Character, target: Character): DialogueTurn[] {
  return [
    {
      speaker: "narrator",
      text: `*It starts as tension and resolves itself, as things often do here, into spectacle. ${instigator.name} and ${target.name} at the pole together — not cooperating, competing. Each watching the other. Each performing for you.*`,
    },
    {
      speaker: instigator.id,
      text: `*She moves in a way she's calibrated to you specifically — everything she's learned about what makes you watch. Her eyes don't leave yours.* You don't need to compare us. *A deliberate pause, a spin, a landing.* There's no comparison to make.`,
      emotion: { primary: "competitive", intensity: 0.8 },
    },
    {
      speaker: target.id,
      text: `*${target.name} answers in movement rather than words — a sequence that's more honest, less calculated, and somehow more devastating for it. She's not trying to win. She's trying to be seen.*`,
      emotion: { primary: "vulnerable", intensity: 0.6 },
    },
    {
      speaker: "narrator",
      text: `*By the end neither of them is performing for the other anymore. They're both performing for you. The rivalry is still there — it probably always will be — but it's feeding something larger now.*`,
    },
    {
      speaker: instigator.id,
      text: `*Barely winded.* Well?`,
      emotion: { primary: "expectant", intensity: 0.5 },
      choices: [
        {
          text: `*Look at ${target.name}.* "She had something you didn't. But you had something she didn't."`,
          intent: "divide_and_rule",
          effects: { desire: 10, corruption: 6 },
        },
        {
          text: `"Both of you. Now."`,
          intent: "claim_both",
          effects: { desire: 15, corruption: 10, affection: 3 },
        },
        {
          text: `"I'm still deciding."`,
          intent: "withhold_verdict",
          effects: { respect: 12, fear: 5, desire: 5 },
        },
      ],
    },
  ];
}

function buildCompetitionSceneTurns(instigator: Character, target: Character): DialogueTurn[] {
  return [
    {
      speaker: "narrator",
      text: `*The competition between ${instigator.name} and ${target.name} has reached its natural terminus. There's nothing left to settle with words. They both know it. You know it.*`,
    },
    {
      speaker: instigator.id,
      text: `*She looks at ${target.name} for a long moment, then back at you. Something has shifted in her — the rivalry is still there but it's been redirected, focused.* One of us is going to ruin the other for you. *A beat.* I intend for it to be me.`,
      emotion: { primary: "determined", intensity: 0.9 },
      choices: [
        {
          text: `"Show me."`,
          intent: "accept_competition",
          effects: { desire: 15, corruption: 12, affection: 5 },
        },
        {
          text: `"You're both going to ruin each other. That's the game."`,
          intent: "reframe_as_game",
          effects: { respect: 10, desire: 10, corruption: 8 },
        },
        {
          text: `"I don't want competition. I want cooperation."`,
          intent: "redirect_to_cooperation",
          effects: { desire: 8, affection: 10, corruption: 5 },
        },
      ],
    },
  ];
}

function buildForcedKissTurns(instigator: Character, target: Character): DialogueTurn[] {
  return [
    {
      speaker: "narrator",
      text: `*There's a moment — just a moment — where the rivalry between ${instigator.name} and ${target.name} collapses into something else entirely. You see it before they do.*`,
    },
    {
      speaker: instigator.id,
      text: `*She's close to ${target.name}. Too close for it to be about fighting anymore. Her voice, when it comes, is unsteady.* I hate that I understand you. I hate that you're the only one here who actually gets it.`,
      emotion: { primary: "conflicted", intensity: 0.8 },
    },
    {
      speaker: target.id,
      text: `*${target.name} doesn't step back. She closes the remaining distance. What follows isn't gentle — it's the release of weeks of accumulated tension, confusion, and resentment. When they separate, both of them are looking at you.*`,
      emotion: { primary: "stunned", intensity: 0.7 },
      choices: [
        {
          text: `*Say nothing. Let them figure out what just happened.*`,
          intent: "observe",
          effects: { desire: 12, respect: 8, corruption: 5 },
        },
        {
          text: `"That's the most honest thing that's happened in this room all week."`,
          intent: "acknowledge",
          effects: { affection: 8, trust: 5, desire: 8 },
        },
        {
          text: `"Again. But this time I'm watching properly."`,
          intent: "command",
          effects: { desire: 15, fear: 5, corruption: 8 },
        },
      ],
    },
  ];
}

function buildSabotageTurns(instigator: Character, target: Character): DialogueTurn[] {
  return [
    {
      speaker: "narrator",
      text: `*It comes to you through a third party — a note, a whispered word, an anonymous message. ${instigator.name} has circulated something about ${target.name}. Something private. Something that was never supposed to leave a closed room.*`,
    },
    {
      speaker: instigator.id,
      text: `*When you find her, she doesn't deny it. She meets your eyes directly.* She was taking something that wasn't hers. I made sure she'd have a harder time doing it again. *A pause.* I'm not sorry.`,
      emotion: { primary: "calculating", intensity: 0.7 },
      choices: [
        {
          text: `"That was dangerous. For everyone, including you."`,
          intent: "warn",
          effects: { trust: -8, respect: 5, fear: 5 },
        },
        {
          text: `"Effective. Ruthless. I'm not sure whether to punish you or reward you."`,
          intent: "ambiguous_response",
          effects: { respect: 10, desire: 5, corruption: 5 },
        },
        {
          text: `*To both of them.* "The next one of you who does something like this without my knowledge answers for it."`,
          intent: "assert_control",
          effects: { fear: 10, respect: 15, corruption: 3 },
        },
      ],
    },
  ];
}

function buildAccusationTurns(instigator: Character, target: Character): DialogueTurn[] {
  return [
    {
      speaker: instigator.id,
      text: `*She comes to you with something that sounds reasonable until you start pulling the threads.* I need to tell you something about ${target.name}. I wouldn't bring it to you if I didn't think you needed to know. *The information she offers is technically true, framed very carefully.*`,
      emotion: { primary: "concerned", intensity: 0.6 },
      choices: [
        {
          text: `"I'll look into it. Thank you."`,
          intent: "accept_information",
          effects: { trust: -3, respect: 3 },
        },
        {
          text: `"You're the third person to come to me with something about a rival this week. I'm starting to see a pattern."`,
          intent: "call_out_pattern",
          effects: { respect: 12, trust: -8, fear: 8 },
        },
        {
          text: `*Pull her aside.* "I know what you're doing. It's clever. Don't do it again."`,
          intent: "private_warning",
          effects: { trust: 5, respect: 8, fear: 5, desire: 3 },
        },
      ],
    },
  ];
}

// ---------------------------------------------------------------------------
// Trigger Check
// ---------------------------------------------------------------------------

/**
 * Check all rivalry tensions and return events that should fire this scene.
 * Called on scene entry when multiple broken queens are present.
 */
export function checkHaremWarsEvents(
  characters: Record<string, Character>,
  tensions: RivalryTension[],
  availableEvents: HaremWarsEvent[],
  currentSceneId: string
): HaremWarsEvent[] {
  const toFire: HaremWarsEvent[] = [];

  for (const tension of tensions) {
    for (const event of availableEvents) {
      if (event.sceneId !== currentSceneId) continue;
      if (event.instigatorId !== tension.queenAId && event.instigatorId !== tension.queenBId) continue;
      if (shouldTriggerHaremWars(tension, event)) {
        toFire.push(event);
        break; // One event per tension pair per scene
      }
    }
  }

  // Return at most one event per scene entry to avoid overwhelming the player
  return toFire.slice(0, 1);
}
