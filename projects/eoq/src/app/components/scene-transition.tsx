"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "@/stores/game-store";

/**
 * Full-screen overlay that fades in/out during scene changes.
 * Shows the scene name and a brief description with cinematic fade-to-black.
 */
export function SceneTransition() {
  const session = useGameStore((s) => s.session);
  const [transitioning, setTransitioning] = useState(false);
  const [sceneName, setSceneName] = useState("");
  const [sceneTime, setSceneTime] = useState("");
  const [sceneHint, setSceneHint] = useState("");
  const lastSceneRef = useRef<string | null>(null);

  useEffect(() => {
    if (!session) return;
    const currentId = session.worldState.currentScene.id;

    // Skip the first render (initial scene load)
    if (lastSceneRef.current === null) {
      lastSceneRef.current = currentId;
      return;
    }

    if (currentId !== lastSceneRef.current) {
      lastSceneRef.current = currentId;
      setSceneName(session.worldState.currentScene.name);
      setSceneTime(`Day ${session.worldState.day} · ${session.worldState.timeOfDay}`);

      // Short atmospheric hint from scene description
      const desc = session.worldState.currentScene.description;
      const firstSentence = desc.split(/[.!]/).filter(Boolean)[0]?.trim() ?? "";
      setSceneHint(firstSentence.length > 80 ? firstSentence.slice(0, 77) + "..." : firstSentence);

      setTransitioning(true);
      setTimeout(() => setTransitioning(false), 2500);
    }
  }, [session]);

  return (
    <AnimatePresence>
      {transitioning && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.6 }}
          className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-black"
        >
          <motion.h2
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.5 }}
            className="text-2xl font-semibold tracking-widest text-amber-400/80"
          >
            {sceneName}
          </motion.h2>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 0.5 }}
            className="mt-2 text-sm text-white/30"
          >
            {sceneTime}
          </motion.p>
          {sceneHint && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.4 }}
              transition={{ delay: 0.8, duration: 0.6 }}
              className="mt-4 max-w-md px-8 text-center text-xs italic text-white/20"
            >
              {sceneHint}
            </motion.p>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
