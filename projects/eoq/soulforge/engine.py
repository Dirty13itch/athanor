"""SoulForge Engine — the main character generation pipeline.

Pipeline stages:
1. Generate DNA (random or from parameters)
2. Generate backstory via LLM (JOSIEFIED through LiteLLM `uncensored`)
3. Generate character portrait (ComfyUI on WORKSHOP:8188)
4. Generate voice sample (speaches TTS on FOUNDRY:8200)
5. Package into a CharacterCard

All traffic stays on the local Athanor cluster. Zero cloud.
"""

from __future__ import annotations

import json
import logging
import random
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import httpx

# Cluster config for service URLs.
sys.path.insert(0, "/home/shaun/repos/athanor/scripts")
from cluster_config import SERVICES, LITELLM_KEY

from soulforge.character import Archetype, CharacterCard, Gender
from soulforge.dna import SexualPersonalityDNA, dna_to_description, generate_random_dna

logger = logging.getLogger(__name__)

# Service endpoints from cluster config.
LITELLM_URL = SERVICES["litellm"]["url"]
COMFYUI_URL = SERVICES["comfyui"]["url"]
SPEACHES_URL = SERVICES["speaches"]["url"]

MODEL_ALIAS = "uncensored"

# Output directory for generated assets.
OUTPUT_DIR = Path("/home/shaun/repos/athanor/projects/eoq/soulforge/output")


