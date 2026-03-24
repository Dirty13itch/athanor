# vLLM v0.17.x Upgrade Assessment

**Date:** 2026-03-15
**Context:** Currently running vLLM nightly v0.16.1rc1.dev32 via custom NGC image (`athanor/vllm:qwen35`). Evaluating upgrade to stable v0.17.1.
**Prior Research:** [2026-02-26-vllm-upgrade-path.md](2026-02-26-vllm-upgrade-path.md), [2026-03-08-vllm-baseline-benchmarks.md](2026-03-08-vllm-baseline-benchmarks.md)

---

## Release Timeline

| Version | Release Date | Notes |
|---------|-------------|-------|
| v0.16.0 | 2026-02-26 | Current stable base; our nightly is dev32 on top of this |
| **v0.17.0** | **2026-03-07** | Major release, 699 commits, 272 contributors |
| **v0.17.1** | **2026-03-11** | Patch: Qwen3.5 SSM cache fix, MoE fixes |
| NGC 26.02 | ~2026-03-01 | Ships vLLM **v0.15.1** (still 2 versions behind) |

Sources: [PyPI vllm](https://pypi.org/project/vllm/), [GitHub v0.17.0](https://github.com/vllm-project/vllm/releases/tag/v0.17.0), [GitHub v0.17.1](https://github.com/vllm-project/vllm/releases/tag/v0.17.1), [NGC 26.02 Release Notes](https://docs.nvidia.com/deeplearning/frameworks/vllm-release-notes/rel-26-02.html)

---

## Question-by-Question Analysis

### 1. Is v0.17.1 released and stable?

**Yes.** v0.17.1 was released on PyPI on March 11, 2026 (4 days ago). It is a patch on v0.17.0 (March 7).

However, v0.17.0 is a **major release** with PyTorch 2.10.0 upgrade (breaking change for dependencies). The v0.17.1 patch focuses on MoE backend stability and Qwen3.5 memory fixes. This is *young* -- only 4 days old for v0.17.1, 8 days for v0.17.0.

**Risk assessment:** Medium. The PyTorch 2.10 upgrade is the biggest concern -- it changes the entire CUDA/dependency chain.

### 2. Does v0.17.1 include `--language-model-only` in stable?

**Yes.** The v0.17.0 release notes explicitly list `--language-model-only` as a new feature "for hybrid models." The [official Qwen3.5 Usage Guide](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html) documents it as a recommended flag. This was previously nightly-only (our v0.16.1rc1.dev32 had it, v0.16.0 stable did not).

**Impact:** We no longer need nightly builds for this flag. This was the primary reason we were on nightly.

### 3. Does v0.17.1 have working sleep mode REST endpoints?

**Yes, with caveats.** Sleep mode now works on both V0 and V1 engines. The REST endpoints are:
- `POST /sleep?level=1` (or `level=2`)
- `POST /wake_up`
- `GET /is_sleeping`

**Critical requirement:** `VLLM_SERVER_DEV_MODE=1` environment variable must be set to enable these dev endpoints. Without it, the endpoints are not registered.

**What changed from our v0.16 experience:** In v0.16.0 stable, sleep mode endpoints returned 404 on V1 engine. The V1 engine sleep support was added in the v0.17.0 timeframe. Additionally, PR #16536 added proper 503 error handling when requests hit a sleeping model (previously caused CUDA crashes).

**Limitations:**
- Sleep level 1 offloads weights to CPU RAM -- requires sufficient CPU memory (our models are 21-28 GiB)
- Sleep level 2 discards everything -- full reload needed on wake
- Wake from sleep is 61-88% faster than cold start (no warmup needed)

Source: [vLLM Sleep Mode docs](https://docs.vllm.ai/en/latest/features/sleep_mode/), [vLLM Blog: Sleep Mode](https://blog.vllm.ai/2025/10/26/sleep-mode.html)

### 4. Does v0.17.x support Qwen3.5 multimodal without `--language-model-only`?

**Partially.** The v0.17.0 release includes "full support for the Qwen3.5 model family (#34110) featuring GDN, with FP8 quantization, MTP speculative decoding, and reasoning parser support."

However, the Qwen3.5 Usage Guide still recommends `--language-model-only` for text-only deployments to "skip loading the vision encoder and free up memory for KV cache." The VLM encoder profiling issue (229K tokens exceeding max seq len) may still occur without this flag on memory-constrained GPUs.

**Recommendation:** Continue using `--language-model-only` on all our nodes. We have no multimodal use case for the coordinator/worker models, and the VRAM savings are significant.

### 5. Breaking changes from v0.16.x to v0.17.x affecting our setup

#### 5a. PyTorch 2.10.0 Upgrade (CRITICAL)

This is the biggest breaking change. v0.17.0 upgrades from PyTorch 2.9.x to 2.10.0. This affects:
- **Our custom image build process:** NGC 26.02 ships PyTorch 2.11.0a0 (CUDA 13.1.1), which is actually *ahead* of upstream v0.17.0's PyTorch 2.10.0. pip-installing vLLM v0.17.1 on top of NGC 26.02 may cause version conflicts.
- **CUDA compatibility:** v0.17.0 ships with CUDA 12.9 wheels by default. Our Blackwell GPUs (sm_120) need CUDA 13.x. We need cu130 wheels.
- **Installation:** New method: `uv pip install vllm --torch-backend=auto` or specific cu130 index.

**Known issue:** CUBLAS_STATUS_INVALID_VALUE error on CUDA 12.9+ due to library mismatch (documented in v0.17.0 release notes).

#### 5b. Our Flags -- Compatibility Check

| Flag | Status in v0.17.1 | Notes |
|------|-------------------|-------|
| `--tool-call-parser qwen3_xml` | **SAFE** | Not deprecated. Still recommended for Qwen3.5. |
| `--enforce-eager` | **SAFE** | Still supported. May be removable (see Q6). |
| `--kv-cache-dtype auto` | **SAFE** | No changes. Still needed for Qwen3.5 GDN layers. |
| `--enable-auto-tool-choice` | **SAFE** | No deprecation found. |
| `--language-model-only` | **NOW STABLE** | Promoted from nightly to stable. |
| `--enable-prefix-caching` | **SAFE** | No changes. |
| `--gpu-memory-utilization` | **SAFE** | No changes. |

#### 5c. Deprecations/Removals in v0.17.0

These should NOT affect us:
- Removed: BitBlas quantization, Marlin 24, DeepSpeedFp8, RTN quantization
- Removed: `vllm:time_per_output_token_seconds` metric (use `vllm:inter_token_latency_seconds`)
- Removed: `VLLM_ALL2ALL_BACKEND` env var
- Removed: deprecated `reasoning_content` message field
- Removed: xformers backend (V0-only, we use V1)
- Deprecated: HQQ quantization
- Changed: KV load failure policy default from "recompute" to "fail"
- New: `AttentionConfig` replaces `VLLM_ATTENTION_BACKEND` env var

**Action required:** Check if we use `VLLM_ATTENTION_BACKEND` anywhere (unlikely but verify). Check Grafana dashboards for the removed metric name.

### 6. Better Blackwell support in v0.17.x?

**Yes, meaningful improvements:**

- **SM120 FP8 GEMM optimization** -- improved inference speed on RTX Blackwell
- **SM100 FMHA FP8 prefill for MLA** -- datacenter Blackwell
- **SM100/SM120 MXFP4 blockscaled grouped MM and quant kernels** -- enables MXFP4 quantization
- **FlashInfer DeepGEMM** integration
- **FlashAttention 4** backend (#32974) -- next-generation attention performance
- **FlashInfer cuDNN backend** for Qwen3 VL ViT
- **FlashInfer Sparse MLA backend**

#### DeltaNet CUDA Graph Fix

PR #35256 fixed the dtype mismatch in `RMSNormGated.forward_native()` during `torch.compile` that caused crashes without `--enforce-eager`. This fix was merged March 1, 2026 (before v0.17.0 branch cut on March 7), so it **should be included in v0.17.0**.

**Implication:** We may be able to **remove `--enforce-eager`** and enable CUDA graphs for Qwen3.5, which could yield a ~20-30% performance improvement. However, this needs careful testing:
- Issue #35743 reports CUDA graph capture still fails for Qwen3.5-27B AWQ 4bit on RTX 5060 Ti (early March 2026, nightly)
- The v0.17.1 fix "Zero freed SSM cache blocks on GPU (#35219)" for Mamba/Qwen3.5 may address related memory corruption

**Recommendation:** Test `--enforce-eager` removal on DEV first, then WORKSHOP, before FOUNDRY.

### 7. Qwen3.5-specific fixes and improvements

| Fix | Version | PR | Impact |
|-----|---------|----|----|
| Full Qwen3.5 model family support | v0.17.0 | #34110 | GDN, FP8, MTP, reasoning parser |
| `--language-model-only` in stable | v0.17.0 | -- | No more nightly requirement |
| DeltaNet RMSNormGated dtype fix | v0.17.0 | #35256 | May remove `--enforce-eager` |
| Zero freed SSM cache blocks on GPU | v0.17.1 | #35219 | Memory safety for Mamba/Qwen3.5 |
| MTP (Multi-Token Prediction) support | v0.17.0 | -- | Speculative decoding for Qwen3.5 |
| `--performance-mode` flag | v0.17.0 | #34936 | Simplified tuning |

**Known Qwen3.5 issue on v0.17.x:** Issue #36773 reports Qwen3.5-35B-A3B producing random output on B200 (datacenter Blackwell) with FP8. Confirmed still broken in v0.17.1. This is FP8 on B200 specifically -- our AWQ on RTX Blackwell (sm_120) is a different code path and likely unaffected.

---

## Upgrade Path Options

### Option A: pip upgrade v0.17.1 on NGC 26.02 base (RECOMMENDED)

```dockerfile
FROM nvcr.io/nvidia/vllm:26.02-py3
# NGC 26.02: CUDA 13.1.1, PyTorch 2.11.0a0, vLLM 0.15.1
RUN pip uninstall -y flash-attn flash_attn && \
    rm -f /usr/local/lib/python3.12/dist-packages/flash_attn_2_cuda*.so && \
    pip install --no-cache-dir vllm==0.17.1 \
    --extra-index-url https://wheels.vllm.ai/nightly/cu130 && \
    pip cache purge
ENV FLASHINFER_DISABLE_VERSION_CHECK=1
```

**Pros:**
- NGC 26.02 has newer CUDA 13.1.1 base (vs 26.01's 13.1.0)
- Stable v0.17.1 instead of nightly
- `--language-model-only` now stable
- Sleep mode REST endpoints available
- DeltaNet dtype fix included
- SSM cache zeroing fix included

**Cons:**
- PyTorch version mismatch: NGC ships 2.11.0a0, vLLM v0.17.1 expects 2.10.0. May need `--no-deps` or careful dependency management.
- Young release (4 days old for v0.17.1)
- flash-attn removal still needed (same as current)
- FlashInfer version check still needed (same as current)

**Risk:** Medium. PyTorch mismatch is the primary concern.

### Option B: pip upgrade v0.17.1 on NGC 26.01 base (SAFE)

Same as current approach but pin to v0.17.1 instead of nightly:
```dockerfile
FROM nvcr.io/nvidia/vllm:26.01-py3
# NGC 26.01: CUDA 13.1.0, PyTorch 2.9.x, vLLM 0.13.0
RUN pip uninstall -y flash-attn flash_attn && \
    rm -f /usr/local/lib/python3.12/dist-packages/flash_attn_2_cuda*.so && \
    pip install --no-cache-dir vllm==0.17.1 \
    --extra-index-url https://wheels.vllm.ai/nightly/cu130 && \
    pip cache purge
ENV FLASHINFER_DISABLE_VERSION_CHECK=1
```

**Pros:** Known-good base image. Minimal change from current approach.
**Cons:** Larger version jump (0.13.0 -> 0.17.1). PyTorch 2.9 in base vs 2.10 in vLLM -- bigger mismatch than Option A.
**Risk:** Medium. We already jumped from 0.13.0 to nightly successfully on this base.

### Option C: Wait for NGC 26.03

NGC 26.02 ships v0.15.1. NGC 26.03 might ship v0.16.0 or v0.17.0. NVIDIA is catching up but still 2 versions behind.

**Pros:** Validated stack, no hacks.
**Cons:** Unknown timeline. May still not have v0.17.x.
**Risk:** Low risk, high delay.

### Option D: Stay on nightly v0.16.1rc1.dev32

Our current state. Working, tested, deployed.

**Pros:** Zero risk. Everything works.
**Cons:** Missing v0.17.1 fixes (SSM cache zeroing, MoE fixes). No sleep mode endpoints. Still on nightly (not reproducible builds). DeltaNet dtype fix may be missing (our nightly predates PR #35256 merge on March 1).
**Risk:** None (status quo).

---

## Recommendation

**Option B (NGC 26.01 + v0.17.1)** is the best immediate path, tested on DEV first.

Rationale:
1. NGC 26.01 base is already our known-good foundation
2. We already successfully jumped from v0.13.0 to nightly on this base -- jumping to v0.17.1 stable is lower risk than staying on unreproducible nightly
3. v0.17.1 gives us: stable `--language-model-only`, sleep mode endpoints, DeltaNet dtype fix, SSM cache zeroing
4. Avoids the NGC 26.02 PyTorch 2.11 mismatch uncertainty

**Testing plan:**
1. Build `athanor/vllm:v0.17.1` image on DEV
2. Test on DEV with 5060Ti (smallest GPU, most memory-constrained)
3. Verify: model loads, inference works, tool calling works, `--language-model-only` works
4. Test sleep mode endpoints with `VLLM_SERVER_DEV_MODE=1`
5. Test removing `--enforce-eager` (DeltaNet CUDA graph fix)
6. If all pass: deploy to WORKSHOP, then FOUNDRY (with approval)

**Timeline:** Wait 1-2 weeks for v0.17.1 to mature (more community testing). Target upgrade: week of March 24-28, 2026.

---

## Summary Table

| Question | Answer | Confidence |
|----------|--------|------------|
| v0.17.1 released and stable? | Yes (March 11, 2026) | High |
| `--language-model-only` in stable? | Yes, new in v0.17.0 | High |
| Sleep mode REST endpoints working? | Yes, with `VLLM_SERVER_DEV_MODE=1` | High |
| Qwen3.5 VLM without `--language-model-only`? | Possible but not recommended for us | Medium |
| Breaking changes affecting us? | PyTorch 2.10 upgrade; some metric/env removals | High |
| Better Blackwell support? | Yes: SM120 FP8 GEMM, FlashAttention 4, MXFP4 | High |
| DeltaNet CUDA graph fix? | PR #35256 merged, likely in v0.17.0. Needs testing. | Medium |
| `--enforce-eager` removable? | Maybe. Fix exists but CUDA graph capture still fails for some configs. | Low |
| `qwen3_xml` parser safe? | Yes, not deprecated | High |

---

## Sources

- [PyPI vllm](https://pypi.org/project/vllm/)
- [GitHub v0.17.0 Release](https://github.com/vllm-project/vllm/releases/tag/v0.17.0)
- [GitHub v0.17.1 Release](https://github.com/vllm-project/vllm/releases/tag/v0.17.1)
- [vLLM Qwen3.5 Usage Guide](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html)
- [vLLM Sleep Mode Docs](https://docs.vllm.ai/en/latest/features/sleep_mode/)
- [vLLM Blog: Zero-Reload Model Switching](https://blog.vllm.ai/2025/10/26/sleep-mode.html)
- [NGC 26.02 Release Notes](https://docs.nvidia.com/deeplearning/frameworks/vllm-release-notes/rel-26-02.html)
- [GitHub Issue #35238: DeltaNet dtype mismatch](https://github.com/vllm-project/vllm/issues/35238)
- [GitHub Issue #35743: Qwen3.5 CUDA graph capture failure](https://github.com/vllm-project/vllm/issues/35743)
- [GitHub Issue #36773: Qwen3.5-35B-A3B random output on B200](https://github.com/vllm-project/vllm/issues/36773)
- [GitHub PR #16536: Sleep mode error handling](https://github.com/vllm-project/vllm/pull/16536)
- [GitHub production-stack Issue #391: V1 Sleep & Wake_up](https://github.com/vllm-project/production-stack/issues/391)
- [NVIDIA Developer Forums: NGC 26.01](https://forums.developer.nvidia.com/t/new-ngc-vllm-container-image-vllm-26-01-py3/359213)
- [NVIDIA Developer Forums: vLLM 0.17.0 MXFP4 on DGX Spark](https://forums.developer.nvidia.com/t/vllm-0-17-0-mxfp4-patches-for-dgx-spark-qwen3-5-35b-a3b-70-tok-s-gpt-oss-120b-80-tok-s-tp-2/362824)

Last updated: 2026-03-15
