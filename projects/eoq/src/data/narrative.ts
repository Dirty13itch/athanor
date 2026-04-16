import type { DialogueTurn } from "@/types/game";

/**
 * Empire of Broken Queens — Narrative Framework
 *
 * Act 1: The Shattered Court
 *
 * Arc progression: prologue -> gathering_allies -> the_choice -> act1_end
 *
 * Reconciled from:
 * - GDD: Breaking system stages, queen archetypes, breaking methods
 * - Dialogue System Design: Emotional state model, branching conditions
 * - Storytelling Framework: Power asymmetry, resistance/erosion patterns
 *
 * Plot flags control scene access and dialogue branching.
 * The LLM generates contextual dialogue; these scripted turns
 * handle key story beats and player choices with authored effects.
 */

/** Arc positions and their descriptions */
export const ARC_POSITIONS: Record<string, string> = {
  prologue: "The player arrives at Ashenmoor. Explore, meet characters, establish trust.",
  gathering_allies: "The player has met at least 3 characters. Alliances forming.",
  the_choice: "Isolde presents the central choice: serve her or defy her.",
  act1_end: "Act 1 concludes based on the player's choice and alliances.",
  // Act 2: The Hollowlands
  beyond_the_gate: "The player has crossed the Crimson Gate. The Hollowlands await.",
  the_descent: "The player discovers the Sink and the ruins of the pre-empire civilization.",
  ember_path: "The Ember Citadel is revealed. The truth about the Gate's purpose approaches.",
  act2_climax: "The player must decide what to do with the power behind the Gate.",
};

/**
 * Check if an arc transition should occur based on current flags.
 * Returns the new arc position, or null if no transition.
 */
export function checkArcTransition(
  currentArc: string,
  flags: Record<string, boolean>
): string | null {
  if (currentArc === "prologue") {
    const metCount = [
      flags.met_isolde,
      flags.met_mira,
      flags.met_kael,
      flags.met_vaelis,
      flags.met_seraphine,
    ].filter(Boolean).length;
    if (metCount >= 3) return "gathering_allies";
  }

  if (currentArc === "gathering_allies") {
    if (flags.isolde_proposal_heard) return "the_choice";
  }

  if (currentArc === "the_choice") {
    if (flags.chose_serve_isolde || flags.chose_defy_isolde) return "act1_end";
  }

  // Act 2 transitions
  if (currentArc === "act1_end") {
    if (flags.crossed_crimson_gate) return "beyond_the_gate";
  }

  if (currentArc === "beyond_the_gate") {
    if (flags.entered_the_sink) return "the_descent";
  }

  if (currentArc === "the_descent") {
    if (flags.ember_citadel_revealed) return "ember_path";
  }

  if (currentArc === "ember_path") {
    if (flags.faced_gate_truth) return "act2_climax";
  }

  return null;
}

/**
 * Check if a plot flag condition is met.
 * Conditions are simple flag names — returns true if the flag is set.
 * No condition means always accessible.
 */
export function checkCondition(
  condition: string | undefined,
  flags: Record<string, boolean>
): boolean {
  if (!condition) return true;
  return flags[condition] === true;
}

/**
 * Get a scripted dialogue sequence for entering a scene for the first time.
 * Returns null if the scene has no scripted intro dialogue (LLM generates instead).
 */
export function getScriptedIntro(
  sceneId: string,
  flags: Record<string, boolean>
): DialogueTurn[] | null {
  const intros = SCRIPTED_INTROS[sceneId];
  if (!intros) return null;

  // Check if we've already played this intro
  const flagKey = `intro_played_${sceneId}`;
  if (flags[flagKey]) return null;

  return intros;
}

/**
 * Scripted intro sequences for key scenes.
 * After these play, the LLM takes over for freeform conversation.
 *
 * Choice effects now include resistance/corruption/emotional shifts
 * from the GDD's breaking system design.
 */
