/**
 * Empire News Network (ENN) — In-game news system
 *
 * Generates contextual news headlines and broadcasts based on
 * current game state: plot flags, queen resistance levels, player
 * style, and arc position. News appears as atmospheric flavor
 * text and can foreshadow events or reflect consequences.
 */

import type { GameSession } from "@/types/game";
import { getBreakingStage } from "@/types/game";

export interface NewsItem {
  headline: string;
  body: string;
  source: string; // "ENN", "Ashenmoor Herald", "Crimson Gate Watch", etc.
  tone: "neutral" | "ominous" | "hopeful" | "fearful" | "propagandist";
  priority: number; // 0-10, higher = more prominent
}

/**
 * Generate contextual news items based on current game state.
 * Returns 2-4 headlines relevant to what the player has done.
 */
export function generateNews(session: GameSession): NewsItem[] {
  const { worldState, characters, arcPosition, playerStyle } = session;
  const flags = worldState.plotFlags;
  const news: NewsItem[] = [];

  // --- Arc-based news ---

  if (arcPosition === "prologue") {
    news.push({
      headline: "Stranger Arrives at Ashenmoor",
      body: "A lone traveler has entered the ruined capital. The garrison watches with suspicion. Queen Isolde has made no public statement.",
      source: "Ashenmoor Herald",
      tone: "neutral",
      priority: 3,
    });
  }

  if (arcPosition === "gathering_allies") {
    news.push({
      headline: "Newcomer Makes Rounds Among Key Figures",
      body: "The stranger has been seen visiting the tavern, the tunnels, and even the Crimson Gate. Some call it diplomacy. Others call it reconnaissance.",
      source: "ENN",
      tone: "ominous",
      priority: 5,
    });
  }

  if (flags.chose_serve_isolde) {
    news.push({
      headline: "Queen's New Right Hand Announced",
      body: "In a rare public address, Queen Isolde presented her new advisor to the court. 'Ashenmoor needs unity,' she declared. 'And unity requires a sharp blade.'",
      source: "Royal Decree",
      tone: "propagandist",
      priority: 8,
    });
  }

  if (flags.chose_defy_isolde) {
    news.push({
      headline: "Tension in the Throne Room",
      body: "Witnesses report a heated exchange between Queen Isolde and the stranger. The royal guard has been doubled. The queen's mood is described as 'volcanic.'",
      source: "Ashenmoor Herald",
      tone: "fearful",
      priority: 8,
    });
  }

  if (flags.mira_confession_heard) {
    news.push({
      headline: "Old Rumors Resurface About the Succession",
      body: "Whispers in the Broken Antler speak of poison, of a king who knew his end was coming, of a tavern keeper's mother who brewed more than ale. The truth, as always, is served cold.",
      source: "Tavern Gossip",
      tone: "ominous",
      priority: 6,
    });
  }

  // --- Queen-based news ---

  const brokenQueens = Object.values(characters).filter(
    (c) => c.resistance === 0,
  );
  if (brokenQueens.length >= 1) {
    news.push({
      headline: `${brokenQueens[0].name} Seen in Complete Submission`,
      body: `Former ${brokenQueens[0].title ?? "queen"} ${brokenQueens[0].name} was seen kneeling in the corridors. Those who knew her before say the person they remember is gone.`,
      source: "Court Observer",
      tone: "fearful",
      priority: 7,
    });
  }

  if (brokenQueens.length >= 5) {
    news.push({
      headline: "The Empire Trembles — Five Queens Broken",
      body: "The conqueror's campaign of domination has claimed five royal wills. The remaining queens watch with a mixture of defiance and dread. Some have begun making contingency plans.",
      source: "ENN",
      tone: "ominous",
      priority: 9,
    });
  }

  // Average resistance across all queens
  const queenEntries = Object.values(characters);
  if (queenEntries.length > 3) {
    const avgRes = queenEntries.reduce((s, c) => s + c.resistance, 0) / queenEntries.length;
    if (avgRes < 30) {
      news.push({
        headline: "Resistance Crumbles Across the Empire",
        body: "With average resistance below 30%, historians note this as the fastest conquest in recorded memory. The question is no longer whether the queens will fall — but what the conqueror will do with them.",
        source: "Imperial Chronicler",
        tone: "ominous",
        priority: 9,
      });
    }
  }

  // --- Player style news ---

  if (playerStyle && playerStyle.totalChoices > 10) {
    if (playerStyle.mercyScore < 20) {
      news.push({
        headline: "The Tyrant of Ashenmoor",
        body: "They don't call the conqueror by name anymore. They call them 'The Tyrant.' Children are hushed with the threat. Guards avoid eye contact. The tavern falls silent when the door opens.",
        source: "Ashenmoor Herald",
        tone: "fearful",
        priority: 7,
      });
    } else if (playerStyle.mercyScore > 75) {
      news.push({
        headline: "A Different Kind of Conqueror",
        body: "Against all expectations, the stranger shows mercy. The queens whisper about it — some with suspicion, others with something they haven't felt in a long time. Hope is a dangerous thing in Ashenmoor.",
        source: "Court Observer",
        tone: "hopeful",
        priority: 6,
      });
    }

    if (playerStyle.seductionScore > 60) {
      news.push({
        headline: "Court Scandals Multiply",
        body: "The conqueror's methods are... unconventional. Multiple queens have been seen leaving private audiences with flushed faces and downcast eyes. The court is equal parts scandalized and fascinated.",
        source: "Tavern Gossip",
        tone: "neutral",
        priority: 5,
      });
    }
  }

  // --- Act 2 news ---

  if (flags.crossed_crimson_gate) {
    news.push({
      headline: "The Gate Has Been Crossed",
      body: "For the first time in four centuries, a living soul has passed beyond the Crimson Gate. Vaelis, the eternal guardian, stands aside. What lies in the Hollowlands is no longer a mystery — it's a destination.",
      source: "Crimson Gate Watch",
      tone: "ominous",
      priority: 10,
    });
  }

  if (flags.ember_blood_recognized) {
    news.push({
      headline: "Ancient Blood Awakens in the Hollowlands",
      body: "Reports from beyond the Gate speak of creatures that recognize the conqueror's bloodline. The ember-born, servants of a forgotten fire, stir for the first time in millennia.",
      source: "ENN",
      tone: "ominous",
      priority: 9,
    });
  }

  // Sort by priority, return top 4
  return news
    .sort((a, b) => b.priority - a.priority)
    .slice(0, 4);
}
