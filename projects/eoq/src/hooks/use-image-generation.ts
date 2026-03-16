"use client";

import { useCallback, useRef } from "react";
import { useGameStore } from "@/stores/game-store";
import type { Character, Queen } from "@/types/game";

function isQueen(char: Character): char is Queen {
  return "performerReference" in char && !!(char as Queen).performerReference;
}

/**
 * Image generation hook — handles scene backgrounds and character portraits.
 * Calls the /api/generate endpoint which proxies to ComfyUI.
 *
 * For queens with a performerReference, uses PuLID face injection:
 * 1. Fetch performer profile image URL from Stash
 * 2. Pass to /api/generate with type=pulid
 *
 * Generation is fire-and-forget — the game continues while images render.
 */
export function useImageGeneration() {
  const store = useGameStore();
  const lastSceneRef = useRef<string | null>(null);
  const lastCharRef = useRef<string | null>(null);
  const stashCache = useRef<Record<string, string | null>>({});

  /** Generate a scene background image */
  const generateSceneImage = useCallback(
    async (sceneId: string, visualPrompt: string) => {
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

  /** Generate a character portrait — uses PuLID for queens with performer references */
  const generatePortrait = useCallback(
    async (charId: string, char: Character) => {
      if (lastCharRef.current === charId) return;
      lastCharRef.current = charId;

      try {
        if (isQueen(char) && char.performerReference) {
          // Queen with performer reference — use PuLID face injection
          const referencePath = await getPerformerImagePath(char.performerReference);

          if (referencePath) {
            const resp = await fetch("/api/generate", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                prompt: char.fluxPrompt || char.visualDescription,
                type: "pulid",
                referencePath,
              }),
            });

            if (resp.ok) {
              const { imageUrl } = await resp.json();
              if (imageUrl) {
                store.setPortraitUrl(imageUrl);
                return;
              }
            }
          }
        }

        // Fallback: basic portrait generation (no face injection)
        const resp = await fetch("/api/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt: char.visualDescription,
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

  /** Fetch performer profile image path from Stash API (cached per performer) */
  async function getPerformerImagePath(performerName: string): Promise<string | null> {
    if (performerName in stashCache.current) {
      return stashCache.current[performerName];
    }

    try {
      const resp = await fetch(`/api/stash?performer=${encodeURIComponent(performerName)}`);
      if (!resp.ok) {
        stashCache.current[performerName] = null;
        return null;
      }

      const data = await resp.json();
      const imagePath = data.performer?.image_path ?? null;
      stashCache.current[performerName] = imagePath;
      return imagePath;
    } catch {
      stashCache.current[performerName] = null;
      return null;
    }
  }

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
        generatePortrait(charId, char);
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
