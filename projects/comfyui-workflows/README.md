# ComfyUI Workflow Templates

Reusable workflow templates for the creative and media agents. ComfyUI runs on WORKSHOP (192.168.1.225:8188).

## Available Workflows

| File | Description | Default Resolution | Steps |
|------|-------------|-------------------|-------|
| `txt2img-flux.json` | Text-to-image with Flux dev FP8 | 1024x1024 | 20 |
| `img2img-flux.json` | Image-to-image with Flux (denoise 0.7) | 1024x1024 | 20 |
| `upscale-4x.json` | 4x upscale via UltraSharp/RealESRGAN | Input-dependent | N/A |
| `character-portrait.json` | EoBQ character portraits (portrait aspect) | 768x1024 | 25 |

## Format

All workflows use the **ComfyUI API format** (not web UI export). Each file is a JSON object with numbered string keys as node IDs:

```json
{
  "1": {
    "class_type": "NodeType",
    "inputs": { ... },
    "_meta": { "title": "Human-Readable Name" }
  }
}
```

## Usage

Send to ComfyUI via POST to `/prompt`:

```python
import httpx

workflow = json.load(open("txt2img-flux.json"))
# Replace placeholder with actual prompt
workflow["6"]["inputs"]["text"] = "your prompt here"

resp = httpx.post(
    "http://192.168.1.225:8188/prompt",
    json={"prompt": workflow, "client_id": "my-client-id"},
)
```

## Placeholders

- `{{prompt}}` in text encode nodes -- replace with the actual prompt before submission.
- Seed values use a fixed default; randomize before submission for variation.
