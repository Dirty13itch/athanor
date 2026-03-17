"use client";

import { useCallback, useRef } from "react";
import { useGameStore } from "@/stores/game-store";
import type { Character, Queen } from "@/types/game";
import { getBreakingStage } from "@/types/game";

function isQueen(char: Character): char is Queen {
  return "performerReference" in char && !!(char as Queen).performerReference;
}

/**
 * Build a stage-aware visual prompt.
 * Defiant queens are fully clothed and hostile.
 * Broken queens are exposed and submissive.
 * The base prompt (fluxPrompt or visualDescription) provides the face/body,
 * and we append a stage-specific scene/clothing/mood modifier.
 */
function buildStagePrompt(char: Character, contentIntensity: number): string {
  const base = isQueen(char) ? (char.fluxPrompt || char.visualDescription) : char.visualDescription;
  const stage = getBreakingStage(char.resistance);
  const emotion = char.emotion.primary;

  // Scene/mood modifiers based on breaking stage
  const stageModifiers: Record<string, string> = {
    defiant: "regal commanding pose, arms crossed, cold hostile expression, fully clothed in ornate dark gown, armored shoulders, dramatic harsh lighting, unyielding",
    struggling: "guarded stance, one shoulder exposed, conflicted expression mixing defiance and vulnerability, dramatic side lighting, tension visible",
    conflicted: "seated with legs crossed, dress slipping off one shoulder, torn expression, warm and cool lighting mixed, inner turmoil visible",
    yielding: "sheer fabric revealing silhouette, lowered gaze with upward glance, compliant but traces of dignity, soft warm amber lighting",
    surrendered: "minimal clothing, kneeling or seated submissively, seeking approval expression, collar visible, warm intimate candlelight",
    broken: "nude or nearly nude, fully submissive pose on knees, devoted desperate expression, collar and chain, dramatic spotlight from above",
  };

  // Only apply explicit modifiers at intensity >= 3
  const modifier = contentIntensity >= 3
    ? (stageModifiers[stage] ?? "")
    : stage === "defiant" || stage === "struggling"
      ? stageModifiers[stage] ?? ""
      : "elegant pose, suggestive tension, dramatic lighting";

  // Emotion overlay — map emotional states to specific visual cues
  const emotionVisuals: Record<string, string> = {
    angry: "furious glare, clenched jaw, flushed cheeks, tense posture",
    fearful: "wide frightened eyes, trembling lips, pale skin, shrinking posture",
    aroused: "flushed skin, parted lips, heavy-lidded eyes, chest heaving",
    contemptuous: "raised chin, cold sneer, narrowed eyes, dismissive posture",
    amused: "sly smile, sparkling eyes, relaxed confident posture",
    tender: "soft warm gaze, gentle half-smile, relaxed open body language",
    defiant: "chin up, hard stare, squared shoulders, proud stance",
    vulnerable: "averted gaze, arms crossed protectively, unshed tears",
    calculating: "narrowed assessing eyes, steepled fingers, predatory calm",
    melancholic: "distant unfocused gaze, tear tracks, hollowed expression",
    playful: "teasing smirk, tilted head, mischievous eyes, relaxed pose",
    desperate: "pleading wide eyes, reaching hands, trembling, tear-streaked",
  };
  const emotionHint = emotion && char.emotion.intensity > 0.4
    ? `, ${emotionVisuals[emotion] ?? `${emotion} expression`}`
    : "";

  // Prefix with solo/single to reduce multi-face generation artifacts
  return `solo, single person, ${base}, ${modifier}${emotionHint}`;
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

  /** Generate a character portrait — uses PuLID for queens with performer references.
   *  Portraits are stage-aware: different breaking stages produce different visuals. */
  const generatePortrait = useCallback(
    async (charId: string, char: Character) => {
      // Cache key includes breaking stage so portraits regenerate on stage transitions
      const stage = getBreakingStage(char.resistance);
      const cacheKey = `${charId}:${stage}`;
      if (lastCharRef.current === cacheKey) return;
      lastCharRef.current = cacheKey;

      // Get content intensity from current session
      const intensity = useGameStore.getState().session?.worldState.contentIntensity ?? 3;
      const prompt = buildStagePrompt(char, intensity);

      try {
        if (isQueen(char) && char.performerReference) {
          // Queen with performer reference — use PuLID face injection
          const referencePath = await getPerformerImagePath(char.performerReference);

          if (referencePath) {
            const resp = await fetch("/api/generate", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                prompt,
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
            prompt,
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

  /** Fetch performer reference image URL from Stash API (cached per performer) */
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
      // Only use profile image if it's a real photo (not a silhouette placeholder)
      const imagePath = data.hasRealProfileImage ? data.performer?.image_path : null;
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

    // Generate portraits for all present characters (fire-and-forget)
    if (scene.presentCharacters.length > 0) {
      for (const charId of scene.presentCharacters) {
        const char = session.characters[charId];
        if (char) {
          generatePortrait(charId, char);
        }
      }
    } else {
      // No character present — clear portrait
      store.setPortraitUrl(null);
      lastCharRef.current = null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Animate an existing portrait into a short video clip via Wan 2.2 I2V.
   *  Uses the current portrait URL as the anchor (first frame).
   *  Fire-and-forget — replaces the portrait with the video URL when done. */
  const generatePortraitVideo = useCallback(
    async (charId: string, char: Character) => {
      const currentPortrait = useGameStore.getState().portraitUrl;
      if (!currentPortrait) return;

      const intensity = useGameStore.getState().session?.worldState.contentIntensity ?? 3;
      const stage = getBreakingStage(char.resistance);

      // Build a motion prompt — describe what movement to add
      const motionPrompts: Record<string, string> = {
        defiant: "subtle breathing, cold stare directly at viewer, slight head tilt, imperious",
        struggling: "uneasy shifting, eyes darting between defiance and uncertainty, breathing quickens",
        conflicted: "slow exhale, eyes close briefly then open, internal struggle visible",
        yielding: "gentle swaying, eyes lowered then glancing up, lips part slightly",
        surrendered: "slow rhythmic breathing, devoted upward gaze, gentle trembling",
        broken: "deep submissive breathing, pleading eyes locked on viewer, body sways gently",
      };

      const basePrompt = isQueen(char) ? (char.fluxPrompt || char.visualDescription) : char.visualDescription;
      const motion = motionPrompts[stage] ?? "subtle breathing, blinking, looking at viewer";
      const prompt = `${basePrompt}, ${motion}, cinematic, photorealistic, 8k`;

      try {
        const resp = await fetch("/api/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt,
            type: "i2v",
            referencePath: currentPortrait,
            nsfw: intensity >= 4,
            negativePrompt: "blurry, distorted face, morphing, identity change, static image, watermark, text, cartoon",
          }),
        });

        if (resp.ok) {
          const { imageUrl } = await resp.json();
          if (imageUrl) {
            store.setPortraitUrl(imageUrl);
          }
        }
      } catch (err) {
        console.error("Portrait video generation failed:", err);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  /** Clear cached refs (for new game) */
  const resetImageCache = useCallback(() => {
    lastSceneRef.current = null;
    lastCharRef.current = null;
  }, []);

  return {
    generateSceneImage,
    generatePortrait,
    generatePortraitVideo,
    generateForCurrentScene,
    resetImageCache,
  };
}
