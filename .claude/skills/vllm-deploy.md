---
name: vLLM Deploy
description: Deploy and manage vLLM inference on Athanor nodes. Custom image v0.16.0 on NGC base.
disable-model-invocation: true
---

# vLLM Deploy

Deploy vLLM inference services on Athanor. Uses custom Docker image (NGC 26.01-py3 base + vLLM v0.16.0 via pip cu130 wheels).

## Architecture

| Instance | Node | Port | GPUs | Model | Purpose |
|----------|------|------|------|-------|---------|
| vllm (primary) | Foundry | 8000 | 0-3 (5070Ti) + 4090, TP=4 | Qwen3-32B-AWQ | Reasoning, agents |
| vllm-embedding | Foundry | 8001 | 4 (4090), 0.40 mem | Qwen3-Embedding-0.6B | Embeddings (1024-dim) |
| vllm (secondary) | Workshop | 8000 | 0 (5090) | Qwen3-14B-AWQ | Fast inference |

## Custom Image Build

The standard vLLM Docker images don't support Blackwell (sm_120). NGC images ship stale vLLM versions. Our solution: NGC base + pip install vLLM from cu130 wheel index.

```dockerfile
# Ansible template: ansible/roles/vllm/templates/Dockerfile.j2
FROM nvcr.io/nvidia/vllm:{{ vllm_ngc_tag }}-py3
RUN pip install vllm=={{ vllm_pip_version }} \
    --extra-index-url https://download.pytorch.org/whl/cu{{ vllm_cuda_suffix }}
```

Built image: `athanor/vllm:latest` (34.6 GB). Verified: v0.16.0, sm_120 compatible.

## Deployment via Ansible

```bash
cd ansible
ansible-playbook playbooks/site.yml --vault-password-file vault-password -i inventory.yml --tags vllm
```

Ansible vars (in `host_vars/`):
- `vllm_custom_build: true` — builds from Dockerfile instead of pulling NGC
- `vllm_pip_version: "0.16.0"` — vLLM version to install
- `vllm_cuda_suffix: "130"` — cu130 for Blackwell
- `vllm_ngc_tag: "26.01"` — NGC base image tag

## Critical Blackwell (sm_120) Settings

```yaml
environment:
  - CUDA_DEVICE_ORDER=PCI_BUS_ID          # Required for mixed GPU TP
  - VLLM_FLASH_ATTN_VERSION=2             # FA3 not supported on Blackwell
  - PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
  - HF_HUB_OFFLINE=1
command:
  - --quantization awq                     # Must be explicit (Marlin crashes on Blackwell)
  - --gpu-memory-utilization 0.85          # 0.90 OOMs on 16GB GPUs during warmup
  - --max-num-seqs 128                     # 256 default OOMs
```

## Mixed GPU Tensor Parallel (Node 1)

4x RTX 5070 Ti (sm_120) + RTX 4090 (sm_89) work together with:
- `--quantization awq` (not Marlin — Marlin kernel crashes on mixed architectures)
- `CUDA_DEVICE_ORDER=PCI_BUS_ID`
- `--tensor-parallel-size 4` (uses GPUs 0-3, the 4x 5070 Ti)

## Sleep Mode

**BLOCKED:** `--enable-sleep-mode` flag is accepted by vLLM v0.16.0 without error, but the REST endpoints (`/sleep`, `/wake_up`, `/is_sleeping`) return 404 in V1 engine (default in v0.16.0). This is a known issue — the endpoints are only registered in the V0 engine path. Need vLLM v0.17.0+ or explicit V0 engine mode (which loses other V1 features).

## Available Models (VAULT NFS)

| Model | Size | Quant | Fits Where |
|-------|------|-------|------------|
| Qwen3-32B-AWQ | ~20 GB | AWQ | Foundry TP=4 (current) |
| Qwen3-14B-AWQ | ~8 GB | AWQ | Workshop single GPU |
| Qwen3-Embedding-0.6B | ~1.2 GB | None | Foundry GPU 4 |
| Qwen3.5-27B-FP8 | ~27 GB | FP8 | Foundry TP=4 (download needed) |

## Validation

```bash
# Check model serving
curl http://192.168.1.244:8000/v1/models

# Test inference
curl http://192.168.1.244:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"/models/Qwen3-32B-AWQ","messages":[{"role":"user","content":"Hello"}],"max_tokens":50}'

# Check embeddings
curl http://192.168.1.244:8001/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"/models/Qwen3-Embedding-0.6B","input":"test"}'

# Check sleep mode
curl http://192.168.1.244:8000/is_sleeping
```
