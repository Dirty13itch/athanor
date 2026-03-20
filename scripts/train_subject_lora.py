#!/usr/bin/env python3
"""
train_subject_lora.py — LoRA training automation for the auto_gen pipeline.

Prepares training data (resize, caption) and generates training configs for
per-subject FLUX LoRA training on WORKSHOP (RTX 5090 32GB).

Usage:
    python train_subject_lora.py peta-jensen
    python train_subject_lora.py peta-jensen --resolution 512 --rank 32 --steps 1500
    python train_subject_lora.py peta-jensen --caption-only   # just regenerate captions
    python train_subject_lora.py peta-jensen --dry-run        # prep data, generate config, don't train
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster_config import LITELLM_KEY, NODES, get_url

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SUBJECTS_DIR = Path("/mnt/vault/data/gen-subjects")
PERFORMERS_DB = Path("/mnt/vault/data/performers.json")
LORA_OUTPUT_DIR = Path("/mnt/vault/models/comfyui/loras")
TRAINING_LOG = Path("/mnt/vault/data/gen-output/lora_training_log.json")
TRAINING_STAGING = Path("/mnt/vault/data/gen-output/lora_training")

# FLUX model paths (on WORKSHOP, accessible via NFS mount)
FLUX_MODEL_PATH = "/mnt/vault/models/comfyui/unet/flux1-dev-fp8.safetensors"
FLUX_VAE_PATH = "/mnt/vault/models/comfyui/vae/ae.safetensors"
FLUX_CLIP_L_PATH = "/mnt/vault/models/comfyui/clip/clip_l.safetensors"
FLUX_T5_PATH = "/mnt/vault/models/comfyui/clip/t5xxl_fp8_e4m3fn.safetensors"

# LiteLLM
LITELLM_URL = get_url("litellm")
LITELLM_KEY = "sk-athanor-litellm-2026"
LITELLM_MODEL = "creative"

# WORKSHOP SSH
WORKSHOP_SSH = f"athanor@{NODES['workshop']}"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("train_subject_lora")


# ---------------------------------------------------------------------------
# Performer DB lookup
# ---------------------------------------------------------------------------
def load_performer(slug: str) -> Optional[dict]:
    """Look up a performer by slug in performers.json."""
    if not PERFORMERS_DB.exists():
        log.warning("Performers DB not found at %s", PERFORMERS_DB)
        return None
    performers = json.loads(PERFORMERS_DB.read_text())
    # Try slug match first (name lowercased, spaces to hyphens)
    for p in performers:
        p_slug = p.get("name", "").lower().replace(" ", "-")
        if p_slug == slug:
            return p
    # Fallback: check aliases
    for p in performers:
        aliases = p.get("aliases", "")
        alias_slugs = [a.strip().lower().replace(" ", "-") for a in aliases.split(",")]
        if slug in alias_slugs:
            return p
    return None


# ---------------------------------------------------------------------------
# Image preparation
# ---------------------------------------------------------------------------
def prepare_images(
    slug: str,
    resolution: int,
    staging_dir: Path,
) -> list[Path]:
    """
    Copy and resize reference images to the training staging directory.
    Returns list of prepared image paths.
    """
    source_dir = SUBJECTS_DIR / slug
    if not source_dir.exists():
        log.error("Subject directory not found: %s", source_dir)
        sys.exit(1)

    image_dir = staging_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    # Collect source images
    extensions = {".jpg", ".jpeg", ".png", ".webp"}
    source_images = sorted(
        f for f in source_dir.iterdir()
        if f.suffix.lower() in extensions and f.is_file()
    )

    if not source_images:
        log.error("No images found in %s", source_dir)
        sys.exit(1)

    log.info("Found %d reference images in %s", len(source_images), source_dir)

    prepared = []
    for i, src in enumerate(source_images):
        dst = image_dir / f"{slug}_{i:03d}.png"

        img = Image.open(src).convert("RGB")

        # Center-crop to square, then resize
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))
        img = img.resize((resolution, resolution), Image.LANCZOS)

        img.save(dst, "PNG", quality=95)
        prepared.append(dst)
        log.info(
            "  [%d/%d] %s -> %s (%dx%d)",
            i + 1, len(source_images), src.name, dst.name, resolution, resolution,
        )

    return prepared


# ---------------------------------------------------------------------------
# Caption generation via LiteLLM
# ---------------------------------------------------------------------------
def generate_caption(image_path: Path, performer: Optional[dict], slug: str) -> str:
    """
    Generate a training caption for a single image using local LLM via LiteLLM.

    For LoRA training, captions should describe the subject with a trigger word
    and relevant physical details, but NOT be overly specific about pose/scene
    (the model should learn to generalize).
    """
    trigger_word = slug

    # Build performer context
    performer_desc = ""
    if performer:
        parts = []
        if performer.get("bust"):
            parts.append(f"bust: {performer['bust']}")
        if performer.get("body_type"):
            parts.append(f"body type: {performer['body_type']}")
        if performer.get("ethnicity"):
            parts.append(f"ethnicity: {performer['ethnicity']}")
        if performer.get("bust_to_frame"):
            parts.append(f"build: {performer['bust_to_frame']}")
        if parts:
            performer_desc = f"Known attributes: {', '.join(parts)}."

    prompt = (
        f'You are generating a training caption for a LoRA model of a person '
        f'with the trigger word "{trigger_word}".\n\n'
        f'Write a single caption line (no quotes, no prefix) describing the person in this photo.\n\n'
        f'Rules:\n'
        f'- Start with the trigger word "{trigger_word}"\n'
        f'- Describe hair color/style, approximate expression, what they are wearing (if visible)\n'
        f'- Keep it factual and concise (one sentence, 15-40 words)\n'
        f'- Do NOT describe background, lighting, or camera angle\n'
        f'- Do NOT use subjective language (beautiful, stunning, etc.)\n'
    )
    if performer_desc:
        prompt += f"- {performer_desc}\n"
    prompt += "\nCaption:"

    try:
        resp = httpx.post(
            f"{LITELLM_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={
                "model": LITELLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 100,
                "temperature": 0.3,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        caption = resp.json()["choices"][0]["message"]["content"].strip()
        # Clean up: remove quotes, "Caption:" prefix
        caption = caption.strip("\"'")
        for pfx in ["Caption:", "caption:"]:
            if caption.startswith(pfx):
                caption = caption[len(pfx):].strip()
        return caption
    except Exception as e:
        log.warning("LLM captioning failed for %s: %s — using fallback", image_path.name, e)
        name = performer["name"] if performer else slug.replace("-", " ").title()
        return f"{trigger_word}, photo of {name}, close up portrait"


def caption_images(
    image_paths: list[Path],
    performer: Optional[dict],
    slug: str,
) -> dict[str, str]:
    """Generate captions for all training images. Returns {filename: caption}."""
    captions = {}
    for i, img_path in enumerate(image_paths):
        caption = generate_caption(img_path, performer, slug)
        captions[img_path.name] = caption

        # Write caption file alongside image (standard kohya/ai-toolkit format)
        caption_path = img_path.with_suffix(".txt")
        caption_path.write_text(caption)

        log.info("  [%d/%d] %s: %s", i + 1, len(image_paths), img_path.name, caption)
        time.sleep(0.5)  # Be polite to LLM endpoint

    return captions


# ---------------------------------------------------------------------------
# Training config generation
# ---------------------------------------------------------------------------
def _write_yaml(data: dict, path: Path) -> None:
    """Minimal YAML writer — avoids pyyaml dependency."""
    lines: list[str] = []
    _yaml_dump(data, lines, indent=0)
    path.write_text("\n".join(lines) + "\n")


def _yaml_dump(obj, lines: list[str], indent: int) -> None:
    prefix = "  " * indent
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{prefix}{k}:")
                _yaml_dump(v, lines, indent + 1)
            elif isinstance(v, bool):
                lines.append(f"{prefix}{k}: {'true' if v else 'false'}")
            elif isinstance(v, str):
                needs_quote = any(c in v for c in ":{}[],&*#?|-<>=!%@\\") or v in (
                    "true", "false", "null", "",
                )
                if needs_quote:
                    lines.append(f'{prefix}{k}: "{v}"')
                else:
                    lines.append(f"{prefix}{k}: {v}")
            else:
                lines.append(f"{prefix}{k}: {v}")
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                keys = list(item.keys())
                first_key = keys[0]
                first_val = item[first_key]
                if isinstance(first_val, (dict, list)):
                    lines.append(f"{prefix}- {first_key}:")
                    _yaml_dump(first_val, lines, indent + 2)
                elif isinstance(first_val, str):
                    needs_q = any(c in first_val for c in ":{},[]&*#?|-<>=!%@\\")
                    if needs_q:
                        lines.append(f'{prefix}- {first_key}: "{first_val}"')
                    else:
                        lines.append(f"{prefix}- {first_key}: {first_val}")
                else:
                    lines.append(f"{prefix}- {first_key}: {first_val}")
                for k in keys[1:]:
                    _yaml_dump({k: item[k]}, lines, indent + 1)
            elif isinstance(item, str):
                lines.append(f'{prefix}- "{item}"')
            else:
                lines.append(f"{prefix}- {item}")


def generate_training_config(
    slug: str,
    staging_dir: Path,
    image_count: int,
    resolution: int,
    rank: int,
    learning_rate: float,
    steps: int,
    batch_size: int,
) -> Path:
    """
    Generate an ai-toolkit compatible YAML training config.
    Also generates a kohya_ss compatible TOML as a fallback option.
    """
    output_name = f"{slug}_lora"
    image_dir = staging_dir / "images"

    # Auto-calculate steps if not specified: ~150 steps per image, min 800, max 3000
    if steps <= 0:
        steps = max(800, min(3000, image_count * 150))
        log.info("Auto-calculated steps: %d (from %d images)", steps, image_count)

    # Save interval: every ~250 steps or 4 saves total
    save_every = max(250, steps // 4)

    # --- ai-toolkit config (YAML) ---
    aitk_config = {
        "job": "extension",
        "config": {
            "name": output_name,
            "process": [
                {
                    "type": "sd_trainer",
                    "training_folder": str(staging_dir / "output"),
                    "device": "cuda:0",
                    "trigger_word": slug,
                    "network": {
                        "type": "lora",
                        "linear": rank,
                        "linear_alpha": rank,
                    },
                    "save": {
                        "dtype": "float16",
                        "save_every": save_every,
                        "max_step_saves_to_keep": 3,
                    },
                    "datasets": [
                        {
                            "folder_path": str(image_dir),
                            "caption_ext": "txt",
                            "caption_dropout_rate": 0.05,
                            "resolution": resolution,
                            "default_caption": f"{slug}, portrait photo",
                            "shuffle_tokens": False,
                        }
                    ],
                    "train": {
                        "batch_size": batch_size,
                        "steps": steps,
                        "gradient_accumulation_steps": 1,
                        "train_unet": True,
                        "train_text_encoder": False,
                        "gradient_checkpointing": True,
                        "noise_scheduler": "flowmatch",
                        "optimizer": "adamw8bit",
                        "lr": learning_rate,
                        "ema_config": {
                            "use_ema": True,
                            "ema_decay": 0.99,
                        },
                        "dtype": "bf16",
                    },
                    "model": {
                        "name_or_path": FLUX_MODEL_PATH,
                        "is_flux": True,
                        "quantize": True,
                    },
                    "sample": {
                        "sampler": "flowmatch",
                        "sample_every": save_every,
                        "width": resolution,
                        "height": resolution,
                        "prompts": [
                            f"{slug}, close up portrait photo, looking at camera",
                            f"{slug}, half body photo, natural lighting",
                        ],
                        "neg": "",
                        "seed": 42,
                        "walk_seed": True,
                        "guidance_scale": 3.5,
                        "sample_steps": 28,
                    },
                }
            ],
        },
    }

    aitk_path = staging_dir / f"{output_name}_aitk.yaml"
    _write_yaml(aitk_config, aitk_path)
    log.info("Generated ai-toolkit config: %s", aitk_path)

    # --- kohya_ss config (TOML) ---
    warmup_steps = max(1, steps // 10)
    kohya_toml = (
        f"# kohya_ss LoRA training config for {slug}\n"
        f"# Generated {datetime.now(timezone.utc).isoformat()}\n\n"
        f"[model]\n"
        f'pretrained_model_name_or_path = "{FLUX_MODEL_PATH}"\n'
        f"v_parameterization = false\n"
        f"v_pred = false\n\n"
        f"[dataset]\n"
        f'train_data_dir = "{image_dir}"\n'
        f'resolution = "{resolution},{resolution}"\n'
        f'caption_extension = ".txt"\n'
        f"shuffle_caption = false\n"
        f"keep_tokens = 1\n"
        f"color_aug = false\n"
        f"flip_aug = false\n"
        f"random_crop = false\n"
        f"caption_dropout_rate = 0.05\n\n"
        f"[training]\n"
        f'output_dir = "{staging_dir / "output"}"\n'
        f'output_name = "{output_name}"\n'
        f"save_every_n_steps = {save_every}\n"
        f'save_model_as = "safetensors"\n'
        f"max_train_steps = {steps}\n"
        f"train_batch_size = {batch_size}\n"
        f"gradient_accumulation_steps = 1\n"
        f"gradient_checkpointing = true\n"
        f'mixed_precision = "bf16"\n'
        f"seed = 42\n"
        f"clip_skip = 1\n"
        f"cache_latents = true\n"
        f"cache_latents_to_disk = true\n\n"
        f"[optimizer]\n"
        f'optimizer_type = "AdamW8bit"\n'
        f"learning_rate = {learning_rate}\n"
        f'lr_scheduler = "cosine"\n'
        f"lr_warmup_steps = {warmup_steps}\n\n"
        f"[network]\n"
        f'network_module = "networks.lora"\n'
        f"network_dim = {rank}\n"
        f"network_alpha = {rank}\n"
        f"network_train_unet_only = true\n\n"
        f"[logging]\n"
        f'logging_dir = "{staging_dir / "logs"}"\n'
        f'log_prefix = "{output_name}"\n'
    )

    kohya_path = staging_dir / f"{output_name}_kohya.toml"
    kohya_path.write_text(kohya_toml)
    log.info("Generated kohya_ss config: %s", kohya_path)

    return aitk_path


# ---------------------------------------------------------------------------
# Training execution (stub)
# ---------------------------------------------------------------------------
def run_training(slug: str, staging_dir: Path, config_path: Path, dry_run: bool) -> dict:
    """
    SSH to WORKSHOP and execute LoRA training.

    TODO: Install one of these training frameworks on WORKSHOP:

    Option A — ai-toolkit (recommended for FLUX):
        git clone https://github.com/ostris/ai-toolkit.git /opt/ai-toolkit
        cd /opt/ai-toolkit && pip install -r requirements.txt
        Training command:
            CUDA_VISIBLE_DEVICES=0 python run.py <config_path>

    Option B — kohya_ss:
        git clone https://github.com/kohya-ss/sd-scripts.git /opt/kohya_ss
        cd /opt/kohya_ss && pip install -r requirements.txt
        Training command:
            CUDA_VISIBLE_DEVICES=0 accelerate launch --num_cpu_threads_per_process 1 \\
                flux_train_network.py --config_file <kohya_toml_path>

    Option C — SimpleTuner:
        git clone https://github.com/bghira/SimpleTuner.git /opt/SimpleTuner
        Supports FLUX natively, good VRAM efficiency.

    Hardware: RTX 5090 32GB (GPU 0 on WORKSHOP) is the training target.
              Use CUDA_VISIBLE_DEVICES=0 to isolate from GPU 1 (5060 Ti running ComfyUI).

    VRAM estimate for FLUX LoRA rank 16 at 1024x1024:
        ~22-26GB with gradient checkpointing + bf16 + adamw8bit
        Fits comfortably on RTX 5090 32GB.
    """
    output_name = f"{slug}_lora"
    final_lora = LORA_OUTPUT_DIR / f"{output_name}.safetensors"

    if dry_run:
        log.info("DRY RUN — skipping actual training")
        log.info("Training config: %s", config_path)
        log.info("Would train on WORKSHOP (RTX 5090, GPU 0)")
        log.info("Output would go to: %s", final_lora)
        return {
            "status": "dry_run",
            "config": str(config_path),
            "output": str(final_lora),
        }

    # ---------- TRAINING STUB ----------
    # Uncomment and adjust when training framework is installed on WORKSHOP:
    #
    # training_cmd = (
    #     f"CUDA_VISIBLE_DEVICES=0 "
    #     f"cd /opt/ai-toolkit && "
    #     f"python run.py {config_path}"
    # )
    # log.info("Starting training on WORKSHOP...")
    # log.info("Command: %s", training_cmd)
    #
    # result = subprocess.run(
    #     ["ssh", WORKSHOP_SSH, training_cmd],
    #     capture_output=True,
    #     text=True,
    #     timeout=7200,  # 2 hour timeout
    # )
    #
    # if result.returncode != 0:
    #     log.error("Training failed: %s", result.stderr[-500:])
    #     return {"status": "failed", "error": result.stderr[-500:]}
    #
    # # Copy final LoRA to the ComfyUI loras directory
    # output_lora = staging_dir / "output" / f"{output_name}.safetensors"
    # if output_lora.exists():
    #     shutil.copy2(output_lora, final_lora)
    #     log.info("LoRA saved to: %s", final_lora)
    # ---------- END STUB ----------

    log.warning(
        "Training execution is not yet configured. "
        "Install ai-toolkit or kohya_ss on WORKSHOP and uncomment "
        "the training block in run_training()."
    )

    manual_cmd = (
        f"ssh {WORKSHOP_SSH} "
        f"'CUDA_VISIBLE_DEVICES=0 python /opt/ai-toolkit/run.py {config_path}'"
    )
    log.info("Training config ready at: %s", config_path)
    log.info("Manual command:\n  %s", manual_cmd)

    return {
        "status": "stub",
        "config": str(config_path),
        "expected_output": str(final_lora),
        "manual_command": manual_cmd,
    }


# ---------------------------------------------------------------------------
# Training log
# ---------------------------------------------------------------------------
def update_training_log(slug: str, result: dict, image_count: int, config: dict):
    """Append training run info to the JSON log."""
    TRAINING_LOG.parent.mkdir(parents=True, exist_ok=True)

    log_entries: list[dict] = []
    if TRAINING_LOG.exists():
        try:
            log_entries = json.loads(TRAINING_LOG.read_text())
        except (json.JSONDecodeError, ValueError):
            log_entries = []

    entry = {
        "slug": slug,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "image_count": image_count,
        "resolution": config["resolution"],
        "rank": config["rank"],
        "learning_rate": config["learning_rate"],
        "steps": config["steps"],
        "batch_size": config["batch_size"],
        "result": result,
    }

    log_entries.append(entry)
    TRAINING_LOG.write_text(json.dumps(log_entries, indent=2))
    log.info("Training log updated: %s", TRAINING_LOG)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="LoRA training automation for auto_gen pipeline subjects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s peta-jensen                          # Full pipeline with defaults\n"
            "  %(prog)s peta-jensen --resolution 512         # Lower res (faster, less VRAM)\n"
            "  %(prog)s peta-jensen --rank 32 --steps 2000   # Higher quality, longer training\n"
            "  %(prog)s peta-jensen --caption-only            # Just regenerate captions\n"
            "  %(prog)s peta-jensen --dry-run                 # Prep everything, skip training\n"
            "  %(prog)s peta-jensen --skip-captions           # Use existing captions\n"
        ),
    )
    parser.add_argument("slug", help="Subject slug (e.g., peta-jensen)")
    parser.add_argument(
        "--resolution", type=int, default=1024, choices=[512, 768, 1024],
        help="Training resolution (default: 1024)",
    )
    parser.add_argument(
        "--rank", type=int, default=16,
        help="LoRA rank/dim (default: 16, higher=more capacity)",
    )
    parser.add_argument(
        "--learning-rate", type=float, default=1e-4,
        help="Learning rate (default: 1e-4)",
    )
    parser.add_argument(
        "--steps", type=int, default=0,
        help="Training steps (default: auto based on image count)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=1,
        help="Training batch size (default: 1)",
    )
    parser.add_argument(
        "--caption-only", action="store_true",
        help="Only generate captions, skip training",
    )
    parser.add_argument(
        "--skip-captions", action="store_true",
        help="Skip caption generation (use existing .txt files)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Prepare data and config but skip training",
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="Remove existing staging dir before starting",
    )
    args = parser.parse_args()

    slug = args.slug.lower().strip()
    log.info("=" * 60)
    log.info("LoRA Training Pipeline — %s", slug)
    log.info("=" * 60)

    # --- Validate subject exists ---
    subject_dir = SUBJECTS_DIR / slug
    if not subject_dir.exists():
        log.error("Subject directory not found: %s", subject_dir)
        available = sorted(d.name for d in SUBJECTS_DIR.iterdir() if d.is_dir())
        log.error("Available subjects: %s", ", ".join(available))
        sys.exit(1)

    # --- Look up performer ---
    performer = load_performer(slug)
    if performer:
        log.info(
            "Performer found: %s (tier: %s, gen_suitability: %s)",
            performer.get("name"), performer.get("tier"), performer.get("gen_suitability"),
        )
    else:
        log.warning(
            "No performer record found for '%s' — captions will use generic descriptions",
            slug,
        )

    # --- Set up staging directory ---
    staging_dir = TRAINING_STAGING / slug
    if args.clean and staging_dir.exists():
        log.info("Cleaning staging directory: %s", staging_dir)
        shutil.rmtree(staging_dir)

    staging_dir.mkdir(parents=True, exist_ok=True)
    (staging_dir / "output").mkdir(exist_ok=True)
    (staging_dir / "logs").mkdir(exist_ok=True)

    # --- Prepare images ---
    log.info("Preparing images at %dx%d...", args.resolution, args.resolution)
    image_paths = prepare_images(slug, args.resolution, staging_dir)
    log.info("Prepared %d images", len(image_paths))

    # --- Generate captions ---
    if args.skip_captions:
        log.info("Skipping caption generation (--skip-captions)")
        missing = [p for p in image_paths if not p.with_suffix(".txt").exists()]
        if missing:
            log.warning(
                "%d images missing caption files — consider running without --skip-captions",
                len(missing),
            )
    else:
        log.info("Generating captions via LiteLLM (%s)...", LITELLM_MODEL)
        captions = caption_images(image_paths, performer, slug)
        log.info("Generated %d captions", len(captions))

        # Save captions manifest
        manifest_path = staging_dir / "captions.json"
        manifest_path.write_text(json.dumps(captions, indent=2))

    if args.caption_only:
        log.info("Caption-only mode — done.")
        return

    # --- Generate training config ---
    log.info("Generating training config...")
    config_path = generate_training_config(
        slug=slug,
        staging_dir=staging_dir,
        image_count=len(image_paths),
        resolution=args.resolution,
        rank=args.rank,
        learning_rate=args.learning_rate,
        steps=args.steps,
        batch_size=args.batch_size,
    )

    # --- Run training ---
    result = run_training(slug, staging_dir, config_path, dry_run=args.dry_run)

    # --- Log results ---
    config_summary = {
        "resolution": args.resolution,
        "rank": args.rank,
        "learning_rate": args.learning_rate,
        "steps": args.steps if args.steps > 0 else "auto",
        "batch_size": args.batch_size,
    }
    update_training_log(slug, result, len(image_paths), config_summary)

    # --- Summary ---
    log.info("=" * 60)
    log.info("Pipeline complete for %s", slug)
    log.info("  Images: %d", len(image_paths))
    log.info("  Staging: %s", staging_dir)
    log.info("  Config:  %s", config_path)
    log.info("  Status:  %s", result.get("status", "unknown"))
    if result.get("manual_command"):
        log.info("  Run manually:\n    %s", result["manual_command"])
    log.info("=" * 60)


if __name__ == "__main__":
    main()
