# Empire of Broken Queens — Architecture

*AI-driven interactive cinematic adult game. Adult content is intentional and central.*

---

## Core Insight

The hardest problem isn't generation — it's coherence over time. An LLM generating dialogue for a single scene is straightforward. An LLM maintaining consistent character personality, remembering previous interactions, tracking relationship state, and producing dialogue that advances a narrative arc across dozens of sessions — that's a state management problem disguised as a generation problem.

**The prompt is not the intelligence — the state management is.**

Character consistency comes from what's IN the prompt, not the model's "memory." A well-constructed prompt with rich character state produces coherent dialogue from almost any capable model.

---

## Design Lineage

The implementation reconciles three source documents from the Gaming-Ideas repo:

| Document | Key Contributions |
|----------|------------------|
| `EMPIRE_OF_BROKEN_QUEENS_GDD.md` | Queen archetypes (12), breaking system (6 stages), Resistance/Corruption stats, breaking methods (Physical/Psychological/Magical/Social), content intensity levels |
| `DIALOGUE_SYSTEM_DESIGN.md` | Emotional profile (Fear/Defiance/Arousal/Submission/Despair), dialogue node types, branching conditions, memory-triggered dialogue |
| `STORYTELLING_MASTERY_FRAMEWORK.md` | Power asymmetry, resistance/erosion patterns, transformation narrative, Stockholm progression |

**What was adopted:**
- Breaking system with Resistance (0-100) and Corruption (0-100) per character
- Breaking stages derived from resistance (Defiant/Struggling/Conflicted/Yielding/Surrendered/Broken)
- 5-axis emotional profile (Fear/Defiance/Arousal/Submission/Despair) per character
- Queen archetypes (12 types) informing personality and vulnerability
- Vulnerability map per character (which breaking methods are effective)
- Content intensity levels (1-5)
- Player choice → breaking method mapping

**What was adapted:**
- The GDD's 12-queen strategy game → 5-character interactive novel format
- Kingdom management/army systems → scene graph with conditional exits
- Per-queen 5-chapter arcs → unified narrative arc with plot flags
- Queen stats (RES/COR/LOY/ABL/BTY/INT) → simplified to resistance/corruption alongside existing relationship axes

**What was deferred:**
- Multiple campaigns, resource management, army systems
- Separate breaking interface/minigame
- Per-queen dedicated storylines (future acts)

---

## Current Stack

```
Next.js 16 + React 19 + Tailwind + Zustand
├── src/types/game.ts          — Type system (Character, Breaking, Emotional)
├── src/data/characters.ts     — 5 characters with full stat blocks
├── src/data/scenes.ts         — 8 scenes, conditional scene graph
├── src/data/narrative.ts      — Arc progression, scripted intros, flag system
├── src/stores/game-store.ts   — Zustand store with localStorage persistence
├── src/hooks/use-game-engine.ts — Game engine (scene nav, dialogue, effects)
├── src/app/page.tsx           — Main game UI
├── src/app/api/chat/route.ts  — LLM dialogue via LiteLLM SSE
├── src/app/api/generate/route.ts — ComfyUI image generation
└── comfyui/*.json             — Flux workflows (portrait 832x1216, scene 1344x768)
```

---

## Character System

Each character has:

| Layer | Fields | Mutability |
|-------|--------|-----------|
| Identity | id, name, title, archetype, speechStyle, visualDescription, boundaries | Fixed |
| Personality | 8-axis vector (dominance, warmth, cunning, loyalty, cruelty, sensuality, humor, ambition) | Fixed |
| Relationship | trust, affection, respect, desire, fear, memories | Mutable per choice |
| Breaking | resistance (0-100), corruption (0-100), vulnerabilities | Mutable per choice |
| Emotion | simple label + intensity, plus 5-axis emotional profile | Mutable per interaction |

**Breaking stage** is derived (not stored) from resistance level:
- 80-100: Defiant — hostile, unyielding
- 60-79: Struggling — cracks showing
- 40-59: Conflicted — torn
- 20-39: Yielding — resistance fading
- 1-19: Surrendered — broken will
- 0: Broken — total submission

**Vulnerabilities** map breaking methods to effectiveness (-1 to 1):
- Positive = effective
- Negative = resistant
- 0 = neutral

---

## Narrative State Store

```
┌─────────────────────────────────────────┐
│           Zustand + localStorage         │
│                                          │
│  Characters:                             │
│    - personality vectors (fixed)         │
│    - relationship scores (mutable)       │
│    - resistance / corruption (mutable)   │
│    - emotional profile (mutable)         │
│    - memory log (append-only)            │
│    - vulnerability map (fixed)           │
│                                          │
│  World State:                            │
│    - scene graph + current location      │
│    - time of day / day number            │
│    - plot flags (boolean map)            │
│    - inventory                           │
│    - content intensity level             │
│                                          │
│  Session:                                │
│    - dialogue history                    │
│    - narrative arc position              │
│    - visited scenes set                  │
└─────────────────────────────────────────┘
```

---

## Dialogue Generation Pipeline

```
Player input / click to continue
  → Check scripted queue (authored story beats play first)
  → If no scripted content: call LLM via /api/chat
      → Build system prompt from full character state:
          - Personality, archetype, speech style
          - Relationship with player
          - Breaking stage + stage-specific behavioral guidance
          - Emotional profile (Fear/Defiance/Arousal/Submission/Despair)
          - Scene context, memories
          - Content intensity ceiling
      → Stream SSE via LiteLLM → vLLM (Qwen3-32B-AWQ)
      → Strip <think> blocks from reasoning models
  → Display with character-by-character streaming
  → Update state store after dialogue completes
```

---

## Scene Graph (Act 1)

```
[courtyard] ←→ [throne-room] → [throne-close]
    ↓
[tavern] → [undercroft] → [crimson-gate] → [oracle-spire] → [vision-chamber]
           (mira_trusts)  (kael_reveals)   (vaelis_grants)   (seraphine_invites)
```

Conditional exits require plot flags. Flags are earned through:
1. Scripted choices (e.g., `met_isolde`)
2. Relationship thresholds (e.g., Mira trust >= 40 → `undercroft_unlocked`)
3. Arc transitions (e.g., met 3+ characters → `gathering_allies`)

---

## Asset Generation Pipeline

- Scene images: ComfyUI + Flux dev FP8 (1344x768 landscape)
- Character portraits: ComfyUI + Flux dev FP8 (832x1216 portrait)
- Workflow JSONs in `comfyui/` — prompt and seed injected at runtime
- Future: Uncensored LoRA for NSFW content, Wan2.x T2V for cinematics
- All generation on Node 2 GPUs (5090 32GB + 5060 Ti 16GB)

---

## Infrastructure Dependencies

| Component | Provided By | Notes |
|-----------|-------------|-------|
| Dialogue LLM | vLLM on Node 1 via LiteLLM | Qwen3-32B-AWQ, SSE streaming |
| Image generation | ComfyUI on Node 2 | Flux dev FP8 |
| State storage | Zustand + localStorage | Client-side, JSON serialization |
| Model routing | LiteLLM on VAULT:4000 | `reasoning` alias |
| Deploy target | Node 2:3002 | Docker, Ansible-managed |

---

Last updated: 2026-02-26
