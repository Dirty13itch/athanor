# vLLM Upgrade Path: NGC Lag and Qwen3.5 Support

**Date:** 2026-02-26
**Updated:** 2026-02-26 (corrected NGC 26.01 version — v0.13.0, not v0.11.1)
**Context:** Session 19 identified vLLM v0.15.0+ as critical for Qwen3.5 DeltaNet. This research investigates the actual upgrade path.

## Current State

- **Running:** `nvcr.io/nvidia/vllm:25.12-py3` → vLLM v0.11.1
- **Latest NGC:** `nvcr.io/nvidia/vllm:26.01-py3` → vLLM **v0.13.0** (NGC release notes incorrectly say v0.11.1)
- **NGC is 2 major versions behind upstream** (v0.13.0 vs v0.15.1 stable)

## NGC vLLM Container Timeline

| Tag | vLLM Version | Notes |
|-----|-------------|-------|
| 25.09-py3 | 0.11.1 | - |
| 25.10-py3 | 0.11.1 | - |
| 25.11-py3 | 0.11.1 | - |
| 25.12-py3 | 0.11.1 | **Currently running** |
| 25.12.post1-py3 | 0.12.0 | Patch release (previously missed) |
| 26.01-py3 | **0.13.0** | Latest available |

NGC was frozen on v0.11.1 for months but finally jumped to v0.13.0 in 26.01. No 26.02-py3 exists yet. NGC release notes page for 26.01 incorrectly says v0.11.1 — confirmed v0.13.0 via [NVIDIA Developer Forum](https://forums.developer.nvidia.com/t/new-ngc-vllm-container-image-vllm-26-01-py3/359213).

## Upstream vLLM Releases

| Version | Date | Key Features |
|---------|------|-------------|
| v0.14.0 | Jan 20, 2026 | Async scheduling default, gRPC, max-model-len auto |
| v0.15.0 | Jan 29, 2026 | NVFP4 65% faster on Blackwell, FlashInfer MLA default, EAGLE-3 |
| **v0.15.1** | **Feb 4, 2026** | **RTX Blackwell SM120 NVFP4 MoE fix**, FP8 kernel fallback for SM120, torch.compile cold-start 88s→22s |
| v0.16.0 | Feb 25, 2026 | Async + Pipeline Parallel (+30.8% throughput), WebSocket Realtime API, Unified Parallel Drafting |

**Deployed: v0.16.0** — includes all SM120 Blackwell fixes from v0.15.1 plus Async+Pipeline Parallel (+30.8% throughput), WebSocket Realtime API, Unified Parallel Drafting. Custom image: NGC 26.01-py3 base + `pip install vllm==0.16.0 --extra-index-url https://wheels.vllm.ai/nightly/cu130`.

## Qwen3.5 Architecture Requirements

Qwen3.5 uses **Gated Delta Networks** (`Qwen3_5GatedDeltaNet`) — a hybrid architecture combining full attention at set intervals with linear attention via Gated DeltaNet. This is fundamentally different from standard transformers.

- vLLM announced "day-0 support" around Qwen3.5 release (Feb 16-24, 2026)
- vLLM blog discussed hybrid KV cache manager + Triton kernels from Flash Linear Attention
- vLLM Qwen3.5 recipes page recommends **nightly** builds
- Realistic minimum: v0.14.0+ for base GatedDeltaNet, v0.15.1+ for SM120 fixes, nightly for fully optimized hybrid attention paging

## Gap Analysis: NGC 26.01 vs What We Need

| Capability | NGC 26.01 (v0.13.0) | We Need (v0.15.1+) | Gap |
|-----------|---------------------|---------------------|-----|
| Qwen3.5 GatedDeltaNet | Likely partial | Full with hybrid KV | 2 versions |
| NVFP4 on Blackwell | No SM120 fix | Fixed in v0.15.1 | Missing |
| vLLM sleep mode REST | Possibly present (v0.14.0+) | Available v0.14.0+ | May work |
| EAGLE-3 speculative | No | v0.15.0+ | Missing |
| FlashInfer MLA default | No | v0.15.0+ | Missing |
| Async + Pipeline Parallel | No | v0.16.0 | 3 versions |

## Upgrade Options

### Option 1: pip upgrade inside NGC container
**Approach:** `pip install vllm==0.15.1 --extra-index-url https://wheels.vllm.ai/nightly/cu130`
**Pros:** Keeps NGC CUDA 13.1 base (required for sm_120 Blackwell)
**Cons:** Breaks validated stack, potential compatibility issues
**Risk:** **Low-Medium** (only 2-version jump from v0.13.0 base)
**Source:** GitHub issue #31424 documents this workaround

### Option 2: Upstream vLLM Docker image
**Approach:** Use `vllm/vllm-openai:v0.15.1`
**Pros:** Official upstream, well-tested
**Cons:** Ships CUDA 12, not CUDA 13. Blackwell sm_120 needs CUDA 13+.
**Risk:** High — GitHub issue #34296 confirms failure on GPUs requiring CUDA 13
**Verdict:** Not viable for our hardware

### Option 3: Custom image (NGC base + pinned vLLM v0.15.1) ← RECOMMENDED
**Approach:** Build custom Dockerfile:
```dockerfile
FROM nvcr.io/nvidia/vllm:26.01-py3
RUN pip install --no-cache-dir vllm==0.15.1 \
    --extra-index-url https://wheels.vllm.ai/nightly/cu130 \
    && pip cache purge
```
**Pros:** CUDA 13.1 base for Blackwell + pinned stable vLLM (not nightly)
**Cons:** May need dependency fixes
**Risk:** Low — only 2-version jump, pinned to stable release with SM120 fixes
**Verdict:** Best path. Ansible role updated to support this.

### Option 4: Wait for NGC 26.02+
**Pros:** Zero risk
**Cons:** NGC just started catching up (v0.13.0). May ship v0.14.0 next but no guarantee.
**Verdict:** Worth checking in 1-2 weeks, but don't block on it.

## Recommendation → EXECUTED

**Option 3 (custom image)** executed. Pinned to v0.16.0 (upgraded from original v0.15.1 target). Steps:

1. ✅ Ansible vLLM role updated with `vllm_custom_build` flag + Dockerfile template
2. ✅ Test image built on Node 1 (`athanor/vllm:test`, 34.6 GB)
3. ✅ Version verified: `import vllm; print(vllm.__version__)` → 0.16.0
4. ✅ **Node 1 deployed and serving** — inference + tool calling verified
5. In progress: Deploy to Node 2
6. ✅ Regression test with Qwen3-32B-AWQ inference — PASSED
7. Pending: Download + test Qwen3.5-27B-FP8

### Deployment Issues Resolved

1. **NGC flash-attn ABI mismatch:** NGC ships `flash_attn_2_cuda.so` compiled against old PyTorch. vLLM v0.16.0 upgrades PyTorch, causing `ImportError: undefined symbol`. **Fix:** `pip uninstall -y flash-attn flash_attn` + `rm -f flash_attn_2_cuda*.so` in Dockerfile BEFORE vLLM install.

2. **NGC flashinfer-cubin version mismatch:** NGC ships `flashinfer-cubin` v0.6.0 (cu131 internal build). pip vLLM installs `flashinfer` v0.6.3. Version check fails at startup. **Fix:** `FLASHINFER_DISABLE_VERSION_CHECK=1` env var. Can't replace NGC cubin (cu131 Blackwell-specific).

3. **Sampler warmup OOM with max-num-seqs 128:** v0.16.0's V1 engine warms up the sampler with `max_num_seqs` dummy requests. On 16GB GPUs with 0.85 util, 128 OOMs during warmup. **Fix:** `--max-num-seqs 64` (sufficient for 8-agent workload).

4. **Sleep mode REST endpoints 404:** `--enable-sleep-mode` is accepted without error, but V1 engine does NOT register `/sleep`, `/wake_up`, `/is_sleeping` endpoints. These were V0 engine features. GPU orchestrator will need alternative mechanism.

This unblocks:
- NVFP4 quantization (65% faster on Blackwell)
- EAGLE-3 speculative decoding
- SageAttention2
- FlashInfer MLA (default in v0.15.0+)
- Qwen3.5 DeltaNet architecture support

**Does NOT unblock:**
- vLLM sleep mode REST endpoints (V1 engine doesn't expose them)

## Remaining

- **Qwen3.5-27B-FP8:** Available on HuggingFace. Need to download to NFS and test.
- **GPU orchestrator sleep/wake:** Needs alternative to REST endpoints (perhaps GPU memory monitoring or vLLM's internal auto-sleep).

## Sources

- [NGC vLLM Container Catalog](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/vllm)
- [NGC vLLM Release 26.01 Notes](https://docs.nvidia.com/deeplearning/frameworks/vllm-release-notes/rel-26-01.html) — incorrectly says v0.11.1
- [NVIDIA Developer Forum: NGC 26.01-py3](https://forums.developer.nvidia.com/t/new-ngc-vllm-container-image-vllm-26-01-py3/359213) — confirms v0.13.0
- [GitHub Issue #31424: NGC container ships outdated vLLM](https://github.com/vllm-project/vllm/issues/31424)
- [GitHub Issue #34296: v0.15.1 CUDA GPU detection failure](https://github.com/vllm-project/vllm/issues/34296)
- [vLLM v0.15.0 Release](https://github.com/vllm-project/vllm/releases/tag/v0.15.0)
- [vLLM v0.15.1 Release](https://github.com/vllm-project/vllm/releases/tag/v0.15.1)
- [vLLM Qwen3.5 Usage Guide](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html)
- [vLLM Blog: Qwen3-Next Hybrid Attention](https://blog.vllm.ai/2025/09/11/qwen3-next.html)
