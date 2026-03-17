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

// ─────────────────────────────────────────────────────────────────────────────
// Queen's Council — Generic scenes for queen freeform dialogue
// ─────────────────────────────────────────────────────────────────────────────

/** Private audience scene — dynamically populated with a single queen */
export const QUEEN_AUDIENCE: SceneDefinition = {
  id: "queen-audience",
  name: "The Private Audience Chamber",
  description:
    "A candlelit chamber deep within the palace. Heavy velvet drapes in crimson and black frame tall windows looking out over a moonlit garden. A chaise lounge, a writing desk, a decanter of dark wine. The air is warm, perfumed with jasmine and something darker. The door locks from the inside.",
  visualPrompt:
    "Luxurious dark fantasy private chamber, candlelight, crimson velvet drapes, tall windows with moonlight, chaise lounge, wine decanter, warm amber lighting, intimate atmosphere, dark opulent decor, cinematic, 8k, photorealistic",
  presentCharacters: [], // Populated dynamically with selected queen
  exits: [
    { label: "Return to the Council Hall", targetSceneId: "queen-council-hall" },
  ],
};

export const QUEEN_COUNCIL_HALL: SceneDefinition = {
  id: "queen-council-hall",
  name: "The Council Hall",
  description:
    "A vast circular chamber ringed with twenty-one throne-like seats, each carved from different stone — obsidian, marble, bloodstone, jade. The floor is a mosaic depicting the empire's founding. Braziers burn low, casting the seated queens in shifting firelight. Some watch you with curiosity, others with contempt, others with barely concealed hunger.",
  visualPrompt:
    "Grand circular council hall, 21 ornate thrones in a ring, diverse beautiful women seated on thrones, mosaic floor, brazier firelight, dark opulent fantasy architecture, dramatic lighting, cinematic wide shot, 8k, photorealistic",
  presentCharacters: [], // Navigation hub — no single character
  exits: [], // Exits generated dynamically from available queens
};

// ─────────────────────────────────────────────────────────────────────────────
// Multi-Queen Rivalry Scenes — 2+ queens interact, compete, and react
// ─────────────────────────────────────────────────────────────────────────────

/** Confrontation scene — two queens face off, player mediates or exploits */
export const QUEEN_CONFRONTATION: SceneDefinition = {
  id: "queen-confrontation",
  name: "The Judgment Hall",
  description:
    "A narrow hall of polished black stone, lit by a single row of oil lamps. Two chairs face each other across a low table. No throne here — just two queens, forced into proximity by your summons. The tension is a living thing. You stand at the head, watching them watching each other.",
  visualPrompt:
    "Dark fantasy judgment hall, polished black stone walls, single row of oil lamps, two ornate chairs facing each other, low table between them, tense atmosphere, dramatic shadow lighting, gothic architecture, cinematic, 8k, photorealistic",
  presentCharacters: [], // Populated with two queens dynamically
  exits: [
    { label: "Dismiss them both", targetSceneId: "queen-council-hall" },
    { label: "Send one away", targetSceneId: "queen-audience" },
  ],
};

/** Banquet scene — multiple queens together, social dynamics play out */
export const QUEEN_BANQUET: SceneDefinition = {
  id: "queen-banquet",
  name: "The Conqueror's Banquet",
  description:
    "A long table groaning with food and wine, set in the great hall. Tapestries depicting your victories line the walls. The queens sit along both sides, each in their place — some by choice, some by force. Music plays from somewhere unseen. Beneath the civility, alliances form and break with every glance. You sit at the head, carving knife in hand.",
  visualPrompt:
    "Dark fantasy banquet hall, long wooden table with feast, tapestries on walls, multiple beautiful women seated at the table, goblets of wine, candlelight, warm but tense atmosphere, gothic opulence, cinematic wide shot, 8k, photorealistic",
  presentCharacters: [], // Populated with 3-5 queens
  exits: [
    { label: "End the banquet", targetSceneId: "queen-council-hall" },
    { label: "Call a queen to your side", targetSceneId: "queen-audience" },
  ],
};

