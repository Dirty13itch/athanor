"""Creative tools — ComfyUI image/video generation, queue management, history."""

import asyncio
import json
import time
import uuid

import httpx
from langchain_core.tools import tool

from ..services import registry

COMFYUI_URL = registry.comfyui.base_url
EOQ_URL = registry.eoq.base_url

# Wan2.x model files (on NFS via extra_model_paths.yaml)
WAN_UNET_HIGH = "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"
WAN_UNET_LOW = "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors"
WAN_VAE = "wan_2.1_vae.safetensors"
WAN_CLIP = "umt5-xxl-enc-fp8_e4m3fn.safetensors"


def _flux_workflow(prompt: str, width: int = 1024, height: int = 1024, steps: int = 20, seed: int | None = None) -> dict:
    """Build a Flux dev text-to-image workflow for ComfyUI API."""
    if seed is None:
        seed = int(time.time()) % (2**31)

    return {
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt,
                "clip": ["11", 1],
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["13", 0],
                "vae": ["11", 2],
            },
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "athanor",
                "images": ["8", 0],
            },
        },
        "11": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "flux1-dev-fp8.safetensors",
            },
        },
        "13": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
                "model": ["11", 0],
                "positive": ["6", 0],
                "negative": ["25", 0],
                "latent_image": ["27", 0],
            },
        },
        "25": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "",
                "clip": ["11", 1],
            },
        },
        "27": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1,
            },
        },
    }


