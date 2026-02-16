# vLLM Deploy

Deploy a model on vLLM. Handles model selection, GPU assignment, and health checks.

## Prerequisites

- NVIDIA drivers 580+ installed
- Docker + NVIDIA CTK installed
- NFS mount to VAULT at /mnt/vault/models

## CRITICAL: Blackwell GPU Compatibility

The official `vllm/vllm-openai:latest` image does NOT work with driver 580 / Blackwell GPUs.

**Working image**: `nvcr.io/nvidia/vllm:25.12-py3`
- PyTorch 2.10.0a0 (NVIDIA build), CUDA 13.1, vLLM 0.11.1
- Confirmed working on 4x RTX 5070 Ti (sm_120) with driver 580.126.09

**Key settings for 16 GB GPUs (5070 Ti)**:
- `--gpu-memory-utilization 0.85` (0.90 causes OOM during warmup)
- `--max-num-seqs 128` (256 default causes OOM)
- `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`
- `VLLM_FLASH_ATTN_VERSION=2` (FA3 not supported on Blackwell)

## Deployment: Node 1 (4-GPU Tensor Parallel)

```yaml
# /opt/athanor/vllm/docker-compose.yml
services:
  vllm:
    image: nvcr.io/nvidia/vllm:25.12-py3
    container_name: vllm
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - /mnt/vault/models:/models:ro
    environment:
      - HF_HUB_OFFLINE=1
      - VLLM_FLASH_ATTN_VERSION=2
      - PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
    ipc: host
    ulimits:
      memlock: -1
      stack: 67108864
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    entrypoint: ["python3", "-m", "vllm.entrypoints.openai.api_server"]
    command:
      - --model
      - /models/Qwen3-14B
      - --tensor-parallel-size
      - "4"
      - --host
      - 0.0.0.0
      - --port
      - "8000"
      - --max-model-len
      - "8192"
      - --gpu-memory-utilization
      - "0.85"
      - --max-num-seqs
      - "128"
      - --dtype
      - auto
```

## Available Models on VAULT NFS

| Model | Size | Quantization | Fits Where |
|-------|------|-------------|------------|
| Qwen3-14B | ~28 GB FP16 | None | Node 1 TP=4 (current) |
| Qwen3-32B-AWQ | ~20 GB | AWQ | Node 1 TP=4 or Node 2 5090 single |
| gte-Qwen2-7B-instruct | ~14 GB | None | Any single GPU |

## Validation

```bash
# List models
curl http://192.168.1.244:8000/v1/models

# Test inference
curl http://192.168.1.244:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "/models/Qwen3-14B",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
  }'
```

## Upgrading vLLM

When newer NGC vLLM images are released (e.g., 26.01, 26.02):
1. Check Blackwell/sm_120 support in release notes
2. Test CUDA init: `docker run --rm --gpus all --entrypoint python3 <image> -c "import torch; print(torch.cuda.is_available())"`
3. If True, update the image tag in docker-compose.yml

Alternative: Build from source using `nvcr.io/nvidia/pytorch:25.02-py3` base + PyTorch nightly cu128.

## Ports

| Service | Node | Port | Purpose |
|---------|------|------|---------|
| vLLM primary | Node 1 | 8000 | 4-GPU TP, large models |