/** Rivalry duel — two queens compete for favor, player judges */
export const QUEEN_RIVALRY_DUEL: SceneDefinition = {
  id: "queen-rivalry-duel",
  name: "The Arena of Favors",
  description:
    "A sunken pit ringed with torches, once used for gladiatorial contests. Now repurposed for a different kind of spectacle. Two queens stand at opposite ends, dressed for competition — one in armor, one in silk, both in fury. The court watches from above. You sit on the raised platform, the only judge that matters.",
  visualPrompt:
    "Dark fantasy arena pit, ring of torches, two beautiful women facing off at opposite ends, spectators watching from above, raised judge platform, dramatic contrast lighting, dust particles, cinematic, tension, 8k, photorealistic",
  presentCharacters: [], // Populated with two rival queens
  exits: [
    { label: "Declare a victor", targetSceneId: "queen-council-hall" },
    { label: "Take both to your chambers", targetSceneId: "queen-audience" },
  ],
};

// ─────────────────────────────────────────────────────────────────────────────
// Act 2: The Hollowlands — Scenes beyond the Crimson Gate
// ─────────────────────────────────────────────────────────────────────────────

export const ACT2_SCENES: Record<string, SceneDefinition> = {
  "ashen-wastes": {
    id: "ashen-wastes",
    name: "The Ashen Wastes",
    description:
      "Beyond the Crimson Gate, the world dies. Grey dust stretches to every horizon, broken only by the black skeletons of trees that haven't grown in centuries. The sky is wrong — too close, too still, like a painted ceiling. The air tastes of copper and endings. Somewhere in the distance, something vast shifts under the dust.",
    visualPrompt:
      "Vast grey wasteland stretching to horizon, dead black tree skeletons, low oppressive sky like painted ceiling, copper-tinted atmosphere, dust storms in distance, dark fantasy, desolate, cinematic wide shot, 8k, photorealistic",
    presentCharacters: [],
    exits: [
      { label: "Return to the Crimson Gate", targetSceneId: "crimson-gate" },
      { label: "Follow the bone road east", targetSceneId: "bone-road" },
      { label: "Descend into the Sink", targetSceneId: "the-sink" },
      {
        label: "Approach the Ember Citadel",
        targetSceneId: "ember-citadel",
        condition: "ember_citadel_revealed",
      },
    ],
  },

  "bone-road": {
    id: "bone-road",
    name: "The Bone Road",
    description:
      "A road paved with bones — human, animal, and things you can't name. Each step produces a muted crunch that echoes longer than it should. The bones are arranged too precisely to be natural. Someone built this road. Someone who wanted travelers to know exactly what they were walking on. Lanterns of pale green fire float at regular intervals, guiding the way to something you're not sure you want to find.",
    visualPrompt:
      "Fantasy road paved with bones in a wasteland, pale green floating lanterns lining the path, eerie perspective, skulls and ribcages visible in the road surface, dark misty atmosphere, gothic horror, cinematic, 8k, photorealistic",
    presentCharacters: [],
    exits: [
      { label: "Turn back to the wastes", targetSceneId: "ashen-wastes" },
      { label: "Follow the road to its end", targetSceneId: "the-ossuary" },
    ],
  },

  "the-ossuary": {
    id: "the-ossuary",
    name: "The Ossuary of the Forgotten",
    description:
      "The bone road ends at a cathedral of bones. Ribs arc overhead like Gothic vaults. Skulls line the walls in rows so perfect they look printed. At the center, a throne of fused vertebrae. And on it — nothing. An empty throne. But the throne is warm. Someone was just sitting here. The bones around the throne are newer than the rest.",
    visualPrompt:
      "Cathedral interior built entirely of human bones, gothic bone vaults, rows of skulls on walls, central throne made of fused vertebrae, warm amber glow suggesting recent presence, dark fantasy, macabre beauty, cinematic, 8k, photorealistic",
    presentCharacters: [],
    exits: [
      { label: "Leave this place", targetSceneId: "bone-road" },
      {
        label: "Sit on the throne",
        targetSceneId: "ossuary-throne",
        condition: "knows_throne_secret",
      },
    ],
  },

  "the-sink": {
    id: "the-sink",
    name: "The Sink",
    description:
      "A vast depression in the wasteland, miles across, where the ground sags inward like a wound that won't heal. At the bottom, liquid darkness pools — not water, not shadow. Something between. Structures jut from the slopes: half-buried buildings from a civilization that existed before Ashenmoor, before the Crimson Gate, before the bones. The air here is thicker. Warmer. You can hear a heartbeat that isn't yours.",
    visualPrompt:
      "Vast sinkhole depression in wasteland, ruined ancient buildings half-buried in slopes, pool of liquid darkness at the bottom, warm hazy atmosphere, ancient pre-civilization ruins, mysterious and foreboding, dark fantasy, cinematic aerial view, 8k, photorealistic",
    presentCharacters: [],
    exits: [
      { label: "Climb back to the wastes", targetSceneId: "ashen-wastes" },
      {
        label: "Enter the submerged temple",
        targetSceneId: "drowned-temple",
        condition: "sink_path_cleared",
      },
    ],
  },

  "ember-citadel": {
    id: "ember-citadel",
    name: "The Ember Citadel",
    description:
      "The citadel burns. It has always burned. Not with fire — with heat, with light trapped in stone, with the memory of a sun that died and refused to stop shining. The walls pulse with an amber glow, veins of molten light running through obsidian. Inside, the heat is almost unbearable. Figures move in the deeper corridors — not ghosts, not quite alive. The ember-born. Servants of whoever lit this place and never learned to put it out.",
    visualPrompt:
      "Massive obsidian citadel with veins of molten amber light running through the walls, pulsing heat glow, ember-born figures in corridors, volcanic glass architecture, oppressive heat haze, dark fantasy fortress, dramatic lighting, cinematic, 8k, photorealistic",
    presentCharacters: [],
    exits: [
      { label: "Retreat to the wastes", targetSceneId: "ashen-wastes" },
      { label: "Enter the throne of embers", targetSceneId: "ember-throne" },
    ],
  },
};

