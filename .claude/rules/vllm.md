---
paths:
  - "ansible/roles/vllm/**"
  - "docs/research/*vllm*"
---

# vLLM on Blackwell (sm_120)

- Custom image required: NGC 26.01-py3 base + pip vLLM v0.16.0 cu130 wheels
- **NGC flash-attn must be removed** in Dockerfile — ABI mismatch with vLLM's PyTorch causes `ImportError: undefined symbol` in `flash_attn_2_cuda.so`. vLLM v0.16.0 uses FlashInfer instead.
- **NGC flashinfer-cubin version mismatch:** NGC ships v0.6.0, pip vLLM installs flashinfer v0.6.3. Set `FLASHINFER_DISABLE_VERSION_CHECK=1` env var (NGC cubin is cu131 Blackwell-specific, can't replace from pip).
- Do NOT set `VLLM_FLASH_ATTN_VERSION` or `--attention-backend FLASH_ATTN` — the NGC flash-attn .so is broken after pip upgrade.
- `--quantization awq` must be explicit (Marlin kernel crashes on Blackwell)
- `CUDA_DEVICE_ORDER=PCI_BUS_ID` required for mixed GPU TP (5070 Ti sm_120 + 4090 sm_89)
- `--gpu-memory-utilization 0.85` on 16GB GPUs (0.90 OOMs during warmup)
- `--max-num-seqs 64` on 16GB GPUs (128 OOMs during v0.16.0 sampler warmup with 128 dummy requests)
- Sleep mode: `--enable-sleep-mode` accepted but **REST endpoints (`/sleep`, `/wake_up`, `/is_sleeping`) are NOT available** in v0.16.0 V1 engine. Flag is accepted without error but endpoints return 404.
- NGC vLLM images are stale: 26.01-py3 ships v0.13.0, not what release notes claim
- Embedding model: Qwen3-Embedding-0.6B at `/models/Qwen3-Embedding-0.6B` on port 8001
- Ansible `docker_compose_v2` needs `recreate: always` in custom build mode — otherwise stale containers persist
- All `vllm_extra_args` must be quoted as `"{{ arg }}"` in compose template (YAML renders numbers as int)
