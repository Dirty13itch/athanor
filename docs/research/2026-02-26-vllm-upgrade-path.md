# vLLM Upgrade Path: NGC Lag and Qwen3.5 Support

**Date:** 2026-02-26
**Context:** Session 19 identified vLLM v0.15.0+ as critical for Qwen3.5 DeltaNet. This research investigates the actual upgrade path.

## Current State

- **Running:** `nvcr.io/nvidia/vllm:25.12-py3` → vLLM v0.11.1
- **Latest NGC:** `nvcr.io/nvidia/vllm:26.01-py3` → still vLLM v0.11.1
- **NGC is 5 major versions behind upstream**

## NGC vLLM Container Timeline

| Tag | vLLM Version | Notes |
|-----|-------------|-------|
| 25.09-py3 | 0.11.1 | - |
| 25.10-py3 | 0.11.1 | - |
| 25.11-py3 | 0.11.1 | - |
| 25.12-py3 | 0.11.1 | **Current** |
| 26.01-py3 | 0.11.1 | Latest available |

NGC has shipped the same vLLM version for at least 5 months. No 26.02-py3 exists.

## Upstream vLLM Releases

| Version | Date | Key Features |
|---------|------|-------------|
| v0.14.0 | Jan 20, 2026 | Async scheduling default, gRPC, Qwen3-Next LoRA |
| v0.15.0 | Jan 29, 2026 | NVFP4 65% faster on Blackwell, EAGLE-3, new architectures |
| v0.15.1 | Feb 4, 2026 | Security fixes, RTX Blackwell GPU fixes |
| v0.16.0 | Feb 12-25, 2026 | PyTorch 2.10, WebSocket Realtime API, +30.8% throughput |

## Qwen3.5 Architecture Requirements

Qwen3.5 uses **Gated Delta Networks** (`Qwen3_5GatedDeltaNet`) — a hybrid architecture combining full attention at set intervals with linear attention via Gated DeltaNet. This is fundamentally different from standard transformers.

- vLLM announced "day-0 support" around Qwen3.5 release (Feb 16-24, 2026)
- vLLM Qwen3.5 recipes page recommends **nightly** builds
- Realistic minimum: v0.14.0+ for base GatedDeltaNet, v0.16.0 nightly for full support

## Upgrade Options

### Option 1: pip upgrade inside NGC container
**Approach:** `pip install -U vllm --extra-index-url https://wheels.vllm.ai/nightly/cu130`
**Pros:** Keeps NGC CUDA 13.1 base (required for sm_120 Blackwell)
**Cons:** Breaks validated stack, potential compatibility issues
**Risk:** Medium
**Source:** GitHub issue #31424 documents this workaround

### Option 2: Upstream vLLM Docker image
**Approach:** Use `vllm/vllm-openai:v0.15.1` or `vllm/vllm-openai:nightly`
**Pros:** Official upstream, well-tested
**Cons:** Ships CUDA 12, not CUDA 13. Blackwell sm_120 needs CUDA 13+.
**Risk:** High — GitHub issue #34296 confirms failure on GPUs requiring CUDA 13
**Verdict:** Not viable for our hardware

### Option 3: Custom image (NGC base + pip vLLM)
**Approach:** Build custom Dockerfile:
```dockerfile
FROM nvcr.io/nvidia/vllm:26.01-py3
RUN pip install -U vllm --extra-index-url https://wheels.vllm.ai/nightly/cu130
```
**Pros:** CUDA 13.1 base for Blackwell + latest vLLM
**Cons:** Untested combination, may need dependency fixes
**Risk:** Medium — but we already do this for ComfyUI successfully
**Verdict:** Most likely path

### Option 4: Wait for NGC 26.02+
**Pros:** Zero risk
**Cons:** NGC has shipped the same vLLM for 5 months. No evidence they'll update soon.
**Verdict:** Not a viable strategy

## Recommendation

**Option 3 (custom image)** is the way forward. Steps:

1. Build test image with NGC 26.01-py3 base + pip vLLM nightly
2. Test on a single 5070 Ti first (flex GPU zone)
3. Verify Qwen3.5-27B loads and generates
4. If stable, update Ansible vLLM role with custom Dockerfile
5. Roll out to all vLLM instances

This also unblocks:
- vLLM sleep mode (REST endpoints `/sleep`, `/is_sleeping`)
- NVFP4 quantization (65% faster on Blackwell)
- EAGLE-3 speculative decoding
- SageAttention2

## Blockers

- **Need to test Qwen3.5-27B model availability.** Is the AWQ quant available?
- **Need to verify cu130 wheel index has compatible nightly builds.**
- **Risk of breaking mixed GPU TP=4 on Node 1** (5070 Ti sm_120 + 4090 sm_89 together).

## Sources

- [NGC vLLM Container Catalog](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/vllm)
- [NGC vLLM Release 26.01 Notes](https://docs.nvidia.com/deeplearning/frameworks/vllm-release-notes/rel-26-01.html)
- [GitHub Issue #31424: NGC container ships outdated vLLM](https://github.com/vllm-project/vllm/issues/31424)
- [GitHub Issue #34296: v0.15.1 CUDA GPU detection failure](https://github.com/vllm-project/vllm/issues/34296)
- [vLLM v0.15.0 Release](https://github.com/vllm-project/vllm/releases/tag/v0.15.0)
- [vLLM Qwen3.5 Usage Guide](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html)
