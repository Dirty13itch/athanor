import type { SceneDefinition } from "@/types/game";

/**
 * Empire of Broken Queens — Scene Definitions
 *
 * Act 1: The Shattered Court
 *
 * Scene graph:
 *
 *   [courtyard] ←→ [throne-room]
 *       ↓                ↓
 *   [tavern]      [throne-close]
 *       ↓
 *   [undercroft]
 *       ↓
 *   [crimson-gate] → [oracle-spire]
 *                         ↓
 *                    [vision-chamber]
 *
 * The player starts in the courtyard and can explore freely.
 * Some exits require plot flags (e.g., undercroft needs Mira's trust).
 */

export const SCENES: Record<string, SceneDefinition> = {
  courtyard: {
    id: "courtyard",
    name: "The Courtyard of Ashenmoor",
    description:
      "The central courtyard of Ashenmoor Keep, open to a bruised sky. Siege damage scars every surface — cracked flagstones, toppled statues, a dry fountain choked with rubble. Soldiers huddle around fires in oil drums. The smell of smoke and unwashed bodies. Three paths lead deeper into what remains of the capital.",
    visualPrompt:
      "Dark fantasy castle courtyard at night, siege damage, cracked flagstones, toppled stone statues, dry fountain with rubble, soldiers around barrel fires, bruised purple sky, torchlight, wide cinematic shot, atmospheric fog, 8k, photorealistic, moody, film color grading",
    presentCharacters: [],
    exits: [
      { label: "Enter the throne room", targetSceneId: "throne-room" },
      { label: "Head to the tavern", targetSceneId: "tavern" },
      {
        label: "Descend to the undercroft",
        targetSceneId: "undercroft",
        condition: "undercroft_unlocked",
      },
      {
        label: "Take the road to the Crimson Gate",
        targetSceneId: "crimson-gate",
        condition: "crimson_gate_known",
      },
    ],
  },

  "throne-room": {
    id: "throne-room",
    name: "The Shattered Throne Room",
    description:
      "The throne room of Ashenmoor Keep, half-destroyed by the siege. Moonlight streams through a collapsed eastern wall, illuminating rubble-strewn marble floors. The iron throne remains — scarred but standing. Isolde sits upon it, watching through hooded eyes. The air tastes of ash and old stone.",
    visualPrompt:
      "Dark fantasy throne room, collapsed wall revealing moonlit sky, rubble on marble floor, iron throne with seated regal woman in black and gold, gothic architecture, dramatic side lighting, dust motes in moonbeams, cinematic, 8k, photorealistic",
    presentCharacters: ["isolde"],
    exits: [
      { label: "Return to the courtyard", targetSceneId: "courtyard" },
      { label: "Approach the throne", targetSceneId: "throne-close" },
    ],
  },

  "throne-close": {
    id: "throne-close",
    name: "Before the Iron Throne",
    description:
      "You stand at the foot of the dais. Up close, the throne is worse than it appeared — the iron is warped, partially melted, fused with fragments of the stone wall behind it. Isolde looks down at you, her scarred jaw catching the moonlight. Her fingers drum on the armrest. You can see the thin blade hidden in the throne's hollow arm.",
    visualPrompt:
      "Close-up view of dark fantasy iron throne, warped and partially melted metal, regal woman with scar leaning forward, ice-blue eyes intense, moonlight from above, intimate and tense atmosphere, cinematic, shallow depth of field, 8k, photorealistic",
    presentCharacters: ["isolde"],
    exits: [
      { label: "Step back", targetSceneId: "throne-room" },
      { label: "Leave the throne room", targetSceneId: "courtyard" },
    ],
  },

  tavern: {
    id: "tavern",
    name: "The Broken Antler",
    description:
      "A squat stone building that survived the siege by virtue of having nothing worth destroying. Inside: low ceilings, tallow candles, the smell of cheap ale and roasting meat. Mira works behind the bar, pouring drinks with one hand and palming coins with the other. A mix of soldiers, refugees, and people who'd rather not be identified fill the tables. Someone's playing a hurdy-gurdy badly in the corner.",
    visualPrompt:
      "Dark fantasy medieval tavern interior, low stone ceiling, tallow candles on rough wooden tables, warm amber light, barmaid with dark skin and curly hair behind the bar, crowded with rough patrons, mugs of ale, fireplace, cozy but dangerous atmosphere, cinematic, warm color grading, 8k, photorealistic",
    presentCharacters: ["mira"],
    exits: [
      { label: "Return to the courtyard", targetSceneId: "courtyard" },
      {
        label: "Ask Mira about the undercroft",
        targetSceneId: "undercroft",
        condition: "mira_trusts_player",
      },
    ],
  },

  undercroft: {
    id: "undercroft",
    name: "The Undercroft",
    description:
      "Below the tavern, through a trapdoor Mira showed you, ancient tunnels stretch beneath Ashenmoor. The walls are older than the keep itself — pre-empire stonework carved with symbols no one alive can read. Kael has made his camp here among stolen books and half-eaten meals. A lantern casts unsteady shadows. Water drips somewhere in the dark.",
    visualPrompt:
      "Underground stone tunnels, ancient carved walls with mysterious symbols, scattered books and papers, makeshift camp with bedroll, single lantern casting warm light in darkness, young man with disheveled hair sitting among books, wet stone, atmospheric, dark fantasy, cinematic, 8k, photorealistic",
    presentCharacters: ["kael"],
    exits: [
      { label: "Climb back to the tavern", targetSceneId: "tavern" },
      {
        label: "Follow the tunnel to the Crimson Gate",
        targetSceneId: "crimson-gate",
        condition: "kael_reveals_gate",
      },
    ],
  },

  "crimson-gate": {
    id: "crimson-gate",
    name: "The Crimson Gate",
    description:
      "A massive gate of dark red stone, older than Ashenmoor itself. It marks the boundary between the living city and whatever lies beyond — the Hollowlands, the locals call it. Vaelis stands before it, motionless as a statue, his void-black left eye fixed on something you can't see. The air here is noticeably colder. The gate's surface seems to pulse faintly, like a heartbeat.",
    visualPrompt:
      "Massive dark red stone gate in a narrow canyon, ancient carved runes glowing faintly, tall armored knight with grey skin standing guard, void-black eye, cold mist rolling through, eerie red light from the gate surface, dark fantasy, dramatic scale, cinematic, 8k, photorealistic",
    presentCharacters: ["vaelis"],
    exits: [
      { label: "Return to the courtyard", targetSceneId: "courtyard" },
      {
        label: "Take the path to the Oracle's Spire",
        targetSceneId: "oracle-spire",
        condition: "vaelis_grants_passage",
      },
    ],
  },

  "oracle-spire": {
    id: "oracle-spire",
    name: "The Oracle's Spire",
    description:
      "A crumbling tower rising from the wasteland beyond the Crimson Gate. Once the tallest structure in the empire, now broken at the midpoint, its upper half scattered across the landscape like bone fragments. Seraphine sits at the base, tracing patterns in the dust with her fingers. Her cracked orb flickers beside her. The sky here is wrong — too many stars, and they move.",
    visualPrompt:
      "Broken fantasy tower in a wasteland, crumbled halfway up with rubble scattered, young woman with silver-white hair sitting at the base, glowing crystal orb, alien sky with too many moving stars, eerie and beautiful, ethereal lighting, dark fantasy, cinematic, 8k, photorealistic",
    presentCharacters: ["seraphine"],
    exits: [
      { label: "Return to the Crimson Gate", targetSceneId: "crimson-gate" },
      {
        label: "Enter the vision chamber",
        targetSceneId: "vision-chamber",
        condition: "seraphine_invites_player",
      },
    ],
  },

  "vision-chamber": {
    id: "vision-chamber",
    name: "The Vision Chamber",
    description:
      "The ground floor of the spire, still intact. A circular room lined with shattered mirrors that reflect things that aren't there — or haven't happened yet. Seraphine's orb sits on a stone pedestal at the center, pulsing with stronger light than you've seen from it before. She stands beside it, hands trembling. The mirrors show fractured images: a burning city, a crown breaking, a figure with your face doing something terrible.",
    visualPrompt:
      "Circular chamber inside a fantasy tower, walls lined with broken mirrors reflecting impossible scenes, central stone pedestal with glowing crystal orb, silver-haired woman standing beside it, ethereal blue light filling the room, reflections showing fire and crowns, mystical and unsettling, dark fantasy, cinematic, 8k, photorealistic",
    presentCharacters: ["seraphine"],
    exits: [
      { label: "Leave the chamber", targetSceneId: "oracle-spire" },
    ],
  },
};