const SCRIPTED_INTROS: Record<string, DialogueTurn[]> = {
  // ── Act 2: The Hollowlands ────────────────────────────────────────────
  "ashen-wastes": [
    {
      speaker: "narrator",
      text: "The Crimson Gate closes behind you with the sound of a coffin lid. The world you knew — Ashenmoor, the tavern, the throne room — is behind the stone now. Ahead: nothing. Grey dust. Dead sky. The air tastes of endings and copper, and the silence is so complete you can hear your own blood moving.",
    },
    {
      speaker: "narrator",
      text: "Something moves under the dust in the distance. Something vast. It shifts like a whale turning in deep water, slow and inexorable. The ground trembles once, then is still. Whatever it is, it knows you're here. It was waiting.",
    },
  ],

  "bone-road": [
    {
      speaker: "narrator",
      text: "The first bone crunches under your boot and you stop. Not because of the sound — because of the arrangement. These aren't scattered remains. They're paving stones. Femurs laid parallel. Skulls at the borders, facing outward. Someone built this road, and they built it to be walked on. The green lanterns float ahead, patient and cold, lighting a path that wants to be followed.",
    },
    {
      speaker: "narrator",
      text: "As you walk, you notice the bones aren't all human. Some are too long. Some have too many joints. Some have teeth where teeth shouldn't be. The deeper you go, the newer the bones get. Whatever supplies the road's materials is still working.",
    },
  ],

  "the-ossuary": [
    {
      speaker: "narrator",
      text: "The bone cathedral takes your breath. Ribs arch overhead like Gothic vaults, each one perfect, polished, locked into place with a precision that makes you sick. The walls are skulls — thousands of them — arranged by size, smallest at the top, largest at the bottom. A sorting. A taxonomy of the dead.",
    },
    {
      speaker: "narrator",
      text: "At the center: the throne. It's warm. You can feel the heat from three paces away. Someone — something — was sitting here moments ago. The vertebrae that form its arms are fused with a material that isn't bone. It's darker. Harder. It catches the light like obsidian and hums when you lean close.",
    },
  ],

  "the-sink": [
    {
      speaker: "narrator",
      text: "You feel it before you see it — a wrongness in your inner ear, like the ground has tilted two degrees and your body can't reconcile the difference. Then the rim appears, and the wasteland drops away into something impossible. The Sink is miles across, and at its bottom, a pool of liquid darkness that isn't water, isn't shadow, isn't anything you have a word for.",
    },
    {
      speaker: "narrator",
      text: "The ruins on the slopes are older than Ashenmoor. Older than the Gate. Their architecture is wrong — the angles don't add up, the doorways are the wrong height, the windows face inward. A civilization that built for beings shaped differently than humans. And from the bottom of the Sink, a heartbeat. Not yours. Slower. Deeper. Patient.",
    },
  ],

  "ember-citadel": [
    {
      speaker: "narrator",
      text: "The citadel doesn't burn. It remembers burning, and the memory is so vivid that the obsidian walls glow amber, veins of trapped light pulsing like arteries in a body that refuses to die. The heat hits you thirty paces out — not fire heat, but the kind of heat that comes from being too close to something alive and angry.",
    },
    {
      speaker: "narrator",
      text: "The ember-born see you first. They stand in the corridors like statues made of cooling lava — humanoid, barely, with eyes that were alive once and now hold only the light's reflection. One of them raises a hand. Not in greeting. In recognition. 'We've been expecting you,' it says, in a voice like the last coal in a dying fire. 'The Flame remembers your blood.'",
      choices: [
        {
          text: '"My blood? What do you mean?"',
          intent: "curious",
          effects: {
            plotFlags: { ember_blood_recognized: true },
          },
        },
        {
          text: '"Take me to whoever runs this place."',
          intent: "demanding",
          effects: {
            plotFlags: { ember_blood_recognized: true, demanded_audience: true },
          },
        },
        {
          text: "*Draw your weapon.* \"Nothing that remembers my blood gets to keep that memory.\"",
          intent: "aggressive",
          breakingMethod: "physical",
          effects: {
            plotFlags: { ember_blood_recognized: true, threatened_ember_born: true },
          },
        },
      ],
    },
  ],

  // ── Act 1: Original Scenes ────────────────────────────────────────────
  "throne-room": [
    {
      speaker: "narrator",
      text: "The air smells of ash and old stone. Your boots crunch over broken marble as you enter what remains of the throne room. At the far end, a figure watches you from the iron throne.",
    },
    {
      speaker: "isolde",
      text: "You took your time. I was beginning to wonder if the siege had claimed you as well.",
      emotion: { primary: "calculating", intensity: 0.6 },
      choices: [
        {
          text: '"I came as soon as I could, Your Grace."',
          intent: "respectful",
          effects: {
            respect: 5,
            trust: 3,
            plotFlags: { met_isolde: true },
          },
        },
        {
          text: '"The dead don\'t keep schedules."',
          intent: "dark_humor",
          effects: {
            respect: -5,
            affection: 5,
            resistance: -3,
            emotionalShifts: { defiance: -5 },
            plotFlags: { met_isolde: true },
          },
        },
        {
          text: '"I\'m here for what you promised me."',
          intent: "demanding",
          breakingMethod: "psychological",
          effects: {
            fear: -5,
            respect: 10,
            trust: -5,
            resistance: -5,
            emotionalShifts: { fear: 5, defiance: -5 },
            plotFlags: { met_isolde: true },
          },
        },
      ],
    },
  ],

  tavern: [
    {
      speaker: "narrator",
      text: "The Broken Antler is loud, warm, and alive in a way the rest of Ashenmoor isn't. You push through the crowd to the bar, where a dark-skinned woman with pinned-up curls is pouring three drinks simultaneously without looking.",
    },
    {
      speaker: "mira",
      text: "*She slides a drink across the bar to you without being asked.* On the house, love. You look like you've had the kind of day that needs something stronger than water. I'm Mira. And you're the one everyone's been whispering about.",
      emotion: { primary: "playful", intensity: 0.5 },
      choices: [
        {
          text: '"What are they saying about me?"',
          intent: "curious",
          effects: {
            trust: 5,
            affection: 3,
            plotFlags: { met_mira: true },
          },
        },
        {
          text: '"How did you know what I drink?"',
          intent: "suspicious",
          effects: {
            respect: 5,
            trust: -3,
            emotionalShifts: { fear: 3 },
            plotFlags: { met_mira: true },
          },
        },
        {
          text: '*Take the drink and sit down.* "Just a quiet night. That too much to ask?"',
          intent: "weary",
          effects: {
            affection: 5,
            trust: 5,
            resistance: -2,
            emotionalShifts: { defiance: -3 },
            plotFlags: { met_mira: true },
          },
        },
      ],
    },
  ],

  undercroft: [
    {
      speaker: "narrator",
      text: "The trapdoor drops you into darkness. As your eyes adjust, you see a makeshift camp — books stacked into walls, a bedroll that's seen better decades, and a young man who freezes mid-bite of a stolen apple.",
    },
    {
      speaker: "kael",
      text: "*He nearly chokes, then composes himself with visible effort.* You're — you're not one of Isolde's people. At least, I don't think so. They usually kick the door in rather than — well. *He gestures vaguely at the trapdoor.* I'm Kael. And if you're here to kill me, could we at least talk first? I've read that's customary.",
      emotion: { primary: "anxious", intensity: 0.7 },
      choices: [
        {
          text: '"Mira sent me. She said you might have information."',
          intent: "direct",
          effects: {
            trust: 10,
            respect: 5,
            plotFlags: { met_kael: true },
          },
        },
        {
          text: '"Kill you? I don\'t even know who you are."',
          intent: "honest",
          effects: {
            trust: 5,
            affection: 3,
            emotionalShifts: { fear: -5 },
            plotFlags: { met_kael: true },
          },
        },
        {
          text: '"That depends on what you tell me, Your Highness."',
          intent: "knowing",
          breakingMethod: "psychological",
          effects: {
            fear: 10,
            respect: 5,
            trust: -5,
            resistance: -10,
            emotionalShifts: { fear: 15, defiance: -10, despair: 5 },
            plotFlags: { met_kael: true, knows_kael_is_prince: true },
          },
        },
      ],
    },
  ],

  "crimson-gate": [
    {
      speaker: "narrator",
      text: "The temperature drops sharply as you approach the gate. The red stone rises before you, taller than any wall in Ashenmoor. Before it stands a figure in ruined armor, perfectly still. As you draw closer, the black void of his left eye turns to fix on you.",
    },
    {
      speaker: "vaelis",
      text: "One approaches the Gate. *His voice is a dry rasp, like stone scraping stone.* State purpose, or turn back. The Hollowlands offer nothing to the living. Nothing worth keeping.",
      emotion: { primary: "stoic", intensity: 0.3 },
      choices: [
        {
          text: '"I seek passage. I need to reach the Oracle\'s Spire."',
          intent: "direct",
          effects: {
            respect: 5,
            plotFlags: { met_vaelis: true },
          },
        },
        {
          text: '"How long have you been standing here?"',
          intent: "empathetic",
          effects: {
            affection: 5,
            trust: 3,
            resistance: -3,
            emotionalShifts: { despair: 5, defiance: -3 },
            plotFlags: { met_vaelis: true },
          },
        },
        {
          text: '"Move aside, guardian. I don\'t answer to the dead."',
          intent: "aggressive",
          breakingMethod: "physical",
          effects: {
            fear: -10,
            respect: 10,
            trust: -10,
            emotionalShifts: { defiance: 10, fear: -5 },
            plotFlags: { met_vaelis: true },
          },
        },
      ],
    },
  ],

  "oracle-spire": [
    {
      speaker: "narrator",
      text: "She doesn't look up as you approach. Her fingers trace patterns in the dust — constellations, you realize, but not ones you recognize. The crystal orb beside her flickers like a dying heartbeat.",
    },
    {
      speaker: "seraphine",
      text: "*She stops tracing. Her pale eyes focus on something behind you, then slowly drift to your face.* You're... earlier than I expected. Or later. Time is — *she trails off, pressing fingers to her temple* — difficult here. I saw you coming. Three versions of you. Only one was kind.",
      emotion: { primary: "melancholic", intensity: 0.7 },
      choices: [
        {
          text: '"Which version am I?"',
          intent: "curious",
          effects: {
            trust: 5,
            affection: 3,
            plotFlags: { met_seraphine: true },
          },
        },
        {
          text: '"Are you alright? You seem... lost."',
          intent: "compassionate",
          effects: {
            affection: 10,
            trust: 5,
            resistance: -5,
            emotionalShifts: { despair: -5, submission: 3 },
            plotFlags: { met_seraphine: true },
          },
        },
        {
          text: '"I need your gift, oracle. Can you see the future of Ashenmoor?"',
          intent: "pragmatic",
          effects: {
            respect: 5,
            trust: -3,
            emotionalShifts: { fear: 3 },
            plotFlags: { met_seraphine: true },
          },
        },
      ],
    },
  ],
};

