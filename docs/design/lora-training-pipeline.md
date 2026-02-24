# LoRA Training Pipeline

*Planned capability. Hardware is capable, no implementation yet.*

---

## Use Cases

1. **EoBQ Character Consistency (Text):** Train LoRAs on character dialogue samples and personality traits for consistent voice per character without relying entirely on prompt engineering
2. **EoBQ Visual Consistency (Image):** Train image LoRAs (Flux/SDXL) on character reference images — same face, body type, clothing style across scenes
3. **Custom Style Models:** Train style LoRAs for specific aesthetics (e.g., "film noir" LoRA, "cyberpunk apartment" LoRA for scene generation)
4. **Business Document Style:** Potentially train a LoRA on Ulrich Energy's report library for consistent writing style

---

## Pipeline Architecture

### Dataset Preparation

- Collect training data (dialogue samples, images, documents)
- Clean and format (JSONL for text, captioned images for visual)
- Split train/validation sets
- Store in `projects/{project}/training_data/`

### Training Execution

- **Text LoRAs:** unsloth, axolotl, or similar framework
- **Image LoRAs:** kohya_ss or sd-scripts for Flux/SDXL LoRA training
- Run on Node 1 (TP=4 group) or Node 2 (RTX 5090) depending on model type
- Training is a BATCH workload — schedule overnight or during low inference demand
- Docker container with training framework, mounts model weights and dataset from NVMe

### Evaluation

- Generate test outputs with LoRA applied
- Compare against baseline (same prompts, no LoRA)
- Human review: does this character sound right? does this face match?
- Automated metrics where applicable (perplexity for text, FID for images)

### Deployment

- Validated LoRA weights → Tier 2 (VAULT model repo) → rsync to node
- For text: vLLM supports LoRA loading at inference time (`--lora-modules` flag)
- For images: ComfyUI loads LoRAs natively via workflow nodes
- Version control: tag LoRA versions in the model repo, roll back if quality regresses

---

## GPU Requirements

| Workload | VRAM Needed | Best GPU |
|----------|-------------|----------|
| Text LoRA on 32B base | ~24-32 GB | RTX 5090 |
| Image LoRA (Flux) | ~16-24 GB | RTX 5090 or 5070 Ti |

Training time: hours to days depending on dataset size and epochs.

**Critical:** Training and inference cannot share the same GPU simultaneously. Schedule training during off-hours, or temporarily remove a GPU from the vLLM pool.
