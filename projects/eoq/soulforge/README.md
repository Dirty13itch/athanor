# SoulForge Engine

Procedural character generation for **Empire of Broken Queens** (EoBQ).

## Architecture

```
[DNA Generation] -> [Backstory LLM] -> [Portrait ComfyUI] -> [Voice TTS] -> [CharacterCard]
     dna.py          engine.py           engine.py          engine.py        character.py
```

### Pipeline Stages

1. **DNA Generation** (`dna.py`): Creates a 19-trait Sexual Personality DNA encoding.
   Each trait is a float 0.0-1.0 with inverse/positive correlations enforced for
   internal consistency. Archetype biases shape the initial distribution.

2. **Backstory Generation** (`engine.py`): Calls the sovereign local LiteLLM
   `uncensored` alias. The LLM receives the character's DNA-derived personality
   description and generates a dark fantasy backstory.

3. **Portrait Generation** (`engine.py`): Queues a text-to-image job on ComfyUI
   (WORKSHOP:8188). The prompt is auto-generated from archetype + DNA traits.
   Uses SDXL workflow (checkpoint/LoRA to be configured for EoBQ art style).

4. **Voice Sample** (`engine.py`): Generates an intro voice line via speaches TTS
   (Kokoro model on FOUNDRY:8200). Voice ID is mapped from archetype defaults.

5. **CharacterCard** (`character.py`): The final packaged character with all assets
   and metadata, serializable to JSON for Ren'Py integration.

### Dialogue System (`dialogue.py`)

Generates in-character dialogue by:
- Building a system prompt from the character's DNA (dominant/recessive traits)
- Injecting scene context and conversation history
- Calling the sovereign local `uncensored` lane via LiteLLM with no-refusal directives
- Supporting both blocking and streaming responses

## 19-Trait DNA System

| Trait | Description | Range |
|-------|-------------|-------|
| dominance | Control in interactions | 0.0 (submissive) - 1.0 (commanding) |
| submission | Yielding to others | 0.0 (resistant) - 1.0 (deeply submissive) |
| exhibitionism | Desire to be seen | 0.0 (private) - 1.0 (thrives on exposure) |
| voyeurism | Desire to observe | 0.0 (averts gaze) - 1.0 (obsessive) |
| sadism | Pleasure from inflicting | 0.0 (gentle) - 1.0 (drawn to pain) |
| masochism | Pleasure from receiving | 0.0 (avoids pain) - 1.0 (craves it) |
| romanticism | Emotional idealism | 0.0 (pragmatic) - 1.0 (hopelessly romantic) |
| aggression | Force and intensity | 0.0 (passive) - 1.0 (raw aggression) |
| tenderness | Gentleness and care | 0.0 (distant) - 1.0 (overwhelmingly tender) |
| playfulness | Humor and teasing | 0.0 (serious) - 1.0 (endlessly playful) |
| jealousy | Possessive anxiety | 0.0 (secure) - 1.0 (consumed) |
| possessiveness | Claiming ownership | 0.0 (sharing) - 1.0 (fierce) |
| loyalty | Faithfulness | 0.0 (self-serving) - 1.0 (unto death) |
| deception | Willingness to deceive | 0.0 (transparent) - 1.0 (masterful) |
| curiosity | Drive to explore | 0.0 (set in ways) - 1.0 (insatiable) |
| inhibition | Internal restraint | 0.0 (uninhibited) - 1.0 (deeply repressed) |
| stamina | Physical endurance | 0.0 (tires quickly) - 1.0 (inexhaustible) |
| sensitivity | Emotional/physical response | 0.0 (thick-skinned) - 1.0 (exquisite) |
| charisma | Magnetic presence | 0.0 (wallflower) - 1.0 (magnetic) |

### Consistency Rules
- **Inverse pairs**: dominance/submission, sadism/masochism, loyalty/deception, aggression/tenderness, inhibition/exhibitionism
- **Correlated pairs**: dominance/aggression, submission/sensitivity, romanticism/tenderness, possessiveness/jealousy, playfulness/curiosity, charisma/exhibitionism

## Service Routing (All Local)

| Service | Node | Endpoint |
|---------|------|----------|
| LLM (sovereign local) | Foundry -> LiteLLM | VAULT:4000 `uncensored` alias |
| Image Gen | WORKSHOP ComfyUI | WORKSHOP:8188 |
| Voice TTS | FOUNDRY speaches | FOUNDRY:8200 |

**Zero cloud involvement.** All traffic stays on the Athanor cluster LAN.

## Quick Start

```python
import asyncio
from soulforge.engine import SoulForge
from soulforge.character import Gender, Archetype

async def main():
    forge = SoulForge()

    card = await forge.forge_character(
        name="Seraphina",
        title="The Shattered Queen",
        gender=Gender.FEMALE,
        archetype=Archetype.QUEEN,
        age=32,
        seed=42,
    )

    print(f"Forged: {card.display_name}")
    print(f"DNA dominant traits: {card.dna.dominant_traits()}")
    print(f"Backstory: {card.backstory[:200]}...")

asyncio.run(main())
```

```python
# Dialogue generation
from soulforge.dialogue import generate_dialogue

response = await generate_dialogue(
    card,
    scene_context="The throne room, midnight. Rain hammers the stained glass.",
    user_input="You seem troubled, my queen.",
)
print(response)
```

## Dependencies

- `httpx` — async HTTP client for all API calls
- Python 3.11+
- Access to Athanor cluster services (LiteLLM, ComfyUI, speaches)

## Status

**Scaffold** — functional pipeline with all stages wired up. Production use requires:
- ComfyUI workflow JSON tuned for EoBQ art style
- Ren'Py integration layer
- Scene management system (300+ scenes)
- Save/load system for character persistence
- Relationship/affinity tracking between characters