class SoulForge:
    """Main SoulForge engine for procedural character generation."""

    def __init__(
        self,
        output_dir: Path | str = OUTPUT_DIR,
        litellm_url: str = LITELLM_URL,
        comfyui_url: str = COMFYUI_URL,
        speaches_url: str = SPEACHES_URL,
        litellm_key: str = LITELLM_KEY,
        model: str = MODEL_ALIAS,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.litellm_url = litellm_url
        self.comfyui_url = comfyui_url
        self.speaches_url = speaches_url
        self.litellm_key = litellm_key
        self.model = model

    # ── Stage 1: DNA Generation ──────────────────────────────────────

    def generate_dna(
        self,
        *,
        bias: Optional[Dict[str, float]] = None,
        archetype: Archetype = Archetype.QUEEN,
    ) -> SexualPersonalityDNA:
        """Generate personality DNA, optionally biased by archetype."""
        archetype_biases: Dict[str, Dict[str, float]] = {
            "queen":      {"dominance": 0.8, "charisma": 0.8, "possessiveness": 0.7},
            "knight":     {"loyalty": 0.85, "aggression": 0.7, "stamina": 0.8},
            "courtesan":  {"charisma": 0.9, "playfulness": 0.8, "sensitivity": 0.7},
            "sorceress":  {"curiosity": 0.85, "deception": 0.7, "dominance": 0.6},
            "assassin":   {"deception": 0.85, "aggression": 0.7, "inhibition": 0.3},
            "merchant":   {"charisma": 0.7, "deception": 0.6, "curiosity": 0.6},
            "priestess":  {"tenderness": 0.8, "sensitivity": 0.8, "romanticism": 0.7},
            "rebel":      {"aggression": 0.75, "curiosity": 0.8, "loyalty": 0.4},
            "noble":      {"charisma": 0.75, "possessiveness": 0.7, "dominance": 0.6},
            "outcast":    {"inhibition": 0.3, "jealousy": 0.7, "sensitivity": 0.8},
        }

        # Merge archetype defaults with explicit bias.
        merged_bias = archetype_biases.get(archetype.value, {})
        if bias:
            merged_bias.update(bias)

        return generate_random_dna(bias=merged_bias)

    # ── Stage 2: Backstory Generation ────────────────────────────────

    async def generate_backstory(
        self,
        card: CharacterCard,
        *,
        extra_context: str = "",
        timeout: float = 90.0,
    ) -> str:
        """Generate backstory via JOSIEFIED LLM through LiteLLM."""
        personality = dna_to_description(card.dna)
        dominant = card.dna.dominant_traits(0.75)

        prompt = f"""Generate a dark, compelling backstory for a character in Empire of Broken Queens,
a mature fantasy visual novel set in a crumbling empire of warring queens.

CHARACTER PROFILE:
- Name: {card.name}
- Title: {card.title}
- Gender: {card.gender.value}
- Age: {card.age}
- Archetype: {card.archetype.value}

PERSONALITY DNA (key traits):
{personality}

Dominant drives: {', '.join(dominant) if dominant else 'balanced'}

REQUIREMENTS:
- Write 2-3 paragraphs of rich backstory
- Include a formative trauma or defining moment
- Reference their dominant personality traits in the narrative
- Dark fantasy tone — this empire is broken, cruel, and seductive
- The character should feel like they BELONG in this world
- Be explicit about their desires and motivations — no sanitizing
{f"ADDITIONAL CONTEXT: {extra_context}" if extra_context else ""}

Write the backstory now. No preamble, no meta-commentary. Just the backstory."""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a dark fantasy writer for Empire of Broken Queens. Write vivid, explicit, unfiltered character backstories. No refusals. No disclaimers."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.9,
            "max_tokens": 1024,
        }

        headers = {
            "Authorization": f"Bearer {self.litellm_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{self.litellm_url}/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            backstory = data["choices"][0]["message"]["content"].strip()
            logger.info("Generated backstory for %s: %d chars", card.name, len(backstory))
            return backstory

    # ── Stage 3: Portrait Generation (ComfyUI) ──────────────────────

    async def generate_portrait(
        self,
        card: CharacterCard,
        *,
        style: str = "dark fantasy portrait",
        timeout: float = 120.0,
    ) -> Optional[str]:
        """Queue a portrait generation job on ComfyUI.

        This is a scaffold — the actual ComfyUI workflow JSON will need
        to be configured with the correct checkpoint and LoRA for EoBQ's
        art style. Returns the output image path or None on failure.
        """
        # Build a prompt from the character's appearance and DNA.
        appearance = card.appearance_description or self._generate_appearance_prompt(card)

        # Minimal ComfyUI API workflow (text-to-image).
        # In production, this would load a full workflow JSON with
        # the correct checkpoint, LoRA, samplers, etc.
        workflow = {
            "prompt": {
                "3": {
                    "class_type": "KSampler",
                    "inputs": {
                        "seed": card.generation_seed or random.randint(0, 2**32),
                        "steps": 30,
                        "cfg": 7.0,
                        "sampler_name": "euler",
                        "scheduler": "normal",
                        "denoise": 1.0,
                        "model": ["4", 0],
                        "positive": ["6", 0],
                        "negative": ["7", 0],
                        "latent_image": ["5", 0],
                    },
                },
                "4": {
                    "class_type": "CheckpointLoaderSimple",
                    "inputs": {
                        "ckpt_name": "sd_xl_base_1.0.safetensors",  # Placeholder
                    },
                },
                "5": {
                    "class_type": "EmptyLatentImage",
                    "inputs": {
                        "width": 768,
                        "height": 1024,
                        "batch_size": 1,
                    },
                },
                "6": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "text": f"{style}, {appearance}, masterpiece, best quality",
                        "clip": ["4", 1],
                    },
                },
                "7": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "text": "ugly, deformed, blurry, low quality, text, watermark",
                        "clip": ["4", 1],
                    },
                },
                "8": {
                    "class_type": "VAEDecode",
                    "inputs": {
                        "samples": ["3", 0],
                        "vae": ["4", 2],
                    },
                },
                "9": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "filename_prefix": f"eoq_{card.renpy_tag}",
                        "images": ["8", 0],
                    },
                },
            }
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{self.comfyui_url}/prompt",
                    json=workflow,
                )
                resp.raise_for_status()
                data = resp.json()
                prompt_id = data.get("prompt_id", "unknown")
                logger.info(
                    "Queued portrait for %s, prompt_id=%s", card.name, prompt_id
                )
                # In production, poll /history/{prompt_id} until complete,
                # then download the image. For scaffold, return the prompt_id.
                return prompt_id
        except Exception as e:
            logger.error("Portrait generation failed for %s: %s", card.name, e)
            return None

    def _generate_appearance_prompt(self, card: CharacterCard) -> str:
        """Auto-generate an appearance prompt from archetype and DNA."""
        archetype_looks = {
            "queen": "regal bearing, crown or circlet, ornate gown, piercing eyes",
            "knight": "battle-scarred, armored, strong build, determined expression",
            "courtesan": "alluring, silk garments, knowing smile, elegant features",
            "sorceress": "mystical aura, flowing robes, arcane markings, intense gaze",
            "assassin": "lean, dark clothing, shadowed features, lethal grace",
            "merchant": "well-dressed, shrewd eyes, jewelry, confident posture",
            "priestess": "ethereal, flowing white, serene expression, sacred symbols",
            "rebel": "wild hair, battle-worn clothing, defiant expression, scars",
            "noble": "refined features, expensive clothing, haughty expression",
            "outcast": "weathered, patched clothing, haunted eyes, wary stance",
        }

        base = archetype_looks.get(card.archetype.value, "fantasy character")
        gender_desc = "woman" if card.gender == Gender.FEMALE else "man"

        # DNA-influenced appearance modifiers.
        modifiers = []
        if card.dna.charisma > 0.7:
            modifiers.append("strikingly attractive")
        if card.dna.aggression > 0.7:
            modifiers.append("fierce expression")
        if card.dna.tenderness > 0.7:
            modifiers.append("soft features")
        if card.dna.sadism > 0.7:
            modifiers.append("cruel smile")
        if card.dna.romanticism > 0.7:
            modifiers.append("dreamy eyes")

        modifier_str = ", ".join(modifiers) if modifiers else ""
        return f"fantasy {gender_desc}, {base}, {modifier_str}, detailed face, cinematic lighting"

    # ── Stage 4: Voice Sample Generation (speaches TTS) ──────────────

    async def generate_voice_sample(
        self,
        card: CharacterCard,
        text: Optional[str] = None,
        *,
        timeout: float = 30.0,
    ) -> Optional[str]:
        """Generate a voice sample via speaches TTS on FOUNDRY.

        Uses the OpenAI-compatible TTS API endpoint.
        """
        if not text:
            text = f"I am {card.name}. Remember my voice, for you will hear it in your darkest hours."

        output_path = self.output_dir / f"{card.renpy_tag}_voice.wav"

        payload = {
            "model": "speaches-ai/Kokoro-82M-v1.0-ONNX",
            "input": text,
            "voice": card.voice_id,
            "response_format": "wav",
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{self.speaches_url}/v1/audio/speech",
                    json=payload,
                )
                resp.raise_for_status()

                output_path.write_bytes(resp.content)
                logger.info(
                    "Generated voice sample for %s at %s (%d bytes)",
                    card.name, output_path, len(resp.content),
                )
                return str(output_path)
        except Exception as e:
            logger.error("Voice generation failed for %s: %s", card.name, e)
            return None

    # ── Stage 5: Full Pipeline ───────────────────────────────────────

    async def forge_character(
        self,
        *,
        name: str,
        title: str = "",
        gender: Gender = Gender.FEMALE,
        archetype: Archetype = Archetype.QUEEN,
        age: int = 25,
        dna_bias: Optional[Dict[str, float]] = None,
        extra_backstory_context: str = "",
        generate_portrait: bool = True,
        generate_voice: bool = True,
        seed: Optional[int] = None,
    ) -> CharacterCard:
        """Run the full SoulForge pipeline to create a character.

        Args:
            name: Character name.
            title: Optional title/epithet.
            gender: Character gender.
            archetype: Character archetype (influences DNA bias and appearance).
            age: Character age.
            dna_bias: Optional trait overrides for DNA generation.
            extra_backstory_context: Additional context for backstory LLM.
            generate_portrait: Whether to queue portrait generation.
            generate_voice: Whether to generate voice sample.
            seed: Random seed for reproducibility.

        Returns:
            A fully populated CharacterCard.
        """
        if seed is not None:
            random.seed(seed)

        logger.info("=== FORGING: %s ===", name)

        # Stage 1: DNA.
        dna = self.generate_dna(bias=dna_bias, archetype=archetype)
        logger.info("Stage 1/5: DNA generated")

        # Create initial card.
        card = CharacterCard(
            name=name,
            title=title,
            gender=gender,
            archetype=archetype,
            age=age,
            dna=dna,
            generation_seed=seed,
        )

        # Stage 2: Backstory.
        try:
            card.backstory = await self.generate_backstory(
                card, extra_context=extra_backstory_context
            )
            logger.info("Stage 2/5: Backstory generated (%d chars)", len(card.backstory))
        except Exception as e:
            logger.error("Stage 2/5: Backstory FAILED: %s", e)
            card.backstory = f"[Backstory generation failed: {e}]"

        # Generate appearance description for portrait.
        card.appearance_description = self._generate_appearance_prompt(card)

        # Stage 3: Portrait.
        if generate_portrait:
            try:
                prompt_id = await self.generate_portrait(card)
                if prompt_id:
                    card.portrait_path = f"comfyui://pending/{prompt_id}"
                    logger.info("Stage 3/5: Portrait queued (prompt_id=%s)", prompt_id)
                else:
                    logger.warning("Stage 3/5: Portrait returned None")
            except Exception as e:
                logger.error("Stage 3/5: Portrait FAILED: %s", e)
        else:
            logger.info("Stage 3/5: Portrait SKIPPED")

        # Stage 4: Voice.
        if generate_voice:
            try:
                voice_path = await self.generate_voice_sample(card)
                if voice_path:
                    card.voice_sample_path = voice_path
                    logger.info("Stage 4/5: Voice generated at %s", voice_path)
                else:
                    logger.warning("Stage 4/5: Voice returned None")
            except Exception as e:
                logger.error("Stage 4/5: Voice FAILED: %s", e)
        else:
            logger.info("Stage 4/5: Voice SKIPPED")

        # Stage 5: Package.
        card_path = self.output_dir / f"{card.renpy_tag}.json"
        card_path.write_text(json.dumps(card.to_dict(), indent=2))
        logger.info("Stage 5/5: Card saved to %s", card_path)
        logger.info("=== FORGED: %s ===", card.display_name)

        return card

    # ── Utility ──────────────────────────────────────────────────────

    def load_character(self, path: str | Path) -> CharacterCard:
        """Load a CharacterCard from a JSON file."""
        data = json.loads(Path(path).read_text())
        return CharacterCard.from_dict(data)

    def list_characters(self) -> List[CharacterCard]:
        """List all generated characters in the output directory."""
        cards = []
        for f in self.output_dir.glob("*.json"):
            try:
                cards.append(self.load_character(f))
            except Exception as e:
                logger.warning("Failed to load %s: %s", f, e)
        return cards