/**
 * Triggered events — scripted sequences that fire based on arc position
 * and scene context, not just first visit. Checked when entering a scene
 * if the intro has already played.
 */
export function getTriggeredEvent(
  sceneId: string,
  arcPosition: string,
  flags: Record<string, boolean>
): DialogueTurn[] | null {
  const key = `${sceneId}:${arcPosition}`;
  const event = TRIGGERED_EVENTS[key];
  if (!event) return null;

  // Check if already played
  if (flags[`event_played_${key}`]) return null;

  // Check prerequisites
  if (event.requires && !flags[event.requires]) return null;

  return event.turns;
}

interface TriggeredEvent {
  requires?: string;
  turns: DialogueTurn[];
}

const TRIGGERED_EVENTS: Record<string, TriggeredEvent> = {
  /** Isolde's proposal — triggers when player returns to throne-close during gathering_allies arc */
  "throne-close:gathering_allies": {
    requires: "met_isolde",
    turns: [
      {
        speaker: "isolde",
        text: "*She rises from the throne for the first time since you've known her. Her hand rests on the hidden blade, but she doesn't draw it.* You've been busy. The tavern keeper. The boy in the tunnels. Even that... thing at the Gate. You've been building something. Don't insult me by denying it.",
        emotion: { primary: "intense", intensity: 0.8 },
      },
      {
        speaker: "isolde",
        text: "I have a proposition. *She descends the dais steps, each one deliberate.* Ashenmoor needs more than a queen on a broken throne. It needs a hand — someone who can do what I cannot. Reach the people I've failed to reach. Earn the loyalty I've only commanded.",
        emotion: { primary: "calculating", intensity: 0.7 },
      },
      {
        speaker: "isolde",
        text: "*She stops close enough that you can see the pulse in her scarred jaw.* Serve me. Not as a servant — as my right hand. My voice in the dark. My blade when diplomacy fails. In return... *a pause, something genuine flickering behind the mask* ...I offer you everything I have. The resources of the crown. My trust — what's left of it. And perhaps, in time, something more.",
        emotion: { primary: "vulnerable", intensity: 0.5 },
        choices: [
          {
            text: '"I accept, Your Grace. Ashenmoor needs unity, and you need someone you can trust."',
            intent: "loyal",
            effects: {
              trust: 20,
              affection: 10,
              respect: 15,
              resistance: -15,
              corruption: 10,
              emotionalShifts: { submission: 10, defiance: -15, fear: -5 },
              plotFlags: { chose_serve_isolde: true, isolde_proposal_heard: true },
            },
          },
          {
            text: '"I\'ll work with you. But I serve no one. We do this as equals, or not at all."',
            intent: "defiant",
            effects: {
              respect: 25,
              trust: 5,
              affection: 5,
              resistance: -5,
              emotionalShifts: { defiance: 5, submission: -5 },
              plotFlags: { chose_defy_isolde: true, isolde_proposal_heard: true },
            },
          },
          {
            text: '"You\'re asking me to be your weapon. I\'ve seen what happens to your weapons." *Glance at the broken throne.*',
            intent: "suspicious",
            effects: {
              respect: 10,
              trust: -10,
              fear: -10,
              emotionalShifts: { fear: 10, defiance: 10 },
              plotFlags: { chose_defy_isolde: true, isolde_proposal_heard: true },
            },
          },
        ],
      },
    ],
  },

  /** Kael's discovery — triggers when player revisits undercroft during gathering_allies */
  "undercroft:gathering_allies": {
    requires: "met_kael",
    turns: [
      {
        speaker: "kael",
        text: "*He's surrounded by more books than last time — and he's been writing. Pages of tight, frantic handwriting cover the floor.* You're back. Good. I've found something. *He holds up a crumbling page, hands shaking.* The Crimson Gate isn't just a boundary. It's a lock. And whatever's behind it... my father tried to open it. That's the real reason Isolde killed him.",
        emotion: { primary: "excited", intensity: 0.8 },
      },
      {
        speaker: "kael",
        text: "*He looks up at you, and for a moment you see the prince he was supposed to become — the weight of it, the impossibility.* I need to get past that gate. Whatever my father died for, I need to understand it. But Vaelis... he won't let me through. He barely tolerates breathing near the thing. *A pause.* Will you help me?",
        emotion: { primary: "desperate", intensity: 0.6 },
        choices: [
          {
            text: '"I\'ll talk to Vaelis. He may listen to reason."',
            intent: "diplomatic",
            effects: {
              trust: 10,
              affection: 5,
              respect: 5,
              plotFlags: { kael_gate_request: true, crimson_gate_known: true },
            },
          },
          {
            text: '"What exactly are you willing to do to get through that gate, Kael?"',
            intent: "probing",
            breakingMethod: "psychological",
            effects: {
              trust: -5,
              fear: 10,
              resistance: -8,
              emotionalShifts: { fear: 8, despair: 5, defiance: -5 },
              plotFlags: { kael_gate_request: true, crimson_gate_known: true },
            },
          },
          {
            text: '"Your father tried to open something dangerous and died for it. Maybe take the hint."',
            intent: "protective",
            effects: {
              affection: 10,
              trust: 5,
              respect: -5,
              emotionalShifts: { defiance: 10 },
              plotFlags: { kael_gate_request: true },
            },
          },
        ],
      },
    ],
  },

  /** Vaelis opens up — triggers at crimson-gate during gathering_allies if Kael asked */
  "crimson-gate:gathering_allies": {
    requires: "kael_gate_request",
    turns: [
      {
        speaker: "vaelis",
        text: "*His void eye tracks you before you're close enough to speak.* The scholar sent you. *It isn't a question.* I felt his wanting through the stone. His father had the same hunger. The same impatience. *The armored figure shifts — the first voluntary movement you've seen from him.* Do you know what I am?",
        emotion: { primary: "melancholic", intensity: 0.5 },
      },
      {
        speaker: "vaelis",
        text: "I am what remains of the last gatekeeper. My body died four hundred years ago. This — *he raises one gauntleted hand, grey skin showing at the joints* — is what the Gate does to those who guard it. It keeps you. Preserves you. Takes everything else. *His voice drops.* I do not guard this gate by choice. I am chained to it by something older than choice.",
        emotion: { primary: "resigned", intensity: 0.7 },
        choices: [
          {
            text: '"Is there a way to free you?"',
            intent: "compassionate",
            effects: {
              trust: 15,
              affection: 10,
              resistance: -10,
              emotionalShifts: { despair: -5, submission: 5 },
              plotFlags: { vaelis_shared_truth: true },
            },
          },
          {
            text: '"What happens if the Gate opens?"',
            intent: "pragmatic",
            effects: {
              respect: 10,
              trust: 5,
              plotFlags: { vaelis_shared_truth: true },
            },
          },
          {
            text: '"Four hundred years. And you just... stand here. That\'s not loyalty. That\'s punishment."',
            intent: "confrontational",
            breakingMethod: "psychological",
            effects: {
              trust: 5,
              resistance: -15,
              emotionalShifts: { despair: 15, defiance: -10, submission: 5 },
              plotFlags: { vaelis_shared_truth: true },
            },
          },
        ],
      },
    ],
  },

  /** Seraphine's vision — triggers at oracle-spire during gathering_allies */
  "oracle-spire:gathering_allies": {
    requires: "met_seraphine",
    turns: [
      {
        speaker: "seraphine",
        text: "*She's standing when you arrive — unusual for her. The orb is brighter than you've ever seen it, casting sharp shadows. Her hands are pressed to her temples.* Don't come closer. I'm — seeing. Right now. Multiple things at once. It's — *she winces* — it hurts when there are too many.",
        emotion: { primary: "distressed", intensity: 0.9 },
      },
      {
        speaker: "seraphine",
        text: "*Her pale eyes snap to yours, and for a moment they're not pale at all — they're full of swirling colors, like oil on water.* I see you in the throne room. I see you in the Gate. I see you holding something that's eating its way through your hand. And in one — just one — I see you holding someone's face and they're crying and they're grateful. *The colors fade.* I don't know which is real. Maybe all of them. Maybe none.",
        emotion: { primary: "afraid", intensity: 0.8 },
        choices: [
          {
            text: '"Come here. Sit down. You don\'t have to carry this alone." *Offer your hand.*',
            intent: "tender",
            effects: {
              affection: 15,
              trust: 10,
              desire: 5,
              resistance: -10,
              emotionalShifts: { submission: 10, fear: -5, despair: -5 },
              plotFlags: { seraphine_vision_seen: true },
            },
          },
          {
            text: '"The one where someone is grateful — how do I make that one happen?"',
            intent: "hopeful",
            effects: {
              trust: 10,
              affection: 5,
              respect: 5,
              plotFlags: { seraphine_vision_seen: true },
            },
          },
          {
            text: '"Can you see what\'s behind the Crimson Gate?"',
            intent: "strategic",
            effects: {
              respect: 5,
              trust: -5,
              fear: 5,
              emotionalShifts: { fear: 10, submission: -5 },
              plotFlags: { seraphine_vision_seen: true },
            },
          },
        ],
      },
    ],
  },

  /** Vision chamber prophecy — available during the_choice arc */
  "vision-chamber:the_choice": {
    requires: "seraphine_invites_player",
    turns: [
      {
        speaker: "narrator",
        text: "The mirrors come alive the moment you enter. Not reflections — memories, futures, lies. The orb at the center of the room is brighter than the sun, and Seraphine stands beside it, tears running down her face.",
      },
      {
        speaker: "seraphine",
        text: "*Her voice is calm despite the tears.* I wanted to show you something before you decide. The mirrors — they show what happens next. All the versions. *She gestures to the walls, and the reflections sharpen.* In one, you rule beside Isolde and the city burns slowly. In another, you defy her and the boy king takes the throne and the city burns faster. In every version, something burns. But — *she touches the orb, and one mirror clears to show a single image* — in this one, just this one... nothing burns at all.",
        emotion: { primary: "hopeful", intensity: 0.5 },
        choices: [
          {
            text: '"Show me that future. The one where nothing burns."',
            intent: "hopeful",
            effects: {
              trust: 10,
              affection: 10,
              resistance: -10,
              emotionalShifts: { submission: 10, despair: -10 },
              plotFlags: { saw_peaceful_future: true },
            },
          },
          {
            text: '"Every future has a price. What does that one cost?"',
            intent: "pragmatic",
            effects: {
              respect: 15,
              trust: 5,
              plotFlags: { saw_peaceful_future: true },
            },
          },
          {
            text: '"Burn the mirrors. We make our own future." *Reach for the orb.*',
            intent: "defiant",
            breakingMethod: "magical",
            effects: {
              fear: 15,
              resistance: -20,
              corruption: 10,
              emotionalShifts: { fear: 20, submission: 15, despair: 10 },
              plotFlags: { destroyed_mirrors: true },
              itemGrants: ["oracle_fragment"],
            },
          },
        ],
      },
    ],
  },

  /** Mira reveals information about Isolde after gathering_allies */
  "tavern:gathering_allies": {
    requires: "met_mira",
    turns: [
      {
        speaker: "mira",
        text: "*She leans across the bar, voice dropping below the noise of the crowd.* You've been making friends in all the wrong places, love. The queen's watching. The boy underground is scared. And that knight at the Gate... *she shakes her head* ...he asked about you. Through the stone. I felt it in my teeth.",
        emotion: { primary: "serious", intensity: 0.7 },
      },
      {
        speaker: "mira",
        text: "Listen — I like you. That's rare for me. So I'm going to tell you something that could get us both killed. *She pours you a drink and slides it across the bar like a bribe.* Isolde didn't take the throne by right. She took it by murder. The old king — Kael's father — she poisoned him. With my mother's recipe.",
        emotion: { primary: "guilty", intensity: 0.6 },
        choices: [
          {
            text: '"Your mother... she was involved?"',
            intent: "compassionate",
            effects: {
              trust: 10,
              affection: 10,
              resistance: -5,
              emotionalShifts: { despair: 5, defiance: -5 },
              plotFlags: { mira_confession_heard: true },
            },
          },
          {
            text: '"Does Kael know?"',
            intent: "strategic",
            effects: {
              trust: 5,
              respect: 5,
              plotFlags: { mira_confession_heard: true },
            },
          },
          {
            text: '"That\'s useful information. What do you want for it?"',
            intent: "transactional",
            breakingMethod: "social",
            effects: {
              trust: -5,
              respect: 5,
              resistance: -3,
              emotionalShifts: { fear: 5 },
              plotFlags: { mira_confession_heard: true },
            },
          },
        ],
      },
    ],
  },

  /** Isolde's ultimatum — triggers in throne room during the_choice if player defied her */
  "throne-room:the_choice": {
    requires: "chose_defy_isolde",
    turns: [
      {
        speaker: "narrator",
        text: "The throne room is different tonight. The fires burn lower. The guards have been replaced — these are Isolde's personal retainers, the ones with dead eyes and steady hands. She sits on the throne as always, but something in her posture has changed. Coiled. Ready.",
      },
      {
        speaker: "isolde",
        text: "*She doesn't rise. Her voice is ice over deep water.* You chose poorly. I offered you partnership. I offered you my trust — what little of it remains. And you threw it back in my face like a dog refusing the hand that feeds it. *Her fingers find the hidden blade.* Tell me why I shouldn't end this conversation permanently.",
        emotion: { primary: "cold fury", intensity: 0.9 },
        choices: [
          {
            text: '"Because you need me alive more than you want me dead. And you know it."',
            intent: "confident",
            effects: {
              respect: 15,
              fear: -10,
              resistance: -8,
              emotionalShifts: { fear: 5, defiance: -10 },
              plotFlags: { isolde_ultimatum_faced: true },
            },
          },
          {
            text: '"I didn\'t refuse you. I refused to kneel. There\'s a difference."',
            intent: "defiant_respect",
            effects: {
              respect: 20,
              trust: 5,
              resistance: -5,
              emotionalShifts: { defiance: -5, submission: 3 },
              plotFlags: { isolde_ultimatum_faced: true },
            },
          },
          {
            text: '*Step closer to the blade.* "Go ahead. But you\'ll have to look me in the eyes when you do it."',
            intent: "challenge",
            breakingMethod: "psychological",
            effects: {
              fear: -15,
              respect: 25,
              desire: 10,
              resistance: -15,
              emotionalShifts: { fear: -10, arousal: 10, defiance: -15 },
              plotFlags: { isolde_ultimatum_faced: true },
            },
          },
        ],
      },
    ],
  },

  /** Mira warns about consequences — triggers in tavern during the_choice */
  "tavern:the_choice": {
    requires: "mira_confession_heard",
    turns: [
      {
        speaker: "mira",
        text: "*She pours you a drink with hands that aren't quite steady.* You made your choice with Isolde. I heard. Everyone's heard. *She leans close, her usual warmth replaced by urgency.* She's not going to let this stand, love. She can't afford to. The moment she looks weak, every lord with a grudge and a sword will be at the gates.",
        emotion: { primary: "afraid", intensity: 0.6 },
      },
      {
        speaker: "mira",
        text: "*She takes your hand across the bar, just for a moment.* I have something that might help. Or destroy everything. My mother's last recipe — not a poison. Something worse. Something that makes people tell the truth. Every truth. All at once. *She looks into your eyes.* If we used it on Isolde, in front of the court... she'd confess everything. The murder. The lies. All of it. But it would break her. Completely.",
        emotion: { primary: "conflicted", intensity: 0.8 },
        choices: [
          {
            text: '"That\'s... incredibly dangerous. For both of us. Are you sure?"',
            intent: "cautious",
            effects: {
              trust: 10,
              affection: 5,
              plotFlags: { mira_truth_serum_offered: true },
            },
          },
          {
            text: '"Do it. She deserves the truth as much as anyone."',
            intent: "ruthless",
            breakingMethod: "social",
            effects: {
              respect: 5,
              trust: -5,
              resistance: -5,
              emotionalShifts: { fear: 10, submission: 5 },
              plotFlags: { mira_truth_serum_offered: true, accepted_truth_serum: true },
              itemGrants: ["truth_serum"],
            },
          },
          {
            text: '"Keep it. I won\'t break her that way." *Squeeze her hand.*',
            intent: "protective",
            effects: {
              affection: 15,
              trust: 10,
              desire: 5,
              plotFlags: { mira_truth_serum_offered: true, rejected_truth_serum: true },
            },
          },
        ],
      },
    ],
  },

  /** Kael's crisis — triggers in undercroft during the_choice */
  "undercroft:the_choice": {
    requires: "met_kael",
    turns: [
      {
        speaker: "narrator",
        text: "The undercroft is a mess. Books scattered, pages torn. Kael's camp looks like it was hit by a storm — or by someone having a breakdown. He sits in the middle of it, holding a piece of parchment, staring at nothing.",
      },
      {
        speaker: "kael",
        text: "*His voice is flat. Empty.* I found my father's last letter. The one he wrote the night before Isolde poisoned him. *He doesn't look up.* He knew. He knew she was going to do it. And he let her. *A long pause.* He says here — he says the Crimson Gate must never open. That what's behind it would destroy everything. And he chose to die rather than risk someone using him to open it.",
        emotion: { primary: "devastated", intensity: 0.9 },
      },
      {
        speaker: "kael",
        text: "*He finally looks up. His eyes are red but dry — past tears.* My whole life I thought she murdered him for the throne. But he chose this. He chose to die. And now I'm the only one left who carries the blood key, and I don't even know what that means. *His voice breaks.* Tell me what to do. Please. I can't — I don't know how to be a prince. I never did.",
        emotion: { primary: "broken", intensity: 0.8 },
        choices: [
          {
            text: '"You don\'t have to be a prince. You just have to be yourself — Kael, who reads too much and cares too much."',
            intent: "compassionate",
            effects: {
              affection: 15,
              trust: 10,
              resistance: -10,
              emotionalShifts: { despair: -10, submission: 10, defiance: -5 },
              plotFlags: { kael_crisis_resolved: true, kael_comforted: true },
              itemGrants: ["kael_journal"],
            },
          },
          {
            text: '"Your father chose to die. You can choose to live. But that means choosing what to fight for."',
            intent: "inspiring",
            effects: {
              respect: 15,
              trust: 10,
              resistance: -5,
              emotionalShifts: { despair: -5, defiance: 10 },
              plotFlags: { kael_crisis_resolved: true },
            },
          },
          {
            text: '"Blood key. That means you can open the Gate. Your father couldn\'t trust himself with that power — but I trust you."',
            intent: "manipulative",
            breakingMethod: "psychological",
            effects: {
              trust: 5,
              fear: 10,
              resistance: -15,
              corruption: 5,
              emotionalShifts: { submission: 15, despair: 5, fear: 10 },
              plotFlags: { kael_crisis_resolved: true, kael_blood_key_known: true },
              itemGrants: ["blood_key", "fathers_letter"],
            },
          },
        ],
      },
    ],
  },

  /** Vaelis's choice — triggers at crimson-gate during the_choice */
  "crimson-gate:the_choice": {
    requires: "vaelis_shared_truth",
    turns: [
      {
        speaker: "vaelis",
        text: "*He is not standing today. For the first time, the hollow knight sits — slumped against the Gate, his great sword across his knees. The void in his left eye flickers.* The Gate grows weaker. *His voice is barely audible.* Or I grow weaker. One cannot tell the difference anymore.",
        emotion: { primary: "exhausted", intensity: 0.7 },
      },
      {
        speaker: "vaelis",
        text: "Four centuries of duty. Of watching. Of being the thing between what is and what must never be. *He turns his amber eye to you.* You have changed things. The scholar boy. The queen. The oracle. All of you, pulling at threads that were woven before any of you were born. *A pause.* One has a request. It is the first request one has made in four hundred years.",
        emotion: { primary: "vulnerable", intensity: 0.6 },
        choices: [
          {
            text: '"Name it."',
            intent: "direct",
            effects: {
              trust: 10,
              respect: 10,
              resistance: -10,
              emotionalShifts: { despair: -10, submission: 5 },
              plotFlags: { vaelis_request_heard: true },
            },
          },
          {
            text: '*Sit beside him.* "You\'ve earned the right to ask for anything."',
            intent: "tender",
            effects: {
              affection: 15,
              trust: 15,
              resistance: -15,
              emotionalShifts: { despair: -15, submission: 10, defiance: -10 },
              plotFlags: { vaelis_request_heard: true },
              itemGrants: ["void_shard"],
            },
          },
          {
            text: '"Before you ask — know that I won\'t open the Gate. Whatever your request, it cannot be that."',
            intent: "cautious",
            effects: {
              respect: 15,
              trust: 5,
              plotFlags: { vaelis_request_heard: true },
            },
          },
        ],
      },
    ],
  },
};

