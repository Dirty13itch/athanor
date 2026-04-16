"use client";

import { useGameStore } from "@/stores/game-store";

/**
 * Subtle ambient mood text — displayed at the top of the screen,
 * changing based on time of day and scene atmosphere.
 */
export function AmbientMood() {
  const session = useGameStore((s) => s.session);
  if (!session) return null;

  const { timeOfDay } = session.worldState;
  const sceneId = session.worldState.currentScene.id;
  const mood = getMoodText(sceneId, timeOfDay);

  return (
    <div className="pointer-events-none fixed left-0 right-0 top-14 z-10 text-center">
      <p className="text-[10px] italic tracking-widest text-white/15">
        {mood}
      </p>
    </div>
  );
}

function getMoodText(
  sceneId: string,
  time: string
): string {
  // Scene-specific moods
  const sceneMoods: Record<string, Record<string, string>> = {
    courtyard: {
      dawn: "The first gray light reveals new damage from the night",
      morning: "Soldiers stir among the rubble, trading silence for routine",
      afternoon: "Heat shimmers off broken stone, making the air taste of dust",
      dusk: "Shadows stretch across the courtyard like reaching fingers",
      evening: "Fire barrels flicker to life, orange light on scarred faces",
      night: "The courtyard breathes smoke and whispered prayers",
    },
    "throne-room": {
      dawn: "Moonlight retreats, leaving the throne in cold shadow",
      morning: "Dust motes drift through the collapsed wall like slow snow",
      afternoon: "The iron throne absorbs what little warmth the sun offers",
      dusk: "The last light catches the scar on the metal, making it bleed gold",
      evening: "Candlelight makes the throne room feel almost alive",
      night: "Moonlight floods the broken wall, and the throne watches",
    },
    "throne-close": {
      dawn: "The blade in the armrest catches the first light",
      morning: "She has not moved since you last saw her",
      afternoon: "The air between you feels taut as wire",
      dusk: "Her shadow falls across you like a judgment",
      evening: "The candlelight shows every line of exhaustion on her face",
      night: "This close, you can hear her breathing. It is not calm.",
    },
    tavern: {
      dawn: "The tavern smells of last night's revelry and this morning's regret",
      morning: "Sunlight finds its way through grimy windows to illuminate spilled ale",
      afternoon: "The lunch crowd is thin — most of Ashenmoor has nowhere to go",
      dusk: "The evening regulars drift in, drawn by warmth and the absence of choices",
      evening: "The hurdy-gurdy player has found a tune that almost doesn't hurt",
      night: "The Broken Antler is full of people trying not to think",
    },
    undercroft: {
      dawn: "The tunnels don't know dawn. The dark here is permanent.",
      morning: "A candle gutters somewhere deep in the passage",
      afternoon: "Water drips with the patience of centuries",
      dusk: "The air shifts — something above ground has changed",
      evening: "Kael's lantern throws shadows that look like ancient script",
      night: "The breathing of the tunnels grows deeper in the dark",
    },
    "crimson-gate": {
      dawn: "The Gate pulses slower in the gray light, like a sleeper's heart",
      morning: "Frost clings to the red stone despite the warming air",
      afternoon: "The symbols on the Gate seem to rearrange when you look away",
      dusk: "The Gate glows from within as the sun retreats",
      evening: "Vaelis has not moved. The Gate has not stopped moving.",
      night: "The red light from the Gate is the only light here",
    },
    "oracle-spire": {
      dawn: "The wrong stars are fading into a sky that shouldn't have them",
      morning: "The broken tower casts a shadow that points the wrong direction",
      afternoon: "The orb's light competes with the sun and somehow wins",
      dusk: "Between the moving stars, real constellations begin to appear",
      evening: "Seraphine's fingers trace patterns only she can see",
      night: "The sky above the spire is a window into somewhere else entirely",
    },
    "vision-chamber": {
      dawn: "The mirrors show a sunrise that hasn't happened yet",
      morning: "Every reflection contains a different version of this moment",
      afternoon: "The orb's pulse quickens — it knows something is coming",
      dusk: "The mirrors darken, showing futures that end in flame",
      evening: "One mirror still shows something peaceful. You can't look away.",
      night: "The chamber is full of light from everywhere except here",
    },
  };

  const scene = sceneMoods[sceneId];
  if (scene && scene[time]) return scene[time];

  // Fallback by time of day
  const defaults: Record<string, string> = {
    dawn: "The world holds its breath between darkness and light",
    morning: "Another day in the ruins of what was",
    afternoon: "The sun offers no comfort to the broken",
    dusk: "The dying light makes everything look like a memory",
    evening: "Shadows deepen, and with them, the weight of choice",
    night: "In the dark, all masks fall away",
  };
  return defaults[time] ?? "The air tastes of old decisions";
}
