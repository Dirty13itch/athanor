"use client";

import { useEffect, useRef, useState } from "react";
import { SceneBackground } from "./components/scene-background";
import { CharacterPortrait } from "./components/character-portrait";
import { DialogueBox } from "./components/dialogue-box";
import { ChoicePanel } from "./components/choice-panel";
import { PlayerInput } from "./components/player-input";
import { SceneExits } from "./components/scene-exits";
import { RelationshipHUD } from "./components/relationship-hud";
import { CharacterStatus } from "./components/character-status";
import { GameMenu } from "./components/game-menu";
import { DialogueHistory } from "./components/dialogue-history";
import { SceneTransition } from "./components/scene-transition";
import { AmbientMood } from "./components/ambient-mood";
import { SaveIndicator } from "./components/save-indicator";
import { UnlockToast } from "./components/unlock-toast";
import { QuickActions } from "./components/quick-actions";
import { BreakingEvent } from "./components/breaking-event";
import { CharacterIntro } from "./components/character-intro";
import { DayTransition } from "./components/day-transition";
import { SceneMap } from "./components/scene-map";
import { AutoAdvance } from "./components/auto-advance";
import { SceneParticles } from "./components/scene-particles";
import { Inventory } from "./components/inventory";
import { ItemToast } from "./components/item-toast";
import { StatChangeToast } from "./components/stat-change-toast";
import { useGameStore } from "@/stores/game-store";
import { useGameEngine } from "@/hooks/use-game-engine";
import { useImageGeneration } from "@/hooks/use-image-generation";
import { useKeyboard } from "@/hooks/use-keyboard";