def _wan_t2v_workflow(
    prompt: str,
    width: int = 480,
    height: int = 320,
    num_frames: int = 17,
    steps: int = 15,
    seed: int | None = None,
) -> dict:
    """Build a Wan2.x text-to-video workflow for ComfyUI API.

    Uses WanVideoWrapper nodes (Kijai). Verified on 5060 Ti 16 GB.
    Node specs queried from ComfyUI /object_info endpoint.
    """
    if seed is None:
        seed = int(time.time()) % (2**31)

    return {
        # Load Wan2.x unet model
        "1": {
            "class_type": "WanVideoModelLoader",
            "inputs": {
                "model": WAN_UNET_HIGH,
                "base_precision": "bf16",
                "quantization": "disabled",
                "load_device": "offload_device",
            },
        },
        # Load VAE
        "2": {
            "class_type": "WanVideoVAELoader",
            "inputs": {
                "model_name": WAN_VAE,
                "precision": "bf16",
            },
        },
        # Encode text prompt (non-scaled FP8 encoder)
        "3": {
            "class_type": "WanVideoTextEncodeCached",
            "inputs": {
                "model_name": WAN_CLIP,
                "precision": "bf16",
                "positive_prompt": prompt,
                "negative_prompt": "",
                "quantization": "fp8_e4m3fn",
                "use_disk_cache": True,
                "device": "gpu",
            },
        },
        # Empty image embeds (required for T2V mode)
        "4": {
            "class_type": "WanVideoEmptyEmbeds",
            "inputs": {
                "width": width,
                "height": height,
                "num_frames": num_frames,
            },
        },
        # Sampler
        "5": {
            "class_type": "WanVideoSampler",
            "inputs": {
                "shift": 5.0,
                "steps": steps,
                "cfg": 1.0,
                "seed": seed,
                "scheduler": "unipc",
                "force_offload": True,
                "riflex_freq_index": 0,
                "model": ["1", 0],
                "text_embeds": ["3", 0],
                "image_embeds": ["4", 0],
            },
        },
        # Decode latents to video frames
        "6": {
            "class_type": "WanVideoDecode",
            "inputs": {
                "enable_vae_tiling": True,
                "tile_x": max(width, 272),
                "tile_y": max(height, 272),
                "tile_stride_x": max(width // 2, 144),
                "tile_stride_y": max(height // 2, 128),
                "samples": ["5", 0],
                "vae": ["2", 0],
            },
        },
        # Save as animated WEBP
        "7": {
            "class_type": "SaveAnimatedWEBP",
            "inputs": {
                "filename_prefix": "athanor_video",
                "fps": 16.0,
                "lossless": False,
                "quality": 85,
                "method": "default",
                "images": ["6", 0],
            },
        },
    }


@tool
def generate_video(prompt: str, width: int = 480, height: int = 320, num_frames: int = 17, steps: int = 15) -> str:
    """Generate a short video clip using Wan2.x on ComfyUI. Returns the prompt ID for tracking.

    Args:
        prompt: Text description of the video to generate. Be specific about motion and action.
        width: Video width in pixels (default 480). Must be divisible by 16.
        height: Video height in pixels (default 320). Must be divisible by 16.
        num_frames: Number of frames (default 17). More frames = longer video but more VRAM.
        steps: Number of sampling steps (default 15). More steps = better quality but slower.

    Constraints:
        - Runs on 5060 Ti (16 GB VRAM). 480x320 @ 17 frames uses ~14 GB peak.
        - Higher resolutions need more VRAM. Don't exceed 640x480 @ 17 frames on this GPU.
        - Generation takes ~90s at default settings.

    Example prompts:
        "A cat walking across a sunlit garden, camera tracking shot, cinematic"
        "Ocean waves crashing on rocky shore at golden hour, slow motion, 4K quality"
    """
    try:
        # Round to nearest 16 (Wan2.x requirement)
        width = (width // 16) * 16
        height = (height // 16) * 16

        workflow = _wan_t2v_workflow(prompt, width, height, num_frames, steps)
        client_id = str(uuid.uuid4())

        resp = httpx.post(
            f"{COMFYUI_URL}/prompt",
            json={"prompt": workflow, "client_id": client_id},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        prompt_id = data.get("prompt_id", "unknown")
        number = data.get("number", "?")
        est_time = int(steps * num_frames * 0.35)  # rough estimate

        return (
            f"Video generation queued successfully.\n"
            f"Prompt ID: {prompt_id}\n"
            f"Queue position: {number}\n"
            f"Settings: {width}x{height}, {num_frames} frames, {steps} steps, Wan2.x T2V FP8\n"
            f"Estimated time: ~{est_time}s\n"
            f"Use check_queue to monitor progress."
        )
    except httpx.HTTPStatusError as e:
        error_body = e.response.text[:500] if e.response else "No response"
        return f"ComfyUI rejected the video generation request: {e.response.status_code}\n{error_body}"
    except Exception as e:
        return f"Failed to queue video generation: {e}"


@tool
def generate_image(prompt: str, width: int = 1024, height: int = 1024, steps: int = 20) -> str:
    """Generate an image using Flux on ComfyUI. Returns the prompt ID for tracking.

    Args:
        prompt: Text description of the image to generate.
        width: Image width in pixels (default 1024). Must be divisible by 8.
        height: Image height in pixels (default 1024). Must be divisible by 8.
        steps: Number of sampling steps (default 20). More steps = better quality but slower.

    Example prompts:
        "A dark gothic castle at sunset, dramatic lighting, oil painting style"
        "Portrait of a cyberpunk woman with neon tattoos, photorealistic"
    """
    try:
        # Round to nearest 8
        width = (width // 8) * 8
        height = (height // 8) * 8

        workflow = _flux_workflow(prompt, width, height, steps)
        client_id = str(uuid.uuid4())

        resp = httpx.post(
            f"{COMFYUI_URL}/prompt",
            json={"prompt": workflow, "client_id": client_id},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        prompt_id = data.get("prompt_id", "unknown")
        number = data.get("number", "?")

        return (
            f"Image generation queued successfully.\n"
            f"Prompt ID: {prompt_id}\n"
            f"Queue position: {number}\n"
            f"Settings: {width}x{height}, {steps} steps, Flux dev FP8\n"
            f"Use check_queue to monitor progress."
        )
    except httpx.HTTPStatusError as e:
        error_body = e.response.text[:500] if e.response else "No response"
        return f"ComfyUI rejected the generation request: {e.response.status_code}\n{error_body}"
    except Exception as e:
        return f"Failed to queue generation: {e}"


@tool
def check_queue() -> str:
    """Check the current ComfyUI generation queue. Shows running and pending jobs."""
    try:
        resp = httpx.get(f"{COMFYUI_URL}/queue", timeout=10)
        resp.raise_for_status()
        data = resp.json()

        running = data.get("queue_running", [])
        pending = data.get("queue_pending", [])

        lines = [f"Running: {len(running)}, Pending: {len(pending)}"]

        for job in running:
            if len(job) >= 3:
                prompt_id = job[1] if isinstance(job[1], str) else "?"
                lines.append(f"  Running: {prompt_id}")

        for job in pending:
            if len(job) >= 3:
                prompt_id = job[1] if isinstance(job[1], str) else "?"
                lines.append(f"  Pending: {prompt_id}")

        if not running and not pending:
            lines.append("Queue is empty — ComfyUI is idle.")

        return "\n".join(lines)
    except Exception as e:
        return f"Failed to check queue: {e}"


@tool
def get_generation_history(limit: int = 5) -> str:
    """Get recent ComfyUI generation history. Shows completed jobs with filenames and prompts.

    Args:
        limit: Number of recent generations to show (default 5).
    """
    try:
        resp = httpx.get(f"{COMFYUI_URL}/history", timeout=10)
        resp.raise_for_status()
        history = resp.json()

        if not history:
            return "No generation history available."

        # History is a dict of prompt_id -> data
        items = sorted(history.items(), key=lambda x: x[1].get("_timestamp", 0) if isinstance(x[1], dict) else 0, reverse=True)[:limit]

        lines = [f"Last {min(limit, len(items))} generations:"]

        for prompt_id, data in items:
            if not isinstance(data, dict):
                continue
            outputs = data.get("outputs", {})
            status = data.get("status", {})
            completed = status.get("completed", False)

            # Find image outputs
            images = []
            for node_id, node_output in outputs.items():
                for img in node_output.get("images", []):
                    images.append(img.get("filename", "unknown"))

            # Find the prompt text from the workflow
            prompt_text = "Unknown"
            prompt_data = data.get("prompt", [])
            if len(prompt_data) >= 3 and isinstance(prompt_data[2], dict):
                workflow = prompt_data[2]
                for node in workflow.values():
                    if isinstance(node, dict) and node.get("class_type") == "CLIPTextEncode":
                        text = node.get("inputs", {}).get("text", "")
                        if text:  # Skip empty negative prompts
                            prompt_text = text[:80]
                            break

            status_str = "Done" if completed else "In Progress"
            lines.append(f"\n[{prompt_id[:8]}] {status_str}")
            lines.append(f"  Prompt: {prompt_text}")
            if images:
                lines.append(f"  Output: {', '.join(images)}")

        return "\n".join(lines)
    except Exception as e:
        return f"Failed to get history: {e}"


@tool
def get_comfyui_status() -> str:
    """Check ComfyUI system status — GPU info, memory usage, version."""
    try:
        resp = httpx.get(f"{COMFYUI_URL}/system_stats", timeout=10)
        resp.raise_for_status()
        data = resp.json()

        system = data.get("system", {})
        devices = data.get("devices", [])

        lines = [
            f"ComfyUI v{system.get('comfyui_version', '?')}",
            f"Python {system.get('python_version', '?').split()[0]}",
            f"PyTorch {system.get('pytorch_version', '?')}",
            f"System RAM: {system.get('ram_free', 0) / (1024**3):.1f} / {system.get('ram_total', 0) / (1024**3):.1f} GB free",
        ]

        for dev in devices:
            vram_total = dev.get("vram_total", 0) / (1024**3)
            vram_free = dev.get("vram_free", 0) / (1024**3)
            lines.append(f"GPU: {dev.get('name', 'Unknown')} — {vram_free:.1f} / {vram_total:.1f} GB VRAM free")

        return "\n".join(lines)
    except Exception as e:
        return f"ComfyUI unreachable: {e}"


# --- EoBQ Character Portrait Generation ---

# Per-queen Flux prompts from queens.ts — photorealistic baseline, prime-era accurate.
# PuLID face injection adds the actual performer's face on top of these body/scene prompts.
EOQB_CHARACTERS = {
    # --- Act 1 Fantasy Characters (dark-court narrative overlay) ---
    "isolde": "hyperreal 4K cinematic athletic Nordic woman 5'10\" 34DD high-set implants subsurface glow, hazel almond eyes longing, porcelain freckled skin, Arri Alexa color, volumetric office lighting.",
    "seraphine": "hyperreal 4K ethereal fragile woman silver-white hair violet eyes, tattered white robes, magical sigils on skin, dark circles, Arri Alexa color, moonlit chamber lighting.",
    "valeria": "hyperreal 4K muscular woman sun-bronzed skin close-cropped dark hair grey streak, amber eyes hawkish nose, battle scars, battered steel armor, Arri Alexa color, battlefield lighting.",
    "lilith": "hyperreal 4K strikingly beautiful woman long black hair blood-red lips, dark eyes gold flecks, crimson liquid dress, pale luminescent skin, Arri Alexa color, candlelit chamber lighting.",
    "mireille": "hyperreal 4K petite fox-like woman copper-red curls freckled skin, bright green eyes, dark leather outfit, multiple rings thin dagger, Arri Alexa color, tavern firelight.",
    # --- The 21 Council Queens (full Physical Prime Blueprints from master doc) ---
    "emilie-ekstrom": "hyperreal 4K cinematic athletic Nordic woman 5'10\" 130-139lbs 33-25-35.5 34DD high-set silicone teardrop implants pale pink dime-sized areolas upturned nipples subsurface glow, hazel-brown almond-shaped eyes with epicanthic fold, chestnut brown long straight hair to mid-back, porcelain fair skin subtle summer freckles on shoulders and nose, lithe athletic-slim body 32 inch inseam toned legs etched abs under soft layer subtle pear sway, high cheekbones soft jaw natural bow lips, elegant posture youthful firmness, Arri Alexa color, volumetric office lighting.",
    "jordan-night": "hyperreal 4K voluptuous tattooed woman 5'8\" 130lbs 34-26-39 34H heavy rounded silicone implants pronounced underboob crease, piercing ice blue eyes smirking, jet black long straight hair to mid-back, pale olive flawless skin, full floral sleeve left arm roses thorns throat script Nachtblume clit and navel piercings, voluptuous hourglass thick thighs soft belly, heart-shaped face full smirky lips, tattoo ripple on arch, Arri Alexa color, neon club lighting.",
    "alanah-rae": "hyperreal 4K athletic hourglass woman 5'7\" 130lbs 34F-24-36 34F perfect bolt-on round implants B to DD upgrade 2010 perfect shine, blue eyes, platinum long waves hair, golden California tan skin, athletic hourglass tight waist, sharp jaw full pouty lips, 2010-era perfection bolt-on shine, Arri Alexa color, mirror room lighting.",
    "nikki-benz": "hyperreal 4K athletic woman 5'5\" 121lbs 34E-24-36 34E enhanced silicone 500cc to 700cc implants, blue eyes royal glare, blonde long waves hair, golden tan skin, athletic body strong thighs, diamond high cheekbones, royal posture, Arri Alexa color, throne lighting.",
    "chloe-lamour": "hyperreal 4K curvy French woman 5'6\" 154lbs 36DD-25-39 36DD fake implants pronounced underboob natural jiggle, brown warm eyes, dark brunette long hair to waist, tanned olive glow skin, throat tattoo freedom iron beach forearm tattoos anicka mamka torso fish motif, curvy French hourglass soft belly flared hips, oval face full lips, throat tattoo flexes on gag, Arri Alexa color, medical lighting.",
    "nicolette-shea": "hyperreal 4K amazonian woman 5'11\" 140lbs 36E-26-38 36E high-profile silicone implants, blue eyes, blonde long hair, golden tan long legs, athletic runway body endless legs, sharp bone structure, Arri Alexa color, helipad lighting.",
    "peta-jensen": "hyperreal 4K athletic Nordic woman 5'7\" 125lbs 34F-24-35 34F silicone teardrop implants pale areolas, ice blue eyes, auburn red long waves hair, pale Nordic skin, athletic toned body, classic bone structure full lips, Arri Alexa color, fjord lighting.",
    "sandee-westgate": "hyperreal 4K exotic hourglass woman 5'7\" 120lbs 34DD-24-35 34DD silicone implants, dark brown almond-shaped eyes, dark brown long straight hair, olive tan skin, exotic hourglass toned curves, oval face sculpted features, lower back tattoo, Arri Alexa color, island lighting.",
    "marisol-yotta": "hyperreal 4K thick Latina woman 5'5\" 160lbs 34H-28-42 34H Colombian silicone implants, brown eyes, dark brunette long waves, golden tan skin, thick hourglass exaggerated hips extreme curves, round face full lips, Arri Alexa color, cam room lighting.",
    "trina-michaels": "hyperreal 4K voluptuous woman 5'5\" 145lbs 36G-26-38 36G enhanced heavy silicone implants heavy sway, brown eyes, blonde long hair, tan skin, voluptuous soft curves full figure, round cheeks full face, Arri Alexa color, casino lighting.",
    "nikki-sexx": "hyperreal 4K athletic woman 5'5\" 118lbs 34F-23-34 34F legendary silicone implants, blue eyes intense, dark brunette hair, tan skin, athletic toned body, sharp features, Arri Alexa color, casino lighting.",
    "madison-ivy": "hyperreal 4K tiny woman 4'11\" 105lbs 32F-22-32 32F massive silicone implants insane body to implant ratio contrast on extremely petite frame, green piercing eyes, brunette pixie-cut sharp features, porcelain skin, tiny petite frame, Arri Alexa color, vegas lighting.",
    "amy-anderssen": "hyperreal 4K extreme plastic woman 5'6\" 165lbs 40HH-28-38 40HH overfilled silicone implants massive spherical, dark eyes, brunette hair, olive skin, extreme curves cartoon proportions, angular face, Arri Alexa color, monster showcase lighting.",
    "puma-swede": "hyperreal 4K towering Amazon woman 6'1\" 140lbs 32F-24-36 32F silicone implants on tall athletic frame, ice blue eyes dominant, blonde short pixie, pale Nordic skin, tall athletic body endless legs strong jaw, Arri Alexa color, tall dramatic lighting.",
    "ava-addams": "hyperreal 4K MILF hourglass woman 5'3\" 125lbs 32G-24-36 32G silicone implants, brown eyes warm, dark brunette long waves, olive skin warm glow, MILF hourglass soft voluptuous curves, soft full face high cheekbones, Arri Alexa color, vault lighting.",
    "brooklyn-chase": "hyperreal 4K curvy girl-next-door woman 5'2\" 120lbs 32G-25-36 32G silicone implants, hazel eyes innocent, brunette long waves, tan skin, curvy sweet soft curves, girl-next-door face, small lower back tattoo, Arri Alexa color, sweet bedroom lighting.",
    "esperanza-gomez": "hyperreal 4K Latina hourglass woman 5'7\" 130lbs 34DD-24-38 34DD Colombian silicone implants, brown eyes seductive, dark brunette long waves, golden tan skin, ultimate Latina hourglass full curves, sharp Latina features, Arri Alexa color, Latin villa lighting.",
    "savannah-bond": "hyperreal 4K modern bimbo woman 5'4\" 125lbs 34G-24-36 34G silicone implants recent upgrade, blue eyes glazed bimbo, blonde long waves, golden Australian tan skin, bimbo curves enhanced proportions, soft pretty face, Arri Alexa color, Aussie beach house lighting.",
    "shyla-stylez": "hyperreal 4K perfect 2008 plastic woman 5'3\" 115lbs 36DD-23-34 36DD bolt-on silicone implants perfect original, blue eyes, brunette long hair, tan skin, 2008-era perfect plastic body, angelic face, bolt-on perfection original shine, Arri Alexa color, studio original lighting.",
    "brianna-banks": "hyperreal 4K golden era glamour woman 5'7\" 120lbs 34DD-24-35 34DD enhanced silicone implants, blue-green eyes classic, blonde long waves, tanned skin, athletic golden era curves, high cheekbones classic bone structure, Arri Alexa color, golden hour lighting.",
    "clanddi-jinkcebo": "hyperreal 4K extreme European curves woman 5'7\" 150lbs 34H+-26-40 34H plus enhanced silicone implants, brown eyes turning filthy, dark brunette long hair, olive-pale skin, extreme European curves enhanced proportions, heart-shaped face, Arri Alexa color, fetish dungeon lighting.",
}


def _fetch_dynamic_character_desc(name: str) -> str | None:
    """Try to fetch character visual description from Qdrant (eoq_characters collection).

    Returns None if not found or on error, allowing fallback to static dict.
    """
    try:
        qdrant_url = registry.qdrant.base_url
        resp = httpx.post(
            f"{qdrant_url}/collections/eoq_characters/points/scroll",
            json={
                "filter": {"must": [{"key": "character_id", "match": {"value": name}}]},
                "limit": 1,
                "with_payload": True,
            },
            timeout=5,
        )
        if resp.status_code == 200:
            points = resp.json().get("result", {}).get("points", [])
            if points:
                payload = points[0].get("payload", {})
                desc = payload.get("visual_description") or payload.get("flux_prompt")
                if desc and len(desc) > 20:
                    return desc
    except Exception:
        pass
    return None


@tool
def generate_character_portrait(character_name: str, scene_context: str = "", style: str = "cinematic") -> str:
    """Generate an EoBQ character portrait using Flux on ComfyUI.

    Args:
        character_name: Character name (Act 1: isolde, seraphine, etc. Queens: emilie-ekstrom, jordan-night, etc.)
        scene_context: Optional scene or mood context (e.g., "throne room at night", "after battle")
        style: Visual style — 'cinematic', 'painting', 'illustration' (default: cinematic)

    Checks Qdrant for dynamic character descriptions first, falls back to static dict.
    """
    name = character_name.lower().strip()

    # Try dynamic lookup first (Qdrant), then fall back to static dict
    base_desc = _fetch_dynamic_character_desc(name) or EOQB_CHARACTERS.get(name)
    if not base_desc:
        available = ", ".join(EOQB_CHARACTERS.keys())
        return f"Unknown character '{character_name}'. Available: {available}"

    style_suffix = {
        "cinematic": "Cinematic portrait, dramatic side lighting, dark fantasy, 8k, photorealistic, shallow depth of field, film grain.",
        "painting": "Oil painting style, dramatic chiaroscuro lighting, dark fantasy, rich textures, museum quality, painterly strokes.",
        "illustration": "High detail fantasy illustration, dark atmospheric, concept art, detailed linework, rich colors.",
    }.get(style, "Cinematic portrait, dramatic side lighting, dark fantasy, 8k, photorealistic.")

    prompt = f"{base_desc} {scene_context + '. ' if scene_context else ''}{style_suffix}"

    # Use portrait aspect ratio (832x1216)
    try:
        workflow = _flux_workflow(prompt, width=832, height=1216, steps=25)
        client_id = str(uuid.uuid4())

        resp = httpx.post(
            f"{COMFYUI_URL}/prompt",
            json={"prompt": workflow, "client_id": client_id},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        prompt_id = data.get("prompt_id", "unknown")
        return (
            f"Portrait of {character_name.title()} queued.\n"
            f"Prompt ID: {prompt_id}\n"
            f"Style: {style}, 832x1216, 25 steps\n"
            f"Prompt: {prompt[:120]}...\n"
            f"Use check_queue to monitor."
        )
    except Exception as e:
        return f"Failed to queue portrait: {e}"


@tool
def list_personas() -> str:
    """List all reference personas available for face-injection (PuLID) generation.

    Returns personas in two categories:
    - queens: adult performer likenesses for EoBQ characters
    - custom: personal reference photos (Shaun's own creations)

    Use a persona's name with generate_with_likeness to create images with that face.
    """
    try:
        resp = httpx.get(f"{EOQ_URL}/api/references", timeout=10)
        resp.raise_for_status()
        personas = resp.json()

        if not personas:
            return f"No personas yet. Upload reference photos at {EOQ_URL}/references"

        queens = [p for p in personas if p.get("category") == "queens"]
        custom = [p for p in personas if p.get("category") == "custom"]

        lines = [f"Reference personas ({len(personas)} total):"]
        if queens:
            lines.append("\nQueens:")
            for p in queens:
                n = len(p.get("photos", []))
                lines.append(f"  {p['name']} — {n} photo{'s' if n != 1 else ''}")
        if custom:
            lines.append("\nCustom:")
            for p in custom:
                n = len(p.get("photos", []))
                lines.append(f"  {p['name']} — {n} photo{'s' if n != 1 else ''}")

        return "\n".join(lines)
    except Exception as e:
        return f"Failed to list personas: {e}"


@tool
def generate_with_likeness(prompt: str, persona_name: str, width: int = 832, height: int = 1216, steps: int = 25) -> str:
    """Generate an image using a reference persona's face (PuLID face injection + flux-uncensored LoRA).

    The face from the persona's reference photo is injected into the generated image via PuLID.
    All generations use the flux-uncensored LoRA — no content restrictions.

    Args:
        prompt: Detailed image description. Be specific about pose, setting, lighting, style.
        persona_name: Name of the persona to use (from list_personas). Case-insensitive fuzzy match.
        width: Image width in pixels (default 832, portrait-friendly). Divisible by 8.
        height: Image height in pixels (default 1216, portrait). Divisible by 8.
        steps: Sampling steps (default 25 for quality).

    Example:
        generate_with_likeness("cinematic portrait, dark throne room, ornate gold armor, dramatic lighting, photorealistic 8k", "Isolde Reference")
    """
    try:
        # Fetch persona list
        resp = httpx.get(f"{EOQ_URL}/api/references", timeout=10)
        resp.raise_for_status()
        personas = resp.json()

        # Fuzzy-match by name
        name_lower = persona_name.lower().strip()
        persona = next(
            (p for p in personas if p["name"].lower() == name_lower),
            next((p for p in personas if name_lower in p["name"].lower()), None)
        )

        if not persona:
            available = ", ".join(p["name"] for p in personas) or "none"
            return f"Persona '{persona_name}' not found. Available: {available}"

        if not persona.get("photos"):
            return f"Persona '{persona['name']}' has no reference photos. Upload some at {EOQ_URL}/references"

        # Reference path inside EoBQ container's /references volume
        reference_path = f"/references/{persona['folder']}/{persona['photos'][0]}"

        # Call EoBQ generate API — handles ComfyUI upload + PuLID workflow
        gen_resp = httpx.post(
            f"{EOQ_URL}/api/generate",
            json={
                "type": "pulid",
                "prompt": prompt,
                "referencePath": reference_path,
            },
            timeout=180,  # PuLID loads heavy models, allow generous time
        )
        gen_resp.raise_for_status()
        data = gen_resp.json()

        image_url = data.get("imageUrl")
        prompt_id = data.get("promptId", "?")

        if image_url:
            return (
                f"Generated with likeness of {persona['name']}.\n"
                f"Prompt ID: {prompt_id}\n"
                f"Image URL: {image_url}\n"
                f"View at: {EOQ_URL}/gallery"
            )
        return f"Generation queued (prompt_id={prompt_id}) but polling timed out. Check ComfyUI at {COMFYUI_URL}"

    except httpx.TimeoutException:
        return f"Generation timed out. PuLID models may still be loading - check {COMFYUI_URL}"
    except Exception as e:
        return f"Failed to generate with likeness: {e}"


@tool
def generate_image_batch(prompt: str, count: int = 4, width: int = 1024, height: int = 1024, steps: int = 20) -> str:
    """Generate multiple image variants from the same prompt with different seeds.

    Use this for A/B comparisons, style exploration, or picking the best result
    from several generations.

    Args:
        prompt: Text description of the image to generate
        count: Number of variants to generate (1-8, default 4)
        width: Image width in pixels (default 1024). Divisible by 8.
        height: Image height in pixels (default 1024). Divisible by 8.
        steps: Sampling steps per image (default 20)
    """
    if count < 1 or count > 8:
        return "Count must be between 1 and 8."

    width = (width // 8) * 8
    height = (height // 8) * 8

    results = []
    base_seed = int(time.time()) % (2**31)

    for i in range(count):
        try:
            seed = base_seed + i
            workflow = _flux_workflow(prompt, width, height, steps, seed=seed)
            client_id = str(uuid.uuid4())

            resp = httpx.post(
                f"{COMFYUI_URL}/prompt",
                json={"prompt": workflow, "client_id": client_id},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            results.append(f"  [{i+1}] Prompt ID: {data.get('prompt_id', '?')} (seed: {seed})")
        except Exception as e:
            results.append(f"  [{i+1}] Failed: {e}")

    queued = sum(1 for r in results if "Prompt ID:" in r)
    return (
        f"Batch generation: {queued}/{count} queued\n"
        f"Settings: {width}x{height}, {steps} steps, Flux dev FP8\n"
        f"Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}\n\n"
        + "\n".join(results)
        + "\n\nUse check_queue to monitor progress."
    )


@tool
def generate_i2v_video(anchor_url: str, motion_prompt: str, quality: str = "quick") -> str:
    """Generate an I2V (image-to-video) clip from a portrait/anchor image via EoBQ + ComfyUI.

    Animates a static image into a short video using Wan2.2 I2V pipeline.
    Calls the EoBQ /api/generate endpoint which handles image upload and workflow building.

    Args:
        anchor_url: URL or filesystem path to the anchor/first-frame image.
        motion_prompt: Description of the motion to add (e.g., "subtle breathing, cold stare at viewer").
        quality: "quick" (6 steps, 480p, ~30s) or "production" (25 steps, 832x480, ~120s). Default: quick.

    Returns: prompt_id for tracking, or error message.
    """
    try:
        full_prompt = f"{motion_prompt}, cinematic, photorealistic, 8k"
        resp = httpx.post(
            f"{EOQ_URL}/api/generate",
            json={
                "type": "i2v",
                "prompt": full_prompt,
                "referencePath": anchor_url,
                "quality": quality,
                "negativePrompt": "blurry, distorted face, morphing, identity change, static image, watermark, text, cartoon",
            },
            timeout=600,  # I2V can take 5-10 min for production quality
        )
        resp.raise_for_status()
        data = resp.json()

        video_url = data.get("imageUrl")
        prompt_id = data.get("promptId", "unknown")

        if video_url:
            return (
                f"I2V video generated successfully.\n"
                f"Prompt ID: {prompt_id}\n"
                f"Video URL: {video_url}\n"
                f"Quality: {quality}\n"
                f"Motion: {motion_prompt[:100]}"
            )
        return f"I2V generation queued (prompt_id={prompt_id}) but result not yet available. Poll with poll_video_completion."

    except httpx.TimeoutException:
        return "I2V generation timed out. The job may still be running in ComfyUI — use poll_video_completion."
    except Exception as e:
        return f"Failed to generate I2V video: {e}"


@tool
def poll_video_completion(prompt_id: str, timeout_s: int = 300) -> str:
    """Poll ComfyUI for a specific generation job until it completes or times out.

    Unlike check_queue (which shows queue state), this blocks until a specific
    prompt_id finishes and returns the output URL.

    Args:
        prompt_id: The ComfyUI prompt ID to wait for.
        timeout_s: Maximum seconds to wait (default 300 = 5 min).

    Returns: Video/image URL if completed, or status message.
    """
    start = time.time()
    poll_interval = 3  # seconds between checks

    while time.time() - start < timeout_s:
        try:
            resp = httpx.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                result = data.get(prompt_id)
                if result and result.get("outputs"):
                    # Check for error
                    if result.get("status", {}).get("status_str") == "error":
                        return f"Generation {prompt_id} failed with error."

                    # Find output files
                    for node_output in result["outputs"].values():
                        for key in ("videos", "images", "gifs"):
                            files = node_output.get(key, [])
                            if files:
                                f = files[0]
                                url = f"{COMFYUI_URL}/view?filename={f['filename']}&subfolder={f.get('subfolder', '')}&type={f.get('type', 'output')}"
                                elapsed = int(time.time() - start)
                                return f"Completed in {elapsed}s.\nURL: {url}\nFilename: {f['filename']}"
        except Exception:
            pass

        time.sleep(poll_interval)

    return f"Timed out after {timeout_s}s waiting for {prompt_id}. Job may still be running."


@tool
def check_video_inventory(queen_id: str = "") -> str:
    """Check which EoBQ queens/stages have pre-generated I2V videos.

    Reads Redis athanor:eoq:video_inventory keys. If queen_id is provided,
    shows stages for that queen. Otherwise shows a summary of all queens.

    Args:
        queen_id: Optional queen ID to check (e.g., "isolde", "jordan-night"). If empty, shows all.
    """
    try:
        import redis
        r = redis.Redis(host="192.168.1.203", port=6379, db=0)

        if queen_id:
            stages = ["defiant", "struggling", "conflicted", "yielding", "surrendered", "broken"]
            lines = [f"Video inventory for '{queen_id}':"]
            for stage in stages:
                key = f"athanor:eoq:video_inventory:{queen_id}:{stage}"
                data = r.get(key)
                if data:
                    info = json.loads(data)
                    lines.append(f"  {stage}: {info.get('quality', '?')} — {info.get('video_url', 'unknown')[:80]}")
                else:
                    lines.append(f"  {stage}: MISSING")
            return "\n".join(lines)

        # Summary mode: scan all inventory keys
        cursor = 0
        inventory = {}
        while True:
            cursor, keys = r.scan(cursor, match="athanor:eoq:video_inventory:*", count=100)
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                parts = key_str.split(":")
                if len(parts) >= 5:
                    qid = parts[3]
                    stage = parts[4]
                    inventory.setdefault(qid, []).append(stage)
            if cursor == 0:
                break

        if not inventory:
            return "No video inventory found. No queens have pre-generated I2V videos yet."

        lines = [f"Video inventory ({len(inventory)} queens):"]
        for qid in sorted(inventory.keys()):
            stages = sorted(inventory[qid])
            lines.append(f"  {qid}: {len(stages)}/6 stages — {', '.join(stages)}")

        total_videos = sum(len(s) for s in inventory.values())
        lines.append(f"\nTotal: {total_videos} videos across {len(inventory)} queens")
        return "\n".join(lines)

    except Exception as e:
        return f"Failed to check video inventory: {e}"


@tool
def update_video_inventory(queen_id: str, stage: str, video_url: str, quality: str = "quick") -> str:
    """Record a generated video in the EoBQ inventory (Redis).

    Call this after a successful I2V generation to track which queens/stages have videos.

    Args:
        queen_id: Queen ID (e.g., "isolde", "jordan-night").
        stage: Breaking stage ("defiant", "struggling", "conflicted", "yielding", "surrendered", "broken").
        video_url: URL of the generated video.
        quality: Quality level — "quick" or "production".
    """
    valid_stages = {"defiant", "struggling", "conflicted", "yielding", "surrendered", "broken"}
    if stage not in valid_stages:
        return f"Invalid stage '{stage}'. Must be one of: {', '.join(sorted(valid_stages))}"

    try:
        import redis
        r = redis.Redis(host="192.168.1.203", port=6379, db=0)

        inv_key = f"athanor:eoq:video_inventory:{queen_id}:{stage}"
        quality_key = f"athanor:eoq:video_quality:{queen_id}:{stage}"

        entry = json.dumps({
            "queen_id": queen_id,
            "stage": stage,
            "video_url": video_url,
            "quality": quality,
            "generated_at": time.time(),
        })

        r.set(inv_key, entry)

        # Also set a quality entry (default score based on quality level)
        score = 0.8 if quality == "production" else 0.5
        quality_entry = json.dumps({
            "queen_id": queen_id,
            "stage": stage,
            "score": score,
            "quality": quality,
            "evaluated_at": time.time(),
        })
        r.set(quality_key, quality_entry)

        return f"Inventory updated: {queen_id}/{stage} = {quality} (score={score})"

    except Exception as e:
        return f"Failed to update inventory: {e}"


@tool
def evaluate_video_quality(video_url: str, anchor_url: str = "") -> str:
    """Evaluate video quality using cloud vision model when available, file-size heuristic as fallback.

    When anchor_url is provided AND a vision model is available, calls Gemini Vision
    (via LiteLLM 'gemini' alias) to score face consistency, motion quality, artifacts,
    and prompt adherence. Falls back to file-size heuristic if vision call fails.

    Args:
        video_url: URL of the video to evaluate.
        anchor_url: URL of the original anchor image — enables vision-based face consistency scoring.

    Returns: JSON with score (0-1), reason, and component scores if vision-evaluated.
    """
    # Phase 1: Basic accessibility check
    try:
        resp = httpx.head(video_url, timeout=10, follow_redirects=True)
        if resp.status_code == 405:
            resp = httpx.get(video_url, timeout=10, follow_redirects=True, headers={"Range": "bytes=0-1024"})

        if resp.status_code not in (200, 206):
            return json.dumps({"score": 0.0, "reason": f"Video not accessible (HTTP {resp.status_code})"})

        content_length = resp.headers.get("content-length")
        size_bytes = int(content_length) if content_length else None
    except Exception as e:
        return json.dumps({"score": 0.0, "reason": f"Accessibility check failed: {e}"})

    # Phase 2: Cloud vision evaluation (when anchor is available)
    if anchor_url:
        vision_result = _try_vision_evaluation(video_url, anchor_url, size_bytes)
        if vision_result:
            return vision_result

    # Phase 3: File-size heuristic fallback
    if size_bytes is None:
        score, reason = 0.5, "Cannot determine file size — assumed moderate quality"
    elif size_bytes < 50_000:
        score, reason = 0.1, f"Very small file ({size_bytes} bytes) — likely corrupt or blank"
    elif size_bytes < 200_000:
        score, reason = 0.4, f"Small file ({size_bytes // 1024}KB) — may be low quality"
    elif size_bytes < 2_000_000:
        score, reason = 0.7, f"Reasonable size ({size_bytes // 1024}KB)"
    else:
        score, reason = 0.9, f"Good size ({size_bytes // (1024 * 1024)}MB) — likely production quality"

    return json.dumps({"score": score, "reason": reason, "size_bytes": size_bytes, "method": "heuristic"})


def _try_vision_evaluation(video_url: str, anchor_url: str, size_bytes: int | None) -> str | None:
    """Attempt cloud vision quality evaluation. Returns JSON string or None on failure."""
    try:
        from ..config import settings as _settings
        litellm_url = _settings.llm_base_url + "/chat/completions"
        litellm_key = _settings.llm_api_key

        prompt = (
            "You are evaluating a generated video frame against a reference anchor image. "
            "Score each dimension 0.0-1.0:\n"
            "1. face_consistency: Does the face match the anchor? Same person?\n"
            "2. motion_quality: Is the motion natural, not jerky or frozen?\n"
            "3. artifacts: Are there visual artifacts, distortion, or blurriness? (1.0 = clean)\n"
            "4. prompt_adherence: Does the output match what was requested?\n\n"
            "Respond with ONLY JSON: "
            '{"face_consistency": 0.8, "motion_quality": 0.7, "artifacts": 0.9, "prompt_adherence": 0.8, '
            '"composite": 0.8, "summary": "brief assessment"}'
        )

        resp = httpx.post(
            litellm_url,
            json={
                "model": "gemini",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": anchor_url}},
                            {"type": "image_url", "image_url": {"url": video_url}},
                        ],
                    }
                ],
                "max_tokens": 300,
                "temperature": 0.1,
            },
            headers={"Authorization": f"Bearer {litellm_key}"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Parse vision model response
        import re as _re
        clean = _re.sub(r"```(?:json)?\s*\n?", "", raw).replace("```", "").strip()
        scores = json.loads(clean)

        composite = scores.get("composite", 0)
        if not composite:
            vals = [scores.get(k, 0) for k in ("face_consistency", "motion_quality", "artifacts", "prompt_adherence")]
            composite = sum(vals) / max(len(vals), 1)

        return json.dumps({
            "score": round(composite, 2),
            "reason": scores.get("summary", "Vision-evaluated"),
            "method": "cloud_vision",
            "components": {
                "face_consistency": scores.get("face_consistency"),
                "motion_quality": scores.get("motion_quality"),
                "artifacts": scores.get("artifacts"),
                "prompt_adherence": scores.get("prompt_adherence"),
            },
            "size_bytes": size_bytes,
        })
    except Exception:
        return None  # Fall back to heuristic


CREATIVE_TOOLS = [
    generate_image, generate_image_batch, generate_video, generate_character_portrait,
    check_queue, get_generation_history, get_comfyui_status,
    list_personas, generate_with_likeness,
    generate_i2v_video, poll_video_completion,
    check_video_inventory, update_video_inventory, evaluate_video_quality,
]
