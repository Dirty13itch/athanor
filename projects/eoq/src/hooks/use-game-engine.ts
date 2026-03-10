"use client";

import { useCallback, useRef } from "react";
import { useGameStore } from "@/stores/game-store";
import { CHARACTERS } from "@/data/characters";
import { SCENES, STARTING_SCENE, SCENE_INTROS } from "@/data/scenes";
import {
  getScriptedIntro,
  getTriggeredEvent,
  checkCondition,
  checkRelationshipFlags,
  checkArcTransition,
} from "@/data/narrative";
import type { PlayerChoice, DialogueTurn, SceneExit, ChoiceEffects } from "@/types/game";

/**
 * Game engine hook — manages dialogue flow, scene navigation,
 * scripted intros, LLM streaming, choice effects, and breaking system.
 */
export function useGameEngine() {
  const store = useGameStore();
  const scriptedQueueRef = useRef<DialogueTurn[]>([]);
  const scriptedIndexRef = useRef(0);

  /** Start a new game */
  const startGame = useCallback(() => {
    const startScene = SCENES[STARTING_SCENE];
    if (!startScene) return;

    const session = {
      id: crypto.randomUUID(),
      startedAt: Date.now(),
      lastPlayedAt: Date.now(),
      worldState: {
        currentScene: startScene,
        timeOfDay: "night" as const,
        day: 1,
        plotFlags: {},
        inventory: [],
        contentIntensity: 3 as const,
      },
      characters: { ...CHARACTERS },
      dialogueHistory: [],
      arcPosition: "prologue",
    };

    store.setSession(session);
    store.markSceneVisited(STARTING_SCENE);

    // Play the courtyard narrator intro
    const intro = SCENE_INTROS[STARTING_SCENE];
    if (intro) {
      setTimeout(() => {
        playNarratorLine(intro);
      }, 500);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Navigate to a different scene */
  const changeScene = useCallback(
    (exit: SceneExit) => {
      const { session } = useGameStore.getState();
      if (!session) return;

      // Check condition
      if (!checkCondition(exit.condition, session.worldState.plotFlags)) {
        store.addDialogue({
          speaker: "narrator",
          text: "*The path is not yet open to you.*",
        });
        return;
      }

      const targetScene = SCENES[exit.targetSceneId];
      if (!targetScene) return;

      // Advance time when moving between scenes
      const newTime = advanceTime(session.worldState.timeOfDay);
      const dayAdvanced = newTime.wrapped;

      // Update world state
      store.updateWorldState({
        currentScene: targetScene,
        timeOfDay: newTime.time,
        ...(dayAdvanced ? { day: session.worldState.day + 1 } : {}),
      });

      // Clear portrait when leaving a character scene
      store.setPortraitUrl(null);

      // Add transition narration
      store.addDialogue({
        speaker: "narrator",
        text: `*You ${exit.label.toLowerCase()}.*`,
      });

      // Mark scene visited
      const { visitedScenes } = useGameStore.getState();
      const isFirstVisit = !visitedScenes.has(exit.targetSceneId);
      store.markSceneVisited(exit.targetSceneId);

      // Play scene intro
      setTimeout(() => {
        const updatedSession = useGameStore.getState().session;
        if (!updatedSession) return;

        // Try scripted intro first (first visit only)
        if (isFirstVisit) {
          const scripted = getScriptedIntro(
            exit.targetSceneId,
            updatedSession.worldState.plotFlags
          );
          if (scripted) {
            // Mark intro as played
            store.setPlotFlag(`intro_played_${exit.targetSceneId}`, true);
            // Queue the scripted sequence
            scriptedQueueRef.current = scripted;
            scriptedIndexRef.current = 0;
            playNextScripted();
            return;
          }
        }

        // Check for triggered events (arc-based, not first-visit)
        const triggered = getTriggeredEvent(
          exit.targetSceneId,
          updatedSession.arcPosition,
          updatedSession.worldState.plotFlags
        );
        if (triggered) {
          const eventKey = `${exit.targetSceneId}:${updatedSession.arcPosition}`;
          store.setPlotFlag(`event_played_${eventKey}`, true);
          scriptedQueueRef.current = triggered;
          scriptedIndexRef.current = 0;
          playNextScripted();
          return;
        }

        // Fall back to narrator scene description
        const sceneNarration = SCENE_INTROS[exit.targetSceneId];
        if (sceneNarration) {
          playNarratorLine(sceneNarration);
        }
      }, 400);

      // Auto-save
      setTimeout(() => store.saveGame(), 1000);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  /** Play a narrator line with simulated streaming */
  const playNarratorLine = useCallback(
    (text: string) => {
      store.setGenerating(true);
      store.setStreamingText("");

      let charIndex = 0;
      const interval = setInterval(() => {
        if (charIndex < text.length) {
          store.appendStreamingText(text[charIndex]);
          charIndex++;
        } else {
          clearInterval(interval);
          store.setGenerating(false);
          store.addDialogue({ speaker: "narrator", text });
        }
      }, 15);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  /** Play the next turn in a scripted sequence */
  const playNextScripted = useCallback(() => {
    const turn = scriptedQueueRef.current[scriptedIndexRef.current];
    if (!turn) {
      scriptedQueueRef.current = [];
      scriptedIndexRef.current = 0;
      return;
    }

    store.setGenerating(true);
    store.setStreamingText("");

    const text = turn.text;
    let charIndex = 0;
    const interval = setInterval(() => {
      if (charIndex < text.length) {
        store.appendStreamingText(text[charIndex]);
        charIndex++;
      } else {
        clearInterval(interval);
        store.setGenerating(false);
        store.addDialogue(turn);
        scriptedIndexRef.current++;

        // If no choices on this turn, auto-advance to next scripted
        if (!turn.choices && scriptedIndexRef.current < scriptedQueueRef.current.length) {
          setTimeout(() => playNextScripted(), 800);
        }
      }
    }, 15);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Advance dialogue — either play next scripted turn or call LLM */
  const advanceDialogue = useCallback(() => {
    // If we have queued scripted turns, play next
    if (scriptedIndexRef.current < scriptedQueueRef.current.length) {
      playNextScripted();
      return;
    }

    // Otherwise, call the LLM for freeform dialogue
    advanceLive();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Handle player choosing a dialogue option */
  const handleChoice = useCallback(
    (choice: PlayerChoice) => {
      const { session } = useGameStore.getState();
      if (!session) return;

      // Record the player's choice
      store.addDialogue({ speaker: "player", text: choice.text });

      // Apply all effects
      if (choice.effects) {
        applyChoiceEffects(choice.effects, session.worldState.currentScene.presentCharacters);
      }

      // Check if relationship changes unlock new flags
      const updatedSession = useGameStore.getState().session;
      if (updatedSession) {
        const relFlags = checkRelationshipFlags(
          updatedSession.characters
        );
        if (Object.keys(relFlags).length > 0) {
          store.setPlotFlags(relFlags);
        }

        // Check arc transitions
        const newArc = checkArcTransition(
          updatedSession.arcPosition,
          updatedSession.worldState.plotFlags
        );
        if (newArc) {
          store.setSession({
            ...updatedSession,
            arcPosition: newArc,
            worldState: {
              ...updatedSession.worldState,
              plotFlags: {
                ...updatedSession.worldState.plotFlags,
                ...relFlags,
              },
            },
          });
        }
      }

      // Store significant memories to Qdrant (fire and forget)
      if (choice.effects) {
        const totalImpact =
          Math.abs(choice.effects.trust ?? 0) +
          Math.abs(choice.effects.affection ?? 0) +
          Math.abs(choice.effects.respect ?? 0) +
          Math.abs(choice.effects.resistance ?? 0);
        if (totalImpact >= 10) {
          const presentChars = session.worldState.currentScene.presentCharacters;
          for (const charId of presentChars) {
            storeMemory(charId, session.id, choice, session.worldState.currentScene.name);
          }
        }
      }

      // Continue dialogue
      setTimeout(() => advanceDialogue(), 300);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  /**
   * Apply choice effects to all present characters.
   * Handles relationship, resistance, corruption, emotional shifts, and plot flags.
   */
  function applyChoiceEffects(effects: ChoiceEffects, presentCharacters: string[]) {
    const { session } = useGameStore.getState();
    if (!session) return;

    for (const charId of presentCharacters) {
      const char = session.characters[charId];
      if (!char) continue;

      // Relationship effects
      const rel = { ...char.relationship };
      if (effects.trust)
        rel.trust = clamp(rel.trust + effects.trust, -100, 100);
      if (effects.affection)
        rel.affection = clamp(rel.affection + effects.affection, -100, 100);
      if (effects.respect)
        rel.respect = clamp(rel.respect + effects.respect, -100, 100);
      if (effects.desire)
        rel.desire = clamp(rel.desire + effects.desire, 0, 100);
      if (effects.fear)
        rel.fear = clamp(rel.fear + effects.fear, 0, 100);

      // Resistance/corruption effects (breaking system)
      let resistance = char.resistance;
      let corruption = char.corruption;
      if (effects.resistance) {
        resistance = clamp(resistance + effects.resistance, 0, 100);
      }
      if (effects.corruption) {
        corruption = clamp(corruption + effects.corruption, 0, 100);
      }

      // Emotional profile shifts
      const ep = { ...char.emotionalProfile };
      if (effects.emotionalShifts) {
        const shifts = effects.emotionalShifts;
        if (shifts.fear != null) ep.fear = clamp(ep.fear + shifts.fear, 0, 100);
        if (shifts.defiance != null) ep.defiance = clamp(ep.defiance + shifts.defiance, 0, 100);
        if (shifts.arousal != null) ep.arousal = clamp(ep.arousal + shifts.arousal, 0, 100);
        if (shifts.submission != null) ep.submission = clamp(ep.submission + shifts.submission, 0, 100);
        if (shifts.despair != null) ep.despair = clamp(ep.despair + shifts.despair, 0, 100);
      }

      // Add memory for significant choices
      const totalImpact =
        Math.abs(effects.trust ?? 0) +
        Math.abs(effects.affection ?? 0) +
        Math.abs(effects.respect ?? 0) +
        Math.abs(effects.resistance ?? 0);
      if (totalImpact >= 10) {
        rel.memories = [
          ...rel.memories,
          {
            timestamp: Date.now(),
            summary: `Player chose: "${truncate(effects.plotFlags ? Object.keys(effects.plotFlags).join(", ") : "unknown", 60)}" (impact: ${totalImpact})`,
            emotionalImpact: totalImpact > 0 ? Math.min(totalImpact / 5, 10) : -Math.min(totalImpact / 5, 10),
          },
        ];
      }

      store.updateCharacter(charId, {
        relationship: rel,
        resistance,
        corruption,
        emotionalProfile: ep,
      });
    }

    // Apply plot flag effects
    if (effects.plotFlags) {
      store.setPlotFlags(effects.plotFlags);
    }

    // Grant items
    if (effects.itemGrants) {
      for (const item of effects.itemGrants) {
        store.addInventoryItem(item);
      }
    }
  }

  /** Stream dialogue from the live LLM API */
  const advanceLive = useCallback(async () => {
    const { session } = useGameStore.getState();
    if (!session) return;

    store.setGenerating(true);
    store.setStreamingText("");

    try {
      const presentChars = session.worldState.currentScene.presentCharacters;
      const currentCharId = presentChars[0];

      // If no character present, generate atmospheric narration via LLM
      if (!currentCharId) {
        try {
          const narResp = await fetch("/api/narrate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              worldState: session.worldState,
              recentHistory: session.dialogueHistory.slice(-4),
            }),
          });

          if (narResp.ok && narResp.body) {
            const reader = narResp.body.getReader();
            const decoder = new TextDecoder();
            let narText = "";

            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              const chunk = decoder.decode(value, { stream: true });
              for (const line of chunk.split("\n")) {
                if (!line.startsWith("data: ") || line === "data: [DONE]") continue;
                try {
                  const data = JSON.parse(line.slice(6));
                  const content = data.choices?.[0]?.delta?.content;
                  if (content) {
                    narText += content;
                    store.appendStreamingText(content);
                  }
                } catch { /* skip */ }
              }
            }

            narText = narText.replace(/<think>[\s\S]*?<\/think>/g, "").trim();
            if (narText) {
              store.addDialogue({ speaker: "narrator", text: narText });
            }
          } else {
            // Fallback to static description
            const sceneDesc = session.worldState.currentScene.description;
            playNarratorLine(sceneDesc || "The silence here feels intentional.");
          }
        } catch {
          const sceneDesc = session.worldState.currentScene.description;
          playNarratorLine(sceneDesc || "The silence here feels intentional.");
        }
        store.setGenerating(false);
        return;
      }

      const character = session.characters[currentCharId];
      if (!character) {
        store.setGenerating(false);
        return;
      }

      const recentHistory = session.dialogueHistory.slice(-10);
      const lastPlayerTurn = [...recentHistory]
        .reverse()
        .find((t) => t.speaker === "player");

      const resp = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          character,
          worldState: session.worldState,
          recentHistory,
          playerInput:
            lastPlayerTurn?.text ?? "[The player approaches in silence.]",
        }),
      });

      if (!resp.ok || !resp.body) {
        throw new Error(`API error: ${resp.status}`);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let fullText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (!line.startsWith("data: ") || line === "data: [DONE]") continue;
          try {
            const data = JSON.parse(line.slice(6));
            const content = data.choices?.[0]?.delta?.content;
            if (content) {
              fullText += content;
              store.appendStreamingText(content);
            }
          } catch {
            // Skip malformed SSE lines
          }
        }
      }

      // Strip any <think> blocks that might leak through
      fullText = fullText.replace(/<think>[\s\S]*?<\/think>/g, "").trim();

      const turn: DialogueTurn = {
        speaker: currentCharId,
        text: fullText,
      };
      store.addDialogue(turn);

      // Infer emotion from the response and update character state
      const inferredEmotion = inferEmotion(fullText);
      if (inferredEmotion) {
        store.updateCharacter(currentCharId, { emotion: inferredEmotion });
      }

      // Generate contextual choices for the player (fire and forget into state)
      fetchChoices(character, session.worldState, session.dialogueHistory.slice(-10));

      // Auto-save periodically
      store.saveGame();
    } catch (err) {
      console.error("Dialogue generation failed:", err);
      store.addDialogue({
        speaker: "narrator",
        text: "*The words fade into silence. Something went wrong with the connection.*",
      });
    } finally {
      store.setGenerating(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Load a saved game */
  const loadSavedGame = useCallback(() => {
    return store.loadGame();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Check if a saved game exists */
  const hasSavedGame = useCallback(() => {
    try {
      return localStorage.getItem("eoq-save") !== null;
    } catch {
      return false;
    }
  }, []);

  /** Get available exits from current scene, filtered by conditions */
  const getAvailableExits = useCallback((): SceneExit[] => {
    const { session } = useGameStore.getState();
    if (!session) return [];

    return session.worldState.currentScene.exits.filter((exit) =>
      checkCondition(exit.condition, session.worldState.plotFlags)
    );
  }, []);

  /** Send freeform player text and trigger LLM response */
  const sendPlayerMessage = useCallback(
    (text: string) => {
      const { session } = useGameStore.getState();
      if (!session) return;

      // Record the player's message
      store.addDialogue({ speaker: "player", text });

      // Trigger LLM response after a short beat
      setTimeout(() => advanceLive(), 200);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  return {
    startGame,
    advanceDialogue,
    handleChoice,
    sendPlayerMessage,
    changeScene,
    loadSavedGame,
    hasSavedGame,
    getAvailableExits,
  };
}

/** Fetch LLM-generated choices and attach to the last dialogue turn */
function fetchChoices(
  character: import("@/types/game").Character,
  worldState: import("@/types/game").WorldState,
  recentHistory: DialogueTurn[]
) {
  fetch("/api/choices", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ character, worldState, recentHistory }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.choices && data.choices.length > 0) {
        useGameStore.getState().attachChoicesToLastTurn(data.choices);
      }
    })
    .catch(() => {
      // Choice generation is best-effort — player can always type freeform
    });
}

/** Store a significant memory to Qdrant (fire and forget) */
function storeMemory(
  characterId: string,
  sessionId: string,
  choice: PlayerChoice,
  sceneName: string
) {
  const text = `Player chose: "${choice.text}" (intent: ${choice.intent}) in ${sceneName}`;
  fetch("/api/memory", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      characterId,
      sessionId,
      text,
      metadata: {
        intent: choice.intent,
        breaking_method: choice.breakingMethod,
        scene: sceneName,
      },
    }),
  }).catch(() => {
    // Memory storage is best-effort
  });
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function truncate(str: string, maxLen: number): string {
  return str.length > maxLen ? str.slice(0, maxLen - 1) + "…" : str;
}

/** Time of day progression cycle */
const TIME_ORDER: Array<"dawn" | "morning" | "afternoon" | "dusk" | "evening" | "night"> = [
  "dawn", "morning", "afternoon", "dusk", "evening", "night",
];

/** Advance to the next time of day. Returns wrapped=true if a new day starts. */
function advanceTime(current: typeof TIME_ORDER[number]): { time: typeof TIME_ORDER[number]; wrapped: boolean } {
  const idx = TIME_ORDER.indexOf(current);
  const nextIdx = (idx + 1) % TIME_ORDER.length;
  return {
    time: TIME_ORDER[nextIdx],
    wrapped: nextIdx === 0,
  };
}

/**
 * Infer character emotion from LLM response text using keyword analysis.
 * Looks at italicized actions and emotional language to determine mood.
 */
function inferEmotion(text: string): { primary: string; intensity: number; secondary?: string } | null {
  const lower = text.toLowerCase();

  // Extract italicized actions for stronger signal
  const actions = (text.match(/\*[^*]+\*/g) ?? []).join(" ").toLowerCase();
  const combined = actions + " " + lower;

  // Emotion keyword patterns with weights
  const patterns: Array<{ emotion: string; words: string[]; weight: number }> = [
    { emotion: "angry", words: ["glare", "snarl", "hiss", "fury", "rage", "snaps", "seething", "clench"], weight: 1 },
    { emotion: "fearful", words: ["trembl", "shiver", "flinch", "shrink", "cower", "pale", "shak", "afraid"], weight: 1 },
    { emotion: "aroused", words: ["flush", "blush", "breath catch", "shiver", "lip", "heat", "pulse", "gasp"], weight: 0.8 },
    { emotion: "sad", words: ["tear", "weep", "sob", "sorrow", "grief", "hollow", "ache", "mourn"], weight: 1 },
    { emotion: "contemptuous", words: ["scoff", "sneer", "dismiss", "pathetic", "beneath", "disgust", "fool"], weight: 0.9 },
    { emotion: "amused", words: ["laugh", "smile", "smirk", "chuckle", "grin", "tease", "playful"], weight: 0.7 },
    { emotion: "curious", words: ["tilt", "raise.*brow", "study", "curious", "interest", "intrigue", "wonder"], weight: 0.6 },
    { emotion: "tender", words: ["gentle", "soft", "warm", "tender", "kind", "caress", "touch.*light"], weight: 0.8 },
    { emotion: "defiant", words: ["chin.*up", "stand.*tall", "refuse", "never", "won't", "defy", "resist"], weight: 0.9 },
    { emotion: "vulnerable", words: ["whisper", "quiet", "small.*voice", "look.*away", "averts", "hesitat"], weight: 0.7 },
  ];

  let best: { emotion: string; score: number } | null = null;
  let secondBest: { emotion: string; score: number } | null = null;

  for (const p of patterns) {
    let score = 0;
    for (const word of p.words) {
      if (new RegExp(word).test(combined)) {
        score += p.weight;
      }
    }
    if (score > 0) {
      if (!best || score > best.score) {
        secondBest = best;
        best = { emotion: p.emotion, score };
      } else if (!secondBest || score > secondBest.score) {
        secondBest = { emotion: p.emotion, score };
      }
    }
  }

  if (!best) return null;

  const intensity = Math.min(best.score / 3, 1);
  return {
    primary: best.emotion,
    intensity,
    secondary: secondBest?.emotion,
  };
}
