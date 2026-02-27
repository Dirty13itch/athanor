"use client";

import { useCallback, useRef } from "react";
import { useGameStore } from "@/stores/game-store";

/**
 * Image generation hook — handles scene backgrounds and character portraits.
 * Calls the /api/generate endpoint which proxies to ComfyUI.
 * Generation is fire-and-forget — the game continues while images render.
 */
export function useImageGeneration() {
  const store = useGameStore();
  const lastSceneRef = useRef<string | null>(null);
  const lastCharRef = useRef<string | null>(null);

  /** Generate a scene background image */
  const generateSceneImage = useCallback(
    async (sceneId: string, visualPrompt: string) => {
      // Skip if already generated for this scene
      if (lastSceneRef.current === sceneId) return;
      lastSceneRef.current = sceneId;

      store.setGeneratingImage(true);

      try {
        const resp = await fetch("/api/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt: visualPrompt,
            type: "scene",
          }),
        });

        if (resp.ok) {
          const { imageUrl } = await resp.json();
          if (imageUrl) {
            store.setBackgroundUrl(imageUrl);
          }
        }
      } catch (err) {
        console.error("Scene image generation failed:", err);
      } finally {
        store.setGeneratingImage(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  /** Generate a character portrait */
  const generatePortrait = useCallback(
    async (charId: string, visualDescription: string) => {
      // Skip if already generated for this character
      if (lastCharRef.current === charId) return;
      lastCharRef.current = charId;

      try {
        const resp = await fetch("/api/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt: visualDescription,
            type: "portrait",
          }),
        });

        if (resp.ok) {
          const { imageUrl } = await resp.json();
          if (imageUrl) {
            store.setPortraitUrl(imageUrl);
          }
        }
      } catch (err) {
        console.error("Portrait generation failed:", err);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  /** Trigger generation for the current scene and present characters */
  const generateForCurrentScene = useCallback(() => {
    const { session } = useGameStore.getState();
    if (!session) return;

    const scene = session.worldState.currentScene;

    // Generate scene background
    generateSceneImage(scene.id, scene.visualPrompt);

    // Generate portrait for the first present character
    const charId = scene.presentCharacters[0];
    if (charId) {
      const char = session.characters[charId];
      if (char) {
        generatePortrait(charId, char.visualDescription);
      }
    } else {
      // No character present — clear portrait
      store.setPortraitUrl(null);
      lastCharRef.current = null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Clear cached refs (for new game) */
  const resetImageCache = useCallback(() => {
    lastSceneRef.current = null;
    lastCharRef.current = null;
  }, []);

  return {
    generateSceneImage,
    generatePortrait,
    generateForCurrentScene,
    resetImageCache,
  };
}
