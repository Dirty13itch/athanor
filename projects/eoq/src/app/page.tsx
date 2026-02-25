"use client";

import { SceneBackground } from "./components/scene-background";
import { CharacterPortrait } from "./components/character-portrait";
import { DialogueBox } from "./components/dialogue-box";
import { ChoicePanel } from "./components/choice-panel";
import { useGameStore } from "@/stores/game-store";
import { useGameEngine } from "@/hooks/use-game-engine";

export default function GamePage() {
  const { session, isGenerating } = useGameStore();
  const { startGame, advanceDialogue, handleChoice } = useGameEngine();
  const history = session?.dialogueHistory ?? [];
  const lastTurn = history[history.length - 1];
  const choices = lastTurn?.choices ?? [];
  const hasChoices = !isGenerating && choices.length > 0;

  /** Click the dialogue box to advance when there are no choices pending */
  function handleDialogueClick() {
    if (!isGenerating && !hasChoices && session) {
      advanceDialogue();
    }
  }

  return (
    <main className="relative h-screen w-screen overflow-hidden">
      <SceneBackground />
      <CharacterPortrait />

      {/* Scene header */}
      {session && (
        <div className="fixed left-0 right-0 top-0 z-20 p-4">
          <div className="mx-auto max-w-4xl text-center">
            <h2 className="text-sm font-semibold uppercase tracking-widest text-amber-400/60">
              {session.worldState.currentScene.name}
            </h2>
          </div>
        </div>
      )}

      {/* Dialogue area — click to advance */}
      <div onClick={handleDialogueClick} className={!hasChoices && session && !isGenerating ? "cursor-pointer" : ""}>
        <DialogueBox />
      </div>

      {/* Click-to-continue hint */}
      {session && !isGenerating && !hasChoices && history.length > 0 && (
        <div className="fixed bottom-2 left-0 right-0 z-40 text-center">
          <span className="animate-pulse text-xs text-white/30">
            Click to continue
          </span>
        </div>
      )}

      {hasChoices && (
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
            onClick={startGame}
            className="rounded border border-amber-400/40 bg-black/60 px-8 py-3 text-lg text-amber-400 transition-colors hover:bg-amber-900/30"
          >
            Begin
          </button>
        </div>
      )}
    </main>
  );
}