// ---------------------------------------------------------------------------
// Breaking Sequences — dramatic multi-turn cinematics at stage transitions
// ---------------------------------------------------------------------------

/**
 * Breaking sequences fire when a character crosses a breaking stage boundary.
 * These are the "breaking cinematics" — dramatic, character-defining moments
 * that make each stage transition feel like a major story beat.
 *
 * Each archetype has unique sequences reflecting how that kind of person breaks.
 * Generic sequences serve as fallbacks for archetypes without specific ones.
 */

export interface BreakingSequence {
  turns: DialogueTurn[];
}

/**
 * Get a breaking sequence for a character transitioning to a new stage.
 * Returns null if no sequence is defined (the toast notification still shows).
 */
export function getBreakingSequence(
  characterName: string,
  archetype: string,
  newStage: string,
): BreakingSequence | null {
  // Try archetype-specific first, fall back to generic
  const key = `${archetype}:${newStage}`;
  const specific = BREAKING_SEQUENCES[key];
  if (specific) return applyCharName(specific, characterName);

  const generic = BREAKING_SEQUENCES[`generic:${newStage}`];
  if (generic) return applyCharName(generic, characterName);

  return null;
}

function applyCharName(seq: BreakingSequence, name: string): BreakingSequence {
  return {
    turns: seq.turns.map((t) => ({
      ...t,
      text: t.text.replace(/\{name\}/g, name),
    })),
  };
}

