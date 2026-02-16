# vLLM Deploy

Deploy a model on vLLM. Handles model selection, GPU assignment, and health checks.

## Prerequisites

- NVIDIA drivers 580+ installed ✅
- Docker + NVIDIA CTK installed ✅
- NFS mount to VAULT /mnt/user/models (for model cache)

## Deployment Patterns

### Node 1: 4-GPU Tensor Parallel (Primary Inference)

```bash
ssh node1
sudo mkdir -p /opt/athanor/vllm
```

```yaml
# /opt/athanor/vllm/docker-compose.yml
services:
  vllm:
    image: vllm/vllm-openai:latest
    container_name: vllm
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    ports:
      - "8000:8000"
    volumes:
      - /mnt/vault/models:/models
      - ./cache:/root/.cache/huggingface
    environment:
      - HF_HOME=/models
      - VLLM_ATTENTION_BACKEND=FLASHINFER
    command: >
      --model meta-llama/Llama-3.1-70B-Instruct
      --tensor-parallel-size 4
      --host 0.0.0.0
      --port 8000
      --max-model-len 8192
      --gpu-memory-utilization 0.90
    ipc: host
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 300s
```

### Node 2: Single GPU Instances

RTX 5090 (GPU 1) — larger models:
```yaml
services:
  vllm-5090:
    image: vllm/vllm-openai:latest
    container_name: vllm-5090
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['1']
              capabilities: [gpu]
    ports:
      - "8000:8000"
    volumes:
      - /mnt/vault/models:/models
    environment:
      - HF_HOME=/models
      - NVIDIA_VISIBLE_DEVICES=1
    command: >
      --model meta-llama/Llama-3.1-8B-Instruct
      --host 0.0.0.0
      --port 8000
    ipc: host
```

RTX 4090 (GPU 0) — fast chat:
```yaml
  vllm-4090:
    image: vllm/vllm-openai:latest
    container_name: vllm-4090
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['0']
              capabilities: [gpu]
    ports:
      - "8001:8000"
    volumes:
      - /mnt/vault/models:/models
    environment:
      - HF_HOME=/models
      - NVIDIA_VISIBLE_DEVICES=0
    command: >
      --model mistralai/Mistral-7B-Instruct-v0.3
      --host 0.0.0.0
      --port 8000
    ipc: host
```

## Model Sizing Guide

| Model | FP16 VRAM | NVFP4 VRAM | Fits Where |
|-------|-----------|------------|------------|
| Llama 3.1 70B | ~140 GB | ~35 GB | Node 1 (4-GPU TP) or Node 2 5090 (NVFP4) |
| Qwen 72B | ~144 GB | ~36 GB | Node 1 (4-GPU TP) |
| Llama 3.1 8B | ~16 GB | ~4 GB | Any single GPU |
| Mistral 7B | ~14 GB | ~3.5 GB | Any single GPU |
| Phi-3 Mini (3.8B) | ~8 GB | ~2 GB | Any single GPU |

Note: NVFP4 is Blackwell-only (5070 Ti, 5090). RTX 4090 uses GPTQ/AWQ/FP16.

## Validation

```bash
# Health check
curl http://node1:8000/health

# List models
curl http://node1:8000/v1/models

# Test inference
curl http://node1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.1-70B-Instruct",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
  }'
```

## Blackwell Build Notes

If the official vllm/vllm-openai image doesn't support sm_120 (Blackwell), build from source:

```dockerfile
FROM nvidia/cuda:12.8.0-devel-ubuntu22.04
RUN pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu128
RUN TORCH_CUDA_ARCH_LIST="12.0" pip install vllm
ENV VLLM_ATTENTION_BACKEND=FLASHINFER
```

## Ports

| Service | Node | Port | Purpose |
|---------|------|------|---------|
| vLLM primary | Node 1 | 8000 | 4-GPU TP, large models |
| vLLM 5090 | Node 2 | 8000 | Single-GPU, large models |
| vLLM 4090 | Node 2 | 8001 | Fast chat, small models |
