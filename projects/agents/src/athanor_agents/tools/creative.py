"""Creative tools — ComfyUI image/video generation, queue management, history."""

import time
import uuid

import httpx
from langchain_core.tools import tool

COMFYUI_URL = "http://192.168.1.225:8188"

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
                "clip": ["11", 0],
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
                "clip": ["11", 0],
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

# Character visual descriptions for consistent portrait generation
EOQB_CHARACTERS = {
    "isolde": "Regal woman in her 30s, sharp angular features, dark auburn hair in elaborate braids threaded with thin gold chains, pale porcelain skin, ice-blue eyes. Wears a fitted black and gold gown with high structured collar. A thin scar runs from her left ear to her jaw.",
    "seraphine": "Young woman with an ethereal, fragile beauty. Silver-white hair falling past her shoulders, violet eyes with an otherworldly glow. Wears tattered white and lavender robes. Faint magical sigils trace patterns on her skin. Dark circles under her eyes from sleepless visions.",
    "valeria": "Muscular woman in her late 20s, sun-bronzed skin, close-cropped dark hair with a streak of premature grey. Strong jaw, hawkish nose, amber eyes. Wears battered steel plate armor over chainmail. Multiple battle scars on her arms and face.",
    "lilith": "Strikingly beautiful woman with an unsettling edge. Long black hair, blood-red lips, dark eyes with flecks of gold. Wears a deep crimson dress that seems to shift between liquid and fabric. Pale skin with a faint luminescence.",
    "mireille": "Petite woman with sharp, fox-like features. Copper-red curls, freckled skin, bright green eyes that miss nothing. Wears practical dark leather with hidden pockets. Multiple rings and a thin dagger at her belt.",
}


@tool
def generate_character_portrait(character_name: str, scene_context: str = "", style: str = "cinematic") -> str:
    """Generate an EoBQ character portrait using Flux on ComfyUI.

    Args:
        character_name: Character name (isolde, seraphine, valeria, lilith, mireille)
        scene_context: Optional scene or mood context (e.g., "throne room at night", "after battle")
        style: Visual style — 'cinematic', 'painting', 'illustration' (default: cinematic)

    Uses stored visual descriptions for character consistency.
    """
    name = character_name.lower().strip()
    base_desc = EOQB_CHARACTERS.get(name)
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


EOQ_URL = "http://192.168.1.225:3002"


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
            return "No personas yet. Upload reference photos at http://192.168.1.225:3002/references"

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
            return f"Persona '{persona['name']}' has no reference photos. Upload some at http://192.168.1.225:3002/references"

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
                f"View at: http://192.168.1.225:3002/gallery"
            )
        return f"Generation queued (prompt_id={prompt_id}) but polling timed out. Check ComfyUI at http://192.168.1.225:8188"

    except httpx.TimeoutException:
        return "Generation timed out. PuLID models may still be loading — check http://192.168.1.225:8188"
    except Exception as e:
        return f"Failed to generate with likeness: {e}"


CREATIVE_TOOLS = [
    generate_image, generate_video, generate_character_portrait,
    check_queue, get_generation_history, get_comfyui_status,
    list_personas, generate_with_likeness,
]
