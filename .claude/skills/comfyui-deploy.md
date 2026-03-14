---
name: ComfyUI Deploy
description: Deploy ComfyUI on Node 2 with Blackwell GPU compatibility.
---

# ComfyUI Deploy

Deploy ComfyUI on Node 2, pinned to RTX 5090 (GPU 1).

## CRITICAL: Blackwell GPU Compatibility

Standard ComfyUI Docker images do NOT work with RTX 5090 (sm_120).

**Working image**: `athanor/comfyui:blackwell` (custom build)
- Built from `nvcr.io/nvidia/pytorch:25.02-py3` base
- ComfyUI 0.13.0, PyTorch 2.7.0a0, CUDA 12.8
- Dockerfile at `/opt/athanor/comfyui/Dockerfile` on Node 2

## Dockerfile

```dockerfile
FROM nvcr.io/nvidia/pytorch:25.02-py3

ENV DEBIAN_FRONTEND=noninteractive
ENV COMFYUI_DIR=/opt/ComfyUI

RUN apt-get update && apt-get install -y --no-install-recommends \
    git libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/comfyanonymous/ComfyUI.git ${COMFYUI_DIR}
WORKDIR ${COMFYUI_DIR}
RUN pip install --no-cache-dir -r requirements.txt
RUN git clone https://github.com/ltdrdata/ComfyUI-Manager.git ${COMFYUI_DIR}/custom_nodes/ComfyUI-Manager

EXPOSE 8188
CMD ["python3", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
```

## Deployment

```yaml
# /opt/athanor/comfyui/docker-compose.yml
services:
  comfyui:
    image: athanor/comfyui:blackwell
    container_name: comfyui
    restart: unless-stopped
    ports:
      - "8188:8188"
    volumes:
      - comfyui-output:/opt/ComfyUI/output
      - comfyui-input:/opt/ComfyUI/input
      - comfyui-custom-nodes:/opt/ComfyUI/custom_nodes
      - comfyui-user:/opt/ComfyUI/user
      - /mnt/vault/models:/mnt/vault/models:ro
      - /opt/athanor/comfyui/extra_model_paths.yaml:/opt/ComfyUI/extra_model_paths.yaml:ro
    ipc: host
    ulimits:
      memlock: -1
      stack: 67108864
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["1"]
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=1
```

## Models (on VAULT NFS → /mnt/vault/models/comfyui/)

```yaml
# /opt/athanor/comfyui/extra_model_paths.yaml
vault_nfs:
    base_path: /mnt/vault/models/comfyui/
    diffusion_models: unet/
    clip: clip/
    vae: vae/
    checkpoints: checkpoints/
```

| File | Size | Path |
|------|------|------|
| flux1-dev-fp8.safetensors | 12 GB | unet/ |
| clip_l.safetensors | 235 MB | clip/ |
| t5xxl_fp8_e4m3fn.safetensors | 4.6 GB | clip/ |
| ae.safetensors | 320 MB | vae/ |

**Note**: Full-precision Flux dev (23 GB) requires HuggingFace auth (gated repo). FP8 version from [Kijai/flux-fp8](https://huggingface.co/Kijai/flux-fp8) is public and works great on RTX 5090.

## Rebuilding

```bash
ssh node2
cd /opt/athanor/comfyui
sudo docker compose build --no-cache
sudo docker compose up -d
```

## Ports

| Service | Node | Port | Purpose |
|---------|------|------|---------|
| ComfyUI | Node 2 | 8188 | Image generation UI (RTX 5090) |
