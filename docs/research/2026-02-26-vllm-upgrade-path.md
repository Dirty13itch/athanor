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
5. ✅ **Node 2 deployed and serving** — Qwen3-14B FP16, inference + tool calling verified
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

## Qwen3.5 Upgrade → NODE 2 COMPLETE

**Date:** 2026-02-26 (Session 36-37)

### vLLM v0.17.0 Status (researched)

v0.17.0 does NOT exist yet as a stable release. Expected ~March 10, 2026 based on biweekly cadence. 537 commits on main since v0.16.0 branch cut. The `qwen3_5` model type was added in PR #34110 (merged Feb 9, 2026, one day after v0.16.0 branch cut).

### Final Upgrade Path: Custom NGC + Nightly vLLM

The upstream `vllm/vllm-openai:qwen3_5-cu130` image was tried but abandoned in favor of the existing custom build (NGC 26.01-py3 base + nightly vLLM pip install). The custom build already had both Qwen3.5 patches applied:
1. **RMSNormGated activation** (PR #35423) — present in nightly
2. **transformers rope_utils set()** — present in nightly

### FP8 vs AWQ Decision

- **FP8 (28.43 GiB):** Model loads on 5090 (32 GiB), but **OOMs during multimodal encoder profiling.** Even with `--language-model-only`, FP8 left only ~3 GiB headroom which was insufficient for KV cache initialization. Abandoned for single-GPU.
- **AWQ (~21 GiB):** Fits comfortably on 5090. 6.78 GiB available for KV cache (27,440 tokens). 31.7/32.6 GiB total usage at 0.90 util.
- **Architecture decision:** Node 2 (1x 5090) → AWQ. Node 1 (4x 5070 Ti TP=4) → FP8 (7 GiB/GPU).

### Key Discovery: `--language-model-only` Flag

This flag was incorrectly marked as "DOES NOT EXIST" in earlier sessions (tested against v0.16.0 stable). It exists in the nightly (0.16.1rc1.dev32) as part of `MultiModalConfig`:
- **Without it:** vLLM profiles the VLM encoder with 229K dummy tokens → exceeds 131K max seq len → crash
- **With it:** Sets all multimodal modality limits to 0, runs in text-only mode. Vision encoder weights still loaded but never profiled or used.

### Key Discovery: `qwen3_xml` Tool Parser

Qwen3.5 uses XML-style tool calls (`<tool_call><function=name><parameter=arg>value</parameter></tool_call>`), NOT hermes JSON format. The `hermes` parser silently fails — model generates correct output but parser doesn't match it.
- **Correct:** `--tool-call-parser qwen3_xml`
- **Wrong:** `--tool-call-parser hermes` (works for Qwen3, not Qwen3.5)

### Deployment Status

| Node | Model | Quant | VRAM | Status |
|------|-------|-------|------|--------|
| Node 2 (5090) | Qwen3.5-27B-AWQ | AWQ INT4 | 31.7/32.6 GiB | **LIVE** |
| Node 1 (4x 5070 Ti) | Qwen3-32B-AWQ | AWQ INT4 | ~19 GiB TP=4 | Stable, upgrade pending |

### Remaining Steps

- **Node 1 upgrade to Qwen3.5-27B-FP8** — Config ready in Ansible. Needs image build + deploy. Deferred until Node 2 proves stable.
- **GPU orchestrator sleep/wake:** V1 engine doesn't expose REST endpoints. Needs alternative mechanism.
- **Agent framework compatibility:** Verify all 8 agents work correctly with Qwen3.5 output format (thinking mode, XML tool calls) via Node 2.
- **LiteLLM `reasoning` alias:** Update after Node 1 upgrade.
- **Docker image cleanup:** 6 intermediate images removed from Node 2. Only `athanor/vllm:qwen35` (35 GB) + NGC base remain.

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