/** Starting scene for new games */
export const STARTING_SCENE = "courtyard";

/**
 * Introductory dialogue for each scene — played once on first entry.
 * The narrator sets the stage before the character speaks.
 */
export const SCENE_INTROS: Record<string, string> = {
  courtyard:
    "The gates of Ashenmoor groan open and the smell hits you first — smoke, blood, and something sweeter underneath. You survived the siege. Most didn't. The courtyard spreads before you, a memorial to what this place used to be.",
  "throne-room":
    "The throne room opens like a wound in the keep's side. Half the eastern wall is gone, and moonlight floods the space where courtiers once stood. At the far end, on an iron throne that looks like it was pulled from a fire, a woman waits.",
  "throne-close":
    "Each step toward the throne feels heavier. Up close, you can see the damage — not just to the room, but to her. The scar. The tension in her hands. The blade she thinks you can't see. This is not a woman who inherited power. This is a woman who took it.",
  tavern:
    "The Broken Antler smells like every tavern you've ever been in, which is somehow comforting. The woman behind the bar catches your eye and holds it a beat too long before smiling. She's already decided something about you.",
  undercroft:
    "The tunnels breathe. That's the only way to describe the way air moves down here — slow, rhythmic, like something massive sleeping beneath the city. Among the stolen books and dying candlelight, a young man looks up at you with the expression of someone who's been expecting the worst.",
  "crimson-gate":
    "You feel the gate before you see it. A pressure in your chest, a wrongness in the air temperature. Then the red stone rises before you, carved with symbols that hurt to look at directly. The knight standing before it might be part of the stone himself.",
  "oracle-spire":
    "The tower shouldn't exist. Something this damaged should have collapsed entirely. Yet here it stands, broken halfway, its upper half scattered like teeth knocked from a jaw. At its base, a woman sits, her silver hair catching light from stars that aren't where they should be.",
  "vision-chamber":
    "The mirrors don't show your reflection. They show everything else — things that were, things that might be, things you desperately hope won't happen. At the center of it all, the orb pulses with a light that feels like it's looking back at you.",
};
