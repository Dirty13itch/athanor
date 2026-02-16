# EoBQ ComfyUI Workflows

Flux dev FP8 workflows for Empire of Broken Queens image generation.
Running on Node 2 (192.168.1.225:8188), RTX 5090 (32 GB VRAM).

## Workflows

### flux-character-portrait.json
- **Resolution**: 832x1216 (portrait)
- **Steps**: 25, euler sampler, simple scheduler
- **Guidance**: 3.5 via FluxGuidance node
- **Use**: Character portraits, close-ups, upper body shots
- **Output prefix**: `EoBQ/character`

### flux-scene.json
- **Resolution**: 1344x768 (wide cinematic)
- **Steps**: 25, euler sampler, simple scheduler
- **Guidance**: 3.5 via FluxGuidance node
- **Use**: Environment shots, establishing scenes, throne rooms, landscapes
- **Output prefix**: `EoBQ/scene`

## API Usage

Queue a generation via the ComfyUI API:

```bash
curl -X POST http://192.168.1.225:8188/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": <workflow-json-contents>}'
```

Change the prompt text in node "3" (CLIPTextEncode) and the seed in node "7" (KSampler) to generate variations.

## Key Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Model | flux1-dev-fp8.safetensors | FP8 quantized, ~12 GB VRAM |
| CLIP 1 | t5xxl_fp8_e4m3fn.safetensors | T5-XXL text encoder |
| CLIP 2 | clip_l.safetensors | CLIP-L text encoder |
| VAE | ae.safetensors | Flux autoencoder |
| CFG | 1.0 | Flux uses FluxGuidance instead |
| Guidance | 3.5 | Via FluxGuidance node (range: 1.5-5.0) |
| Steps | 25 | 20-30 for quality, 15-20 for speed |

## Prompt Tips for EoBQ

- **Style anchors**: "cinematic, photorealistic, 8k, dramatic lighting, film color grading"
- **Depth**: "shallow depth of field" for portraits, "deep focus" for scenes
- **Mood**: "moody atmosphere, dark fantasy, warm candlelight, cold moonlight"
- **Flux responds well to detailed natural language** — describe the scene like a film director would
- **Negative prompts are ignored** by Flux — leave empty

## Future Enhancements

- LoRA training for character consistency (same face across generations)
- ControlNet for pose guidance
- IP-Adapter for style reference images
- Batch generation scripts for game asset pipelines