export default function GamePage() {
  const { session, isGenerating } = useGameStore();
  const {
    startGame,
    advanceDialogue,
    handleChoice,
    sendPlayerMessage,
    changeScene,
    loadSavedGame,
    hasSavedGame,
    getAvailableExits,
  } = useGameEngine();
  const { generateForCurrentScene, resetImageCache } = useImageGeneration();

  const [showExits, setShowExits] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showCharInfo, setShowCharInfo] = useState(false);
  const [showMap, setShowMap] = useState(false);
  const [showInventory, setShowInventory] = useState(false);
  const [autoAdvance, setAutoAdvance] = useState(false);
  const [savedGameExists, setSavedGameExists] = useState(false);
  const lastSceneIdRef = useRef<string | null>(null);

  // Derive choices and state (before hooks that depend on them)
  const history = session?.dialogueHistory ?? [];
  const lastTurn = history[history.length - 1];
  const choices = lastTurn?.choices ?? [];
  const hasChoices = !isGenerating && choices.length > 0;

  // Keyboard controls
  useKeyboard({
    onAdvance: () => {
      if (!isGenerating && !hasChoices && session) {
        advanceDialogue();
      }
    },
    onChoose: (index) => {
      if (hasChoices && choices[index]) {
        handleChoice(choices[index]);
      }
    },
    onToggleExits: () => {
      if (session) setShowExits((prev) => !prev);
    },
    onToggleHistory: () => {
      if (session) setShowHistory((prev) => !prev);
    },
    onToggleCharInfo: () => {
      if (session) setShowCharInfo((prev) => !prev);
    },
    onToggleMap: () => {
      if (session) setShowMap((prev) => !prev);
    },
    onToggleAutoAdvance: () => {
      if (session) setAutoAdvance((prev) => !prev);
    },
    onCloseExits: () => {
      if (showMap) setShowMap(false);
      else if (showHistory) setShowHistory(false);
      else if (showExits) setShowExits(false);
      else if (showMenu) setShowMenu(false);
      else if (session) setShowMenu(true);
    },
    choices,
    canAdvance: !isGenerating && !hasChoices && !!session,
    showExits,
  });

  // Check for saved game on mount
  useEffect(() => {
    setSavedGameExists(hasSavedGame());
  }, [hasSavedGame]);

  // Generate images when the scene changes
  useEffect(() => {
    if (!session) return;
    const sceneId = session.worldState.currentScene.id;
    if (sceneId !== lastSceneIdRef.current) {
      lastSceneIdRef.current = sceneId;
      generateForCurrentScene();
    }
  }, [session, generateForCurrentScene]);

  /** Click the dialogue box to advance when there are no choices pending */
  function handleDialogueClick() {
    if (!isGenerating && !hasChoices && session) {
      advanceDialogue();
    }
  }

  /** Toggle the scene exit menu */
  function toggleExits() {
    setShowExits((prev) => !prev);
  }

  /** Start new game with image cache reset */
  function handleNewGame() {
    resetImageCache();
    startGame();
  }

  return (
    <main className="vignette relative h-screen w-screen overflow-hidden select-none">
      <SceneBackground />
      <SceneParticles />
      <CharacterPortrait />
      <SceneTransition />
      <AmbientMood />
      <SaveIndicator />
      <UnlockToast />
      <BreakingEvent />
      <CharacterIntro />
      <DayTransition />
      <ItemToast />
      <StatChangeToast />

      {/* Scene header with navigation */}
      {session && (
        <div className="fixed left-0 right-0 top-0 z-20 p-4">
          <div className="mx-auto flex max-w-4xl items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-widest text-amber-400/60">
              {session.worldState.currentScene.name}
            </h2>
            <div className="flex items-center gap-3">
              {/* Day/Time indicator */}
              <span className="text-xs text-white/30">
                Day {session.worldState.day} · {session.worldState.timeOfDay}
              </span>
              {/* History button */}
              <button
                onClick={() => setShowHistory(true)}
                className="rounded border border-white/10 bg-black/40 px-3 py-1 text-xs text-white/50 transition-colors hover:border-amber-400/30 hover:text-amber-400/60"
                title="Dialogue History (H)"
              >
                Log
              </button>
              {/* Map button */}
              <button
                onClick={() => setShowMap(true)}
                className="rounded border border-white/10 bg-black/40 px-3 py-1 text-xs text-white/50 transition-colors hover:border-amber-400/30 hover:text-amber-400/60"
                title="Map (M)"
              >
                Map
              </button>
              {/* Navigation button */}
              <button
                onClick={toggleExits}
                className="rounded border border-white/10 bg-black/40 px-3 py-1 text-xs text-white/50 transition-colors hover:border-amber-400/30 hover:text-amber-400/60"
              >
                {showExits ? "Close" : "Explore"}
              </button>
              {/* Menu button */}
              <button
                onClick={() => setShowMenu(true)}
                className="rounded border border-white/10 bg-black/40 px-2 py-1 text-xs text-white/30 transition-colors hover:border-white/20 hover:text-white/50"
                title="Settings (Esc)"
              >
                &#9881;
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Scene exit menu */}
      {showExits && session && (
        <SceneExits
          exits={getAvailableExits()}
          allExits={session.worldState.currentScene.exits}
          onExit={(exit) => {
            setShowExits(false);
            changeScene(exit);
          }}
          onClose={() => setShowExits(false)}
        />
      )}

      {/* Relationship HUD — shows when talking to a character */}
      {session &&
        session.worldState.currentScene.presentCharacters.length > 0 && (
          <>
            <RelationshipHUD />
            <CharacterStatus
              expanded={showCharInfo}
              onToggle={() => setShowCharInfo((prev) => !prev)}
            />
          </>
        )}

      {/* Dialogue area — click to advance */}
      <div
        onClick={handleDialogueClick}
        className={
          !hasChoices && session && !isGenerating ? "cursor-pointer" : ""
        }
      >
        <DialogueBox />
      </div>

      {/* Quick actions for exploration scenes (no characters) */}
      {session &&
        !isGenerating &&
        !hasChoices &&
        history.length > 0 &&
        session.worldState.currentScene.presentCharacters.length === 0 && (
          <QuickActions
            onAction={(action) => {
              sendPlayerMessage(action);
            }}
            disabled={isGenerating}
            sceneName={session.worldState.currentScene.name}
          />
        )}

      {hasChoices && (
        <ChoicePanel
          choices={choices}
          onChoose={handleChoice}
          disabled={isGenerating}
        />
      )}

      {/* Freeform text input — shows when no scripted choices and a character is present */}
      {session &&
        !isGenerating &&
        !hasChoices &&
        history.length > 0 &&
        session.worldState.currentScene.presentCharacters.length > 0 && (
          <PlayerInput
            onSubmit={sendPlayerMessage}
            disabled={isGenerating}
            placeholder={`Speak to ${session.characters[session.worldState.currentScene.presentCharacters[0]]?.name ?? "them"}... (use *asterisks* for actions)`}
          />
        )}

      {/* Settings menu */}
      <GameMenu
        open={showMenu}
        onClose={() => setShowMenu(false)}
        onNewGame={handleNewGame}
        onOpenInventory={() => setShowInventory(true)}
      />

      {/* Dialogue history overlay */}
      <DialogueHistory
        open={showHistory}
        onClose={() => setShowHistory(false)}
      />

      {/* Inventory overlay */}
      <Inventory
        open={showInventory}
        onClose={() => setShowInventory(false)}
      />

      {/* Scene map overlay */}
      <SceneMap
        open={showMap}
        onClose={() => setShowMap(false)}
        onNavigate={(sceneId) => {
          const exits = session?.worldState.currentScene.exits ?? [];
          const exit = exits.find((e) => e.targetSceneId === sceneId);
          if (exit) changeScene(exit);
        }}
      />

      {/* Auto-advance indicator */}
      {session && (
        <AutoAdvance
          active={autoAdvance}
          onToggle={() => setAutoAdvance((prev) => !prev)}
          onAdvance={advanceDialogue}
          canAdvance={!isGenerating && !hasChoices && !!session}
          hasChoices={hasChoices}
          isGenerating={isGenerating}
        />
      )}

      {/* Title screen when no session */}
      {!session && (
        <div className="relative z-50 flex h-full flex-col items-center justify-center">
          {/* Decorative divider */}
          <div className="mb-6 h-px w-64 bg-gradient-to-r from-transparent via-amber-400/30 to-transparent" />

          <p className="mb-3 text-[10px] uppercase tracking-[0.5em] text-white/20">
            A dark fantasy interactive narrative
          </p>
          <h1 className="title-glow mb-2 text-6xl font-bold tracking-tight text-amber-400">
            Empire of Broken Queens
          </h1>
          <p className="mb-1 text-sm text-white/30">
            Act I: The Shattered Court
          </p>
          <p className="mb-8 text-[10px] text-white/15 italic">
            Every queen has a breaking point. Will you find it?
          </p>

          <div className="flex flex-col gap-3">
            <button
              onClick={handleNewGame}
              className="rounded border border-amber-400/40 bg-black/60 px-8 py-3 text-lg text-amber-400 transition-colors hover:bg-amber-900/30"
            >
              New Game
            </button>
            {savedGameExists && (
              <button
                onClick={() => {
                  loadSavedGame();
                  setSavedGameExists(false);
                }}
                className="rounded border border-white/20 bg-black/40 px-8 py-3 text-sm text-white/60 transition-colors hover:border-amber-400/30 hover:text-amber-400/60"
              >
                Continue
              </button>
            )}
          </div>

          {/* Bottom decorative divider */}
          <div className="mt-6 h-px w-64 bg-gradient-to-r from-transparent via-amber-400/30 to-transparent" />

          {/* Credits */}
          <p className="mt-8 text-[9px] text-white/10">
            Powered by Qwen3-32B · ComfyUI · Athanor
          </p>
        </div>
      )}
    </main>
  );
}