// Register Act 2 scenes in the main SCENES map
for (const [id, scene] of Object.entries(ACT2_SCENES)) {
  SCENES[id] = scene;
}

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
  "queen-council-hall":
    "Twenty-one thrones. Twenty-one queens. Each one was powerful once — a ruler, a warrior, a goddess in her own domain. Now they sit in your circle, watching you with twenty-one different expressions. Hatred. Fear. Calculation. Hunger. The air is thick with perfume and barely restrained violence. You own this room. The question is what you'll do with it.",
  "queen-confrontation":
    "You summoned them both. They know why. The question isn't whether they'll fight — it's how, and whether you'll let them finish. The narrow hall amplifies every sound — the rustle of silk, the scrape of a chair, the sharp intake of breath when they finally look at each other.",
  "queen-banquet":
    "Breaking bread with conquered queens. Some eat because they're hungry. Some because refusing would be worse. A few — the dangerous ones — eat because they're planning something. The wine flows. Inhibitions thin. Under the table, alliances form and fracture with every exchanged glance.",
  "queen-rivalry-duel":
    "Two queens. One favor. The court watches with the particular hunger that comes from seeing powerful women diminished. Torchlight catches on sweat and silk. The rules are simple: impress you, or lose everything. You could stop this. You won't.",
  // Act 2: The Hollowlands
  "ashen-wastes":
    "The world ends at the Crimson Gate, and what begins beyond it isn't a new world — it's the corpse of one. Grey dust. Dead sky. The air tastes like the end of things. Everything you've built in Ashenmoor feels very far away. Very small.",
  "bone-road":
    "The road is bones. Not scattered, not random — laid with the precision of a mason who hated everything alive. Each step is a small desecration. The green lanterns float ahead, patient as death, lighting a path to somewhere you're increasingly sure you shouldn't go.",
  "the-ossuary":
    "The bone cathedral takes your breath. Not with beauty — with scale. The recognition that this many dead exist, arranged this carefully, by hands that took the time to sort femurs from fibulae. The empty throne at the center is the worst part. It's still warm.",
  "the-sink":
    "You feel the Sink before you see it — a wrongness in the ground, a pull like gravity learned a new direction. The ruins on the slopes are older than anything in Ashenmoor. The liquid darkness at the bottom moves when you look at it directly. The heartbeat you hear is getting louder.",
  "ember-citadel":
    "The citadel doesn't burn — it remembers burning, and the memory is strong enough to melt stone. The amber light in the walls pulses like a living thing. The ember-born watch you pass with eyes that were alive once. 'Welcome,' the walls seem to say. 'We've been waiting.'",
};