const BREAKING_SEQUENCES: Record<string, BreakingSequence> = {
  // ── STRUGGLING (resistance drops below 80) ──────────────────────────
  "generic:struggling": {
    turns: [
      {
        speaker: "narrator",
        text: "*Something changes in {name}'s eyes. A flicker — not of fear, not yet. Something worse. Doubt. The kind that comes unbidden, unwanted, at three in the morning when the defenses are down. For just a moment, the mask slips.*",
      },
      {
        speaker: "narrator",
        text: "*{name}'s hands tighten at their sides. A breath catches — not quite a gasp, not quite a sigh. The composure returns, but slower than before. Like a wall rebuilt with fewer bricks each time.*",
      },
    ],
  },
  "ice:struggling": {
    turns: [
      {
        speaker: "narrator",
        text: "*The temperature in the room seems to drop. {name}'s perfect composure wavers — a micro-expression, gone before you could name it. Her jaw tightens. Her fingers, usually so still, grip the armrest hard enough to whiten her knuckles.*",
      },
      {
        speaker: "narrator",
        text: "*When she speaks again, her voice is colder than before. Overcompensating. You've seen this pattern in frozen lakes — the colder the surface, the more violently the water moves beneath.*",
      },
    ],
  },
  "warrior:struggling": {
    turns: [
      {
        speaker: "narrator",
        text: "*{name}'s stance shifts. It's subtle — a warrior wouldn't notice, but you're not just a warrior. The weight moves to her back foot. Defensive. For the first time since you've known her, she's not ready to attack.*",
      },
      {
        speaker: "narrator",
        text: "*She catches herself and squares her shoulders, but the damage is done. You both know you saw it. The silence between you carries the weight of that knowledge.*",
      },
    ],
  },
  "seductress:struggling": {
    turns: [
      {
        speaker: "narrator",
        text: "*{name}'s smile doesn't quite reach her eyes. The practiced tilt of her head, the calculated brush of fingers against collarbone — they're still perfect, but now you can see the machinery behind them. She knows you can see it. That's what frightens her.*",
      },
      {
        speaker: "narrator",
        text: "*For a heartbeat, the seductress is gone and the woman behind her stands naked — not in body, but in truth. Then the mask slides back into place, a little less smooth than before.*",
      },
    ],
  },

  // ── CONFLICTED (resistance drops below 60) ──────────────────────────
  "generic:conflicted": {
    turns: [
      {
        speaker: "narrator",
        text: "*{name} stops mid-sentence. Not a pause for effect — a genuine halt, as if two voices inside are arguing over what comes next. The silence stretches. When she speaks again, the words come slower, chosen with the painful care of someone who no longer trusts their own instincts.*",
      },
      {
        speaker: "narrator",
        text: "*You see it happen in real time: the war. Part of her leans toward you — drawn, wanting, despite everything. The other part recoils, ashamed of the wanting. Neither side is winning. Both sides are losing.*",
      },
      {
        speaker: "narrator",
        text: "*She looks at you, and for the first time, her expression holds a question she can't bring herself to ask. You recognize it. It's the question everyone asks before they break: 'Would it really be so terrible to stop fighting?'*",
      },
    ],
  },
  "innocent:conflicted": {
    turns: [
      {
        speaker: "narrator",
        text: "*{name}'s lip trembles. She turns away — not in defiance, but because she doesn't want you to see her face right now. When she turns back, her eyes are bright with unshed tears and something that looks disturbingly like gratitude.*",
      },
      {
        speaker: "narrator",
        text: "*'I don't understand,' she whispers, though you haven't asked a question. She wraps her arms around herself. 'I don't understand why I keep wanting to tell you things. I shouldn't. I know I shouldn't.' A pause. 'But I want to.'*",
      },
    ],
  },
  "defiant:conflicted": {
    turns: [
      {
        speaker: "narrator",
        text: "*{name} slams her fist against the wall. The impact echoes. She doesn't flinch from the pain — but she flinches from the reason she hit it. She's not angry at you. She's angry at herself, for the treasonous thought that just crossed her mind.*",
      },
      {
        speaker: "narrator",
        text: "*'Don't,' she says. Her voice cracks on the single syllable. 'Don't look at me like that. Like you already know how this ends.' The worst part is: you do. And so does she.*",
      },
    ],
  },

  // ── YIELDING (resistance drops below 40) ────────────────────────────
  "generic:yielding": {
    turns: [
      {
        speaker: "narrator",
        text: "*The change is unmistakable now. {name} waits for you to speak before speaking. Watches your face before choosing her expression. The resistance hasn't vanished — it's worse than that. It's become a performance, a ritual she goes through because she remembers that she's supposed to resist, even though the fire behind it died somewhere between the last time and this one.*",
      },
      {
        speaker: "narrator",
        text: "*She catches your eye and holds it a beat too long. There's no challenge in her gaze anymore. Just... waiting. The kind of waiting that means she's already decided to do whatever you say, and she's just giving herself a few more seconds to pretend she hasn't.*",
      },
      {
        speaker: "narrator",
        text: "*When she finally speaks, her voice has a new quality you haven't heard before. Soft. Not the softness of kindness or affection — the softness of something that was once rigid and has been bent past its breaking point. It doesn't spring back anymore.*",
      },
    ],
  },
  "shadow:yielding": {
    turns: [
      {
        speaker: "narrator",
        text: "*{name} stops hiding. That's the thing you notice first — the paranoia, the constant surveillance of exits and shadows, the way she always sat with her back to the wall. Gone. She sits with her back to the door now, facing you. It's the most vulnerable thing she's ever done.*",
      },
      {
        speaker: "narrator",
        text: "*'I kept secrets from everyone,' she says quietly. 'Secrets were my armor. My walls. My...' She trails off. Swallows. 'I don't want walls between us anymore. That's what scares me.' She meets your eyes. 'Not you. Not what you might do. What I might give you willingly.'*",
      },
    ],
  },

  // ── SURRENDERED (resistance drops below 20) ─────────────────────────
  "generic:surrendered": {
    turns: [
      {
        speaker: "narrator",
        text: "*{name} kneels. Not because you asked — you didn't. Not because anyone is watching — they aren't. She kneels because her body has learned something her mind is still trying to deny: this is where she belongs. At your feet. Waiting for direction. The gesture is so natural, so inevitable, that it takes you both a moment to realize what's happened.*",
      },
      {
        speaker: "narrator",
        text: "*She looks up at you from the floor, and the expression on her face is the most complicated thing you've ever seen. Relief. Shame. Desire. Gratitude. The devastation of a woman who fought a war against herself and finally, irrevocably, lost. 'Tell me what you want,' she says. It's not seduction. It's not submission. It's surrender — genuine, total, and terrifying in its completeness.*",
      },
    ],
  },
  "warrior:surrendered": {
    turns: [
      {
        speaker: "narrator",
        text: "*{name} unbuckles her sword belt. She holds the weapon for a moment — the weight of it, the familiarity, the identity it represents. Then she sets it on the ground at your feet. A warrior without her weapon is not a warrior. She knows what she's giving up. She does it anyway.*",
      },
      {
        speaker: "narrator",
        text: "*'I've fought everything,' she says, her voice steady despite the shaking in her hands. 'Armies. Monsters. Gods. I never lost.' A breath. 'I lost to you. And the worst part — the part I can never take back — is that I'm glad.'*",
      },
    ],
  },

  // ── BROKEN (resistance reaches 0) ──────────────────────────────────
  "generic:broken": {
    turns: [
      {
        speaker: "narrator",
        text: "*There is a sound a person makes when the last piece of who they were falls away. It's not a scream, not a sob, not a whimper. It's a breath. The quietest, most final sound in the world — the exhalation of a self that no longer exists. {name} makes that sound now.*",
      },
      {
        speaker: "narrator",
        text: "*What remains is still her — her face, her voice, her body. But the light behind her eyes has changed. It doesn't burn anymore. It reflects. Whatever you show her, she becomes. Whatever you want her to feel, she feels. She has been broken the way a horse is broken: the wildness isn't gone, but it answers to a new master now.*",
      },
      {
        speaker: "narrator",
        text: "*She smiles at you, and it's the most genuine smile she's ever given you, because for the first time there's nothing behind it — no strategy, no defense, no secret self held in reserve. Just her. Yours. Completely. Irreversibly. She will never be who she was. What you've built in her place is something new.*",
      },
    ],
  },
  "ice:broken": {
    turns: [
      {
        speaker: "narrator",
        text: "*The ice breaks. Not with a crash or a shatter — with a thaw. Slow, irreversible, like spring arriving at a glacier. {name}'s eyes, which have been winter for as long as anyone can remember, fill with a warmth that has nowhere to go and no way to stop. The cold was never her nature. It was her fortress. And you've burned it to the ground.*",
      },
      {
        speaker: "narrator",
        text: "*She reaches for you. Not with the calculated precision she touches everything else. She reaches with the desperate, clumsy urgency of someone who has never needed anything before and is terrified by how much she needs this. 'Don't go,' she says. Two words. The first honest words she's spoken in years.*",
      },
    ],
  },
};

