"use client";

import { useCallback, useRef } from "react";
import { useGameStore } from "@/stores/game-store";
import { createMockSession, MOCK_DIALOGUE } from "@/data/mock-scene";
import type { PlayerChoice, DialogueTurn } from "@/types/game";

/**
 * Game engine hook — manages dialogue flow, LLM streaming, and mock mode.
 */
export function useGameEngine() {
  const {
    session,
    mockMode,
    setSession,
    addDialogue,
    setStreamingText,
    appendStreamingText,
    setGenerating,
    updateCharacter,
  } = useGameStore();

  const mockIndexRef = useRef(0);

  /** Start a new game with mock scene data */
  const startGame = useCallback(() => {
    const newSession = createMockSession();
    setSession(newSession);
    mockIndexRef.current = 0;

    // Auto-play the narrator intro after a short delay
    setTimeout(() => {
      advanceDialogue();
    }, 500);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setSession]);

  /** Advance to the next dialogue turn (mock or live) */
  const advanceDialogue = useCallback(() => {
    if (mockMode) {
      advanceMock();
    } else {
      advanceLive();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mockMode, session]);

  /** Play next mock dialogue turn with simulated streaming */
  const advanceMock = useCallback(() => {
    const turn = MOCK_DIALOGUE[mockIndexRef.current];
    if (!turn) return;

    setGenerating(true);
    setStreamingText("");

    // Simulate streaming by revealing characters over time
    const text = turn.text;
    let charIndex = 0;
    const interval = setInterval(() => {
      if (charIndex < text.length) {
        appendStreamingText(text[charIndex]);
        charIndex++;
      } else {
        clearInterval(interval);
        setGenerating(false);
        addDialogue(turn);
        mockIndexRef.current++;
      }
    }, 20);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setGenerating, setStreamingText, appendStreamingText, addDialogue]);

  /** Handle player choosing a dialogue option */
  const handleChoice = useCallback(
    (choice: PlayerChoice) => {
      // Record the player's choice as a dialogue turn
      addDialogue({
        speaker: "player",
        text: choice.text,
      });

      // Apply relationship effects
      if (choice.effects && session) {
        const presentChars =
          session.worldState.currentScene.presentCharacters;
        for (const charId of presentChars) {
          const char = session.characters[charId];
          if (char && choice.effects) {
            const newRelationship = { ...char.relationship };
            if (choice.effects.trust)
              newRelationship.trust = Math.max(
                -100,
                Math.min(100, newRelationship.trust + choice.effects.trust)
              );
            if (choice.effects.affection)
              newRelationship.affection = Math.max(
                -100,
                Math.min(
                  100,
                  newRelationship.affection + choice.effects.affection
                )
              );
            if (choice.effects.respect)
              newRelationship.respect = Math.max(
                -100,
                Math.min(100, newRelationship.respect + choice.effects.respect)
              );
            if (choice.effects.desire)
              newRelationship.desire = Math.max(
                0,
                Math.min(100, newRelationship.desire + choice.effects.desire)
              );
            if (choice.effects.fear)
              newRelationship.fear = Math.max(
                0,
                Math.min(100, newRelationship.fear + choice.effects.fear)
              );
            updateCharacter(charId, { relationship: newRelationship });
          }
        }
      }

      // Advance to the next dialogue
      setTimeout(() => advanceDialogue(), 300);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [session, addDialogue, updateCharacter, advanceDialogue]
  );

  /** Stream dialogue from the live LLM API */
  const advanceLive = useCallback(async () => {
    if (!session) return;

    setGenerating(true);
    setStreamingText("");

    try {
      const currentChar =
        session.worldState.currentScene.presentCharacters[0];
      const character = session.characters[currentChar];

      // Find the last player turn for context
      const recentHistory = session.dialogueHistory.slice(-10);
      const lastPlayerTurn = [...recentHistory].reverse().find(t => t.speaker === "player");

      const resp = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          character,
          worldState: session.worldState,
          recentHistory,
          playerInput: lastPlayerTurn?.text ?? "[The player approaches in silence.]",
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
              appendStreamingText(content);
            }
          } catch {
            // Skip malformed SSE lines
          }
        }
      }

      // Parse the full response into a DialogueTurn
      const turn: DialogueTurn = {
        speaker: currentChar || "narrator",
        text: fullText,
      };
      addDialogue(turn);
    } catch (err) {
      console.error("Dialogue generation failed:", err);
      addDialogue({
        speaker: "narrator",
        text: "[The words fade into silence. Something went wrong with the connection.]",
      });
    } finally {
      setGenerating(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session, setGenerating, setStreamingText, appendStreamingText, addDialogue]);

  return {
    startGame,
    advanceDialogue,
    handleChoice,
  };
}
