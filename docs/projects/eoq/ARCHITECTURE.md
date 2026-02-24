# Empire of Broken Queens — Architecture

*AI-driven interactive cinematic adult game. Adult content is intentional and central.*

---

## Core Insight

The hardest problem isn't generation — it's coherence over time. An LLM generating dialogue for a single scene is straightforward. An LLM maintaining consistent character personality, remembering previous interactions, tracking relationship state, and producing dialogue that advances a narrative arc across dozens of sessions — that's a state management problem disguised as a generation problem.

**The prompt is not the intelligence — the state management is.**

Character consistency comes from what's IN the prompt, not the model's "memory." A well-constructed prompt with rich character state produces coherent dialogue from almost any capable model. A poorly-constructed prompt produces incoherent dialogue from even the best model. The state store is the most important component — not the model.

---

## Narrative State Store

```
┌─────────────────────────────────────────┐
│           Narrative State Store           │
│  (SQLite initially, PostgreSQL if needed)│
│                                           │
│  Characters:                              │
│    - personality vectors (fixed per char) │
│    - relationship scores (mutable)        │
│    - memory log (append-only)             │
│    - current emotional state (mutable)    │
│    - character-specific speech patterns   │
│    - boundaries and preferences           │
│                                           │
│  World State:                             │
│    - scene graph (current location)       │
│    - time progression                     │
│    - plot flags (branching state)         │
│    - inventory / resources                │
│    - environmental conditions             │
│                                           │
│  Session History:                         │
│    - last N dialogue exchanges            │
│    - key decisions made                   │
│    - narrative arc position               │
│    - player preference signals            │
└─────────────────────────────────────────┘
```

---

## Dialogue Generation Pipeline

```
Player input
  → Game engine parses intent
  → Load character + world state from state store
  → Construct prompt:
      - Character personality vector
      - Relationship context (this character ↔ player)
      - Scene description and emotional tone
      - Recent dialogue history (last N exchanges)
      - Narrative constraints (plot flags, arc position)
      - Player preference signals
  → Generate via local abliterated model (vLLM on Node 1 or Node 2)
  → Validate output:
      - Character consistency check (does this sound like them?)
      - Narrative coherence check (does this contradict established facts?)
      - Content bounds check (custom, not cloud safety filters)
      - If validation fails → regenerate with adjusted constraints
  → Update state store:
      - Append to character memory log
      - Update relationship scores based on interaction
      - Update emotional state
      - Advance plot flags if applicable
  → Return dialogue + scene direction to game client
```

### Model Routing

Cloud models handle most development work — architecture, code, UI, state management, database schemas. The line is specific operations that cloud providers refuse: explicitly sexual dialogue generation, uncensored image/video prompts, content that triggers safety filters.

Even within EoBQ, different pipeline steps route to different models:
- Steps 1, 2, 4, 5 (parsing, state loading, validation, state update) — can use cloud models
- Step 3 (dialogue generation) — **MUST be local abliterated model**

---

## Asset Generation Pipeline

- Scene images generated via ComfyUI (Flux/SDXL) using scene descriptions from narrative state
- Character expressions generated dynamically or from LoRA-trained models for visual consistency
- Video generation (Wan 2.2) for cinematic moments — cutscenes, transitions, key narrative beats
- All generation runs on Node 2 GPUs:
  - RTX 5090 (32GB) — primary for high-res generation and LLM time-sharing
  - RTX 5060 Ti (16GB) — currently running Flux dev FP8
- The model is swappable — upgrade architectures without touching the narrative system

---

## Development Environment Requirements

The dev environment must also be a testing environment for runtime LLM calls. This is unique to EoBQ — most software projects don't call an LLM at runtime.

### Mock Mode

Simulate LLM responses during UI iteration so you don't burn GPU cycles while tweaking layout and flow. Pre-recorded responses or simple template-based generation.

### Quality Evaluation

Acceptance criteria for generated text — does this dialogue meet minimum coherence, character consistency, and narrative advancement thresholds? Automated scoring via a second model or heuristic checks.

### Regression Testing

After model changes (new model version, different quantization, engine upgrade), run the same prompts through and compare output quality. Catch degradation before it reaches players.

### Inference Stack as Test Dependency

The vLLM stack on Athanor becomes part of the test environment. CI/CD for EoBQ needs to know the inference stack is healthy.

---

## Existing Assets

ComfyUI workflows exist at `projects/eoq/comfyui/` — image generation workflows for scene rendering.

---

## Infrastructure Dependencies

| Component | Provided By | Notes |
|-----------|-------------|-------|
| Abliterated LLM | vLLM on Node 1 or Node 2 | Required for explicit dialogue |
| Image generation | ComfyUI on Node 2 | Flux/SDXL for scene images |
| Video generation | ComfyUI on Node 2 | Wan 2.2 for cinematics |
| State storage | SQLite → PostgreSQL | Narrative state store |
| Embedding search | Qdrant on Node 1:6333 | Character memory retrieval |
| Model routing | LiteLLM on VAULT:4000 | Routes to correct backend |
