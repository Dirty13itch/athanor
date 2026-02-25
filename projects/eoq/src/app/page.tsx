"use client";

import { SceneBackground } from "./components/scene-background";
import { CharacterPortrait } from "./components/character-portrait";
import { DialogueBox } from "./components/dialogue-box";
import { ChoicePanel } from "./components/choice-panel";
import { useGameStore } from "@/stores/game-store";
import type { PlayerChoice } from "@/types/game";

export default function GamePage() {
  const { session, isGenerating } = useGameStore();
  const history = session?.dialogueHistory ?? [];
  const lastTurn = history[history.length - 1];
  const choices = lastTurn?.choices ?? [];

  function handleChoice(choice: PlayerChoice) {
    // TODO: Send choice to dialogue generation API route
    console.log("Player chose:", choice.text);
  }

  return (
    <main className="relative h-screen w-screen overflow-hidden">
      <SceneBackground />
      <CharacterPortrait />
      <DialogueBox />
      {!isGenerating && choices.length > 0 && (
        <ChoicePanel
          choices={choices}
          onChoose={handleChoice}
          disabled={isGenerating}
        />
      )}

      {/* Title screen when no session */}
      {!session && (
        <div className="relative z-50 flex h-full flex-col items-center justify-center">
          <h1 className="mb-4 text-6xl font-bold tracking-tight text-amber-400 drop-shadow-lg">
            Empire of Broken Queens
          </h1>
          <p className="mb-8 text-xl text-white/60">
            An AI-driven interactive cinematic experience
          </p>
          <button
            onClick={() => console.log("TODO: Start new game")}
            className="rounded border border-amber-400/40 bg-black/60 px-8 py-3 text-lg text-amber-400 transition-colors hover:bg-amber-900/30"
          >
            Begin
          </button>
        </div>
      )}
    </main>
  );
}
