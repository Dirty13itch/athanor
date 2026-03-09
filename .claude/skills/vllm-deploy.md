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
| vllm-coordinator | Foundry | 8000 | 0,1,3,4 (4x 5070Ti) TP=4 | Qwen3.5-27B-FP8 | Reasoning, agents |
| vllm-utility | Foundry | 8002 | 2 (4090) | Huihui-Qwen3-8B | Utility/fast |
| vllm-embedding | DEV | 8001 | 0 (5060Ti), 0.40 mem | Qwen3-Embedding-0.6B | Embeddings (1024-dim) |
| vllm (secondary) | Workshop | 8000 | 0 (5090) | Qwen3.5-35B-A3B-AWQ | Fast inference |

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
  # Do NOT set VLLM_FLASH_ATTN_VERSION — NGC image handles FA correctly
  - PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
  - HF_HUB_OFFLINE=1
command:
  - --quantization awq                     # Must be explicit (Marlin crashes on Blackwell)
  - --gpu-memory-utilization 0.85          # 0.90 OOMs on 16GB GPUs during warmup
  - --max-num-seqs 64                      # 128+ OOMs on 16GB GPUs
```

## Mixed GPU Tensor Parallel (Node 1)

4x RTX 5070 Ti (sm_120) + RTX 4090 (sm_89) work together with:
- `--quantization awq` (not Marlin — Marlin kernel crashes on mixed architectures)
- `CUDA_DEVICE_ORDER=PCI_BUS_ID`
- `--tensor-parallel-size 4` (uses GPUs 0,1,3,4, the 4x 5070 Ti)

## Sleep Mode

**BLOCKED:** `--enable-sleep-mode` flag is accepted by vLLM v0.16.0 without error, but the REST endpoints (`/sleep`, `/wake_up`, `/is_sleeping`) return 404 in V1 engine (default in v0.16.0). This is a known issue — the endpoints are only registered in the V0 engine path. Need vLLM v0.17.0+ or explicit V0 engine mode (which loses other V1 features).

## Available Models (VAULT NFS)

| Model | Size | Quant | Deployed Where |
|-------|------|-------|----------------|
| Qwen3.5-27B-FP8 | ~27 GB | FP8 | Foundry TP=4 at :8000 (current) |
| Qwen3.5-35B-A3B-AWQ | ~22 GB | AWQ | Workshop single GPU at :8000 (--language-model-only) |
| Huihui-Qwen3-8B | ~8 GB | None | Foundry GPU 2 (4090) at :8002 |
| Qwen3-Embedding-0.6B | ~1.2 GB | None | DEV GPU 0 at :8001 |

## Validation

```bash
# Check model serving
curl http://192.168.1.244:8000/v1/models

# Test inference (Foundry coordinator)
curl http://192.168.1.244:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"/models/Qwen3.5-27B-FP8","messages":[{"role":"user","content":"Hello"}],"max_tokens":50}'

# Check embeddings (DEV)
curl http://192.168.1.189:8001/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"/models/Qwen3-Embedding-0.6B","input":"test"}'

# Check utility (Foundry GPU 2)
curl http://192.168.1.244:8002/v1/models
```
