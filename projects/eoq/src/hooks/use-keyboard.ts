"use client";

import { useEffect } from "react";

/**
 * Keyboard input hook for game controls.
 * Space/Enter = advance dialogue, Escape = close menus, 1-9 = select choice.
 */
export function useKeyboard({
  onAdvance,
  onChoose,
  onToggleExits,
  onToggleHistory,
  onToggleCharInfo,
  onToggleMap,
  onToggleAutoAdvance,
  onCloseExits,
  choices,
  canAdvance,
  showExits,
}: {
  onAdvance: () => void;
  onChoose: (index: number) => void;
  onToggleExits: () => void;
  onToggleHistory: () => void;
  onToggleCharInfo: () => void;
  onToggleMap: () => void;
  onToggleAutoAdvance: () => void;
  onCloseExits: () => void;
  choices: unknown[];
  canAdvance: boolean;
  showExits: boolean;
}) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Don't capture if typing in an input
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      switch (e.key) {
        case " ":
        case "Enter":
          e.preventDefault();
          if (canAdvance) {
            onAdvance();
          }
          break;

        case "Escape":
          e.preventDefault();
          if (showExits) {
            onCloseExits();
          }
          break;

        case "e":
        case "E":
          e.preventDefault();
          onToggleExits();
          break;

        case "h":
        case "H":
          e.preventDefault();
          onToggleHistory();
          break;

        case "i":
        case "I":
          e.preventDefault();
          onToggleCharInfo();
          break;

        case "m":
        case "M":
          e.preventDefault();
          onToggleMap();
          break;

        case "a":
        case "A":
          e.preventDefault();
          onToggleAutoAdvance();
          break;

        case "1":
        case "2":
        case "3":
        case "4":
        case "5":
        case "6":
        case "7":
        case "8":
        case "9": {
          const idx = parseInt(e.key) - 1;
          if (idx < choices.length) {
            e.preventDefault();
            onChoose(idx);
          }
          break;
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onAdvance, onChoose, onToggleExits, onToggleHistory, onToggleCharInfo, onToggleMap, onToggleAutoAdvance, onCloseExits, choices, canAdvance, showExits]);
}
