"use client";

import { useState, useEffect, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useGameStore } from "@/stores/game-store";

function isVideoUrl(url: string): boolean {
  return /\.(mp4|webm|mov)(\?|$)/i.test(url);
}

const AUTO_CYCLE_MS = 12000;

export function CharacterPortrait() {
  const portraitUrl = useGameStore((s) => s.portraitUrl);
  const session = useGameStore((s) => s.session);
  const [portraitIndex, setPortraitIndex] = useState(0);

  const presentCharacters = session?.worldState.currentScene.presentCharacters ?? [];
  const multiChar = presentCharacters.length > 1;
  const currentCharId = presentCharacters[portraitIndex] ?? presentCharacters[0];
  const currentChar = currentCharId ? session?.characters[currentCharId] : null;

  // Auto-cycle portraits in multi-character scenes
  useEffect(() => {
    if (!multiChar) return;
    const timer = setInterval(() => {
      setPortraitIndex((i) => (i + 1) % presentCharacters.length);
    }, AUTO_CYCLE_MS);
    return () => clearInterval(timer);
  }, [multiChar, presentCharacters.length]);

  // Reset index when scene changes
  useEffect(() => {
    setPortraitIndex(0);
  }, [session?.worldState.currentScene.id]);

  const prev = useCallback(() => {
    setPortraitIndex((i) => (i - 1 + presentCharacters.length) % presentCharacters.length);
  }, [presentCharacters.length]);

  const next = useCallback(() => {
    setPortraitIndex((i) => (i + 1) % presentCharacters.length);
  }, [presentCharacters.length]);

  return (
    <AnimatePresence>
      {portraitUrl && (
        <motion.div
          key={portraitUrl}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.5 }}
          className="fixed bottom-48 right-8 z-10 flex h-[60vh] w-auto flex-col items-center md:bottom-48 md:right-8"
        >
          {isVideoUrl(portraitUrl) ? (
            <video
              src={portraitUrl}
              className="h-full w-auto object-contain drop-shadow-2xl rounded-lg"
              autoPlay
              loop
              muted
              playsInline
            />
          ) : (
            <img
              src={portraitUrl}
              alt={currentChar?.name ?? "Character"}
              className="h-full w-auto object-contain drop-shadow-2xl"
            />
          )}

          {/* Character name + navigation for multi-character scenes */}
          {currentChar && (
            <div className="mt-2 flex items-center gap-2">
              {multiChar && (
                <button
                  onClick={prev}
                  className="rounded-full bg-black/50 p-1 text-white/80 hover:bg-black/70 hover:text-white"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
              )}
              <span className="rounded-full bg-black/60 px-3 py-1 text-xs font-medium text-white/90 backdrop-blur-sm"
                    style={{ fontFamily: "'Cormorant Garamond', serif" }}>
                {currentChar.name}
                {multiChar && (
                  <span className="ml-1 text-white/50">
                    {portraitIndex + 1}/{presentCharacters.length}
                  </span>
                )}
              </span>
              {multiChar && (
                <button
                  onClick={next}
                  className="rounded-full bg-black/50 p-1 text-white/80 hover:bg-black/70 hover:text-white"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              )}
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
