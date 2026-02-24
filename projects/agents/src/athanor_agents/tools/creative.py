"""Creative tools — ComfyUI image generation, queue management, history."""

import json
import time
import uuid

import httpx
from langchain_core.tools import tool

COMFYUI_URL = "http://192.168.1.225:8188"


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


CREATIVE_TOOLS = [generate_image, check_queue, get_generation_history, get_comfyui_status]