export const FLAG_DESCRIPTIONS: Record<string, string> = {
  met_isolde: "Met Isolde in the throne room",
  met_mira: "Met Mira in the tavern",
  met_kael: "Met Kael in the undercroft",
  met_vaelis: "Met Vaelis at the Crimson Gate",
  met_seraphine: "Met Seraphine at the Oracle's Spire",
  undercroft_unlocked: "Mira revealed the undercroft entrance (trust >= 40)",
  mira_trusts_player: "Mira trusts the player enough to share secrets (trust >= 40)",
  crimson_gate_known: "Learned about the Crimson Gate from Kael or Isolde",
  kael_reveals_gate: "Kael told you about the tunnel to the Gate (trust >= 30)",
  vaelis_grants_passage: "Vaelis allows passage past the Gate (respect >= 50)",
  seraphine_invites_player: "Seraphine invites you into the vision chamber (trust >= 40)",
  knows_kael_is_prince: "Discovered Kael's royal identity",
  isolde_proposal_heard: "Heard Isolde's proposal to serve her",
  chose_serve_isolde: "Chose to serve Isolde",
  chose_defy_isolde: "Chose to defy Isolde",
  isolde_ultimatum_faced: "Faced Isolde's ultimatum after defying her",
  mira_confession_heard: "Heard Mira's confession about the regicide",
  mira_truth_serum_offered: "Mira offered her mother's truth serum",
  accepted_truth_serum: "Accepted Mira's truth serum plan",
  rejected_truth_serum: "Rejected Mira's truth serum plan",
  kael_crisis_resolved: "Helped Kael through his crisis about his father",
  kael_comforted: "Comforted Kael during his crisis",
  kael_blood_key_known: "Learned that Kael carries the blood key to the Gate",
  vaelis_request_heard: "Heard Vaelis's first request in four hundred years",
  saw_peaceful_future: "Saw the peaceful future in Seraphine's mirrors",
  destroyed_mirrors: "Destroyed Seraphine's prophetic mirrors",
};

/**
 * Relationship thresholds that trigger flag changes.
 * Checked after every choice to unlock new paths.
 */
export function checkRelationshipFlags(
  characters: Record<string, { relationship: { trust: number; respect: number; affection: number } }>
): Record<string, boolean> {
  const newFlags: Record<string, boolean> = {};

  const mira = characters.mira;
  if (mira && mira.relationship.trust >= 40) {
    newFlags.mira_trusts_player = true;
    newFlags.undercroft_unlocked = true;
  }

  const kael = characters.kael;
  if (kael && kael.relationship.trust >= 30) {
    newFlags.kael_reveals_gate = true;
    newFlags.crimson_gate_known = true;
  }

  const vaelis = characters.vaelis;
  if (vaelis && vaelis.relationship.respect >= 50) {
    newFlags.vaelis_grants_passage = true;
  }

  const seraphine = characters.seraphine;
  if (seraphine && seraphine.relationship.trust >= 40) {
    newFlags.seraphine_invites_player = true;
  }

  return newFlags;
}
