---
name: vLLM Deploy
description: Deploy and manage vLLM inference on Athanor nodes. Live production lanes use the pinned deterministic image athanor/vllm:qwen35-20260315.
disable-model-invocation: true
---

# vLLM Deploy

Deploy vLLM inference services on Athanor. Live production lanes on Foundry and Workshop use the pinned deterministic image `athanor/vllm:qwen35-20260315`, which comes from the known-good custom Blackwell lineage.

## Architecture

| Instance | Node | Port | GPUs | Model | Purpose |
|----------|------|------|------|-------|---------|
| vllm-coordinator | Foundry | 8000 | 0,1,3,4 (4x 5070Ti) TP=4 | Qwen3.5-27B-FP8 | Legacy degraded secondary reasoning lineage |
| llama-dolphin | Foundry | 8100 | 2 (4090) | dolphin3-r1-24b | Canonical healthy shared text lane |
| vllm-coder | Foundry | 8006 | 2 (4090) | devstral-small-2 | Coding |
| vllm-embedding | DEV | 8001 | 0 (5060Ti), 0.40 mem | Qwen3-Embedding-0.6B | Embeddings (1024-dim) |
| workshop-vision | Workshop | 8012 | 0 (5090) | Vision runtime | Current live Workshop inference lane |

## Image Strategy

The standard vLLM Docker images don't support Blackwell (sm_120) cleanly enough for Athanor. NGC images also ship stale vLLM versions. The live production solution is:

1. maintain a custom-capable build path in `ansible/roles/vllm/`
2. promote known-good output into a deterministic pinned tag
3. run Foundry and Workshop on the same pinned tag instead of a floating `athanor/vllm:qwen35`

```dockerfile
# Ansible template: ansible/roles/vllm/templates/Dockerfile.j2
FROM nvcr.io/nvidia/vllm:{{ vllm_ngc_tag }}-py3
RUN pip install vllm=={{ vllm_pip_version }} \
    --extra-index-url https://download.pytorch.org/whl/cu{{ vllm_cuda_suffix }}
```

Current pinned production image: `athanor/vllm:qwen35-20260315`

## Deployment via Ansible

```bash
cd ansible
ansible-playbook playbooks/site.yml --vault-password-file vault-password -i inventory.yml --tags vllm
```

Ansible vars (in `host_vars/`):
- `vllm_image: "athanor/vllm:qwen35-20260315"` — current deterministic production image on Foundry and Workshop
- `vllm_custom_build: true` — only when intentionally rebuilding the custom lineage
- `vllm_pip_version: "0.16.0"` — vLLM version to install in the custom lineage

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
| Qwen3.5-27B-FP8 | ~27 GB | FP8 | Foundry TP=4 at :8000 (degraded secondary lineage) |
| Qwen3.5-35B-A3B-AWQ | ~22 GB | AWQ | Historical Workshop worker lineage at :8010, not currently a healthy active lane |
| Huihui-Qwen3-8B | ~8 GB | None | Foundry GPU 2 (4090) at :8002 |
| Qwen3-Embedding-0.6B | ~1.2 GB | None | DEV GPU 0 at :8001 |

## Validation

```bash
# Check model serving
curl http://192.168.1.244:8000/v1/models

# Test degraded legacy coordinator surface
curl http://192.168.1.244:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"/models/Qwen3.5-27B-FP8","messages":[{"role":"user","content":"Hello"}],"max_tokens":50}'

# Check embeddings (DEV)
curl http://192.168.1.189:8001/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"/models/Qwen3-Embedding-0.6B","input":"test"}'

# Check coder (Foundry GPU 2)
curl http://192.168.1.244:8006/v1/models

# Check canonical healthy text lane
curl http://192.168.1.244:8100/v1/models
```
