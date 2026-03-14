---
paths:
  - "ansible/roles/vllm/**"
  - "docs/research/*vllm*"
---

# vLLM on Blackwell (sm_120)

- Custom image required: NGC 26.01-py3 base + pip vLLM v0.16.0 cu130 wheels
- **NGC flash-attn must be removed** in Dockerfile â€” ABI mismatch with vLLM's PyTorch causes `ImportError: undefined symbol` in `flash_attn_2_cuda.so`. vLLM v0.16.0 uses FlashInfer instead.
- **NGC flashinfer-cubin version mismatch:** NGC ships v0.6.0, pip vLLM installs flashinfer v0.6.3. Set `FLASHINFER_DISABLE_VERSION_CHECK=1` env var (NGC cubin is cu131 Blackwell-specific, can't replace from pip).
- Do NOT set `VLLM_FLASH_ATTN_VERSION` or `--attention-backend FLASH_ATTN` â€” the NGC flash-attn .so is broken after pip upgrade.
- `--quantization awq` must be explicit (Marlin kernel crashes on Blackwell)
- `CUDA_DEVICE_ORDER=PCI_BUS_ID` required for mixed GPU TP (5070 Ti sm_120 + 4090 sm_89)
- `--gpu-memory-utilization 0.85` on 16GB GPUs (0.90 OOMs during warmup)
- `--max-num-seqs 64` on 16GB GPUs (128 OOMs during v0.16.0 sampler warmup with 128 dummy requests)
- Sleep mode: `--enable-sleep-mode` accepted but **REST endpoints (`/sleep`, `/wake_up`, `/is_sleeping`) are NOT available** in v0.16.0 V1 engine. Flag is accepted without error but endpoints return 404.
- NGC vLLM images are stale: 26.01-py3 ships v0.13.0, not what release notes claim
- Embedding model: Qwen3-Embedding-0.6B at `/models/Qwen3-Embedding-0.6B` on port 8001
- Ansible `docker_compose_v2` needs `recreate: always` in custom build mode â€” otherwise stale containers persist
- All `vllm_extra_args` must be quoted as `"{{ arg }}"` in compose template (YAML renders numbers as int)

## Qwen3.5 Specifics
- **`--cpu-offload-gb` INCOMPATIBLE** with `--enable-prefix-caching` (Python assertion error at startup) and MTP speculative decoding. Do NOT use either flag together with cpu-offload. Track vLLM/PR#18298 for fix.
- **`--language-model-only` REQUIRED** â€” Without it, VLM encoder profiling allocates 229K tokens â†’ exceeds 131K max â†’ crash. Only exists in nightly (not v0.16.0 stable).
- **`--tool-call-parser qwen3_xml`** â€” Qwen3.5 uses XML tool format, not hermes JSON. `hermes` silently fails.
- **`--enforce-eager` REQUIRED on 16GB GPUs** â€” CUDA graph replay of DeltaNet/Mamba Triton kernels causes "Triton Error [CUDA]: out of memory" even at 0.85 utilization. Eager mode avoids this. First inference is slow (~90s compile), subsequent are fast.
- FP8 (28 GiB) OOMs on single 5090 (32 GiB) â€” insufficient headroom for KV cache after model load. Use AWQ (~21 GiB) for single-GPU, FP8 for TP=4.
- Qwen3.5-9B-abliterated (Qwen3NextForCausalLM) OOMs on 4090 24GB â€” MoE expert weights expand to ~25 GB during init. Does NOT fit single 4090.
- `awq_marlin` auto-detected as faster; `--quantization awq` forces standard AWQ.
- **compressed-tensors AWQ models:** Some AWQ models (e.g., Qwen3.5-35B-A3B-AWQ-4bit) use `compressed-tensors` serialization. Do NOT pass `--quantization awq` — it conflicts with the model config. Let vLLM auto-detect from `config.json`.
- `fix-vllm-qwen35.py` in `ansible/roles/vllm/files/` â€” idempotent patches (both present in nightly, needed for future stable releases).

## Current FOUNDRY Deployment
- Coordinator: Qwen3.5-27B-FP8 TP=4 on GPUs 0,1,3,4 (4x5070Ti) at foundry:8000 â€” `--tool-call-parser qwen3_xml --enforce-eager --language-model-only`
- Coder: Qwen3.5-35B-A3B-AWQ-4bit on GPU 2 (4090) at foundry:8006 — `--tool-call-parser qwen3_xml --enforce-eager --language-model-only` (no --quantization flag, auto-detects compressed-tensors)
- Container names: `vllm-coordinator`, `vllm-coder`
- Image: `athanor/vllm:qwen35` (nightly 0.16.1rc1.dev32)

## Current WORKSHOP Deployment
- Worker: Qwen3.5-35B-A3B-AWQ on GPU 0 (5090) at workshop:8000 â€” `--tool-call-parser qwen3_xml --kv-cache-dtype auto`
- Image: `athanor/vllm:qwen35` (nightly 0.16.1rc1.dev32)

