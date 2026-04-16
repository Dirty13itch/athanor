# vLLM Baseline Throughput Benchmarks

**Date:** 2026-03-08
**Purpose:** Establish baseline inference throughput numbers for FOUNDRY and WORKSHOP vLLM instances.

## Test Parameters

- **Prompt:** "Explain quantum entanglement in three sentences."
- **Max tokens:** 200 (includes thinking tokens for Qwen3/3.5)
- **Temperature:** 0.7
- **Runs:** 5 per test (streaming + non-streaming)
- **Warmup:** 1 request before timing

---

## FOUNDRY — Qwen3-32B-AWQ

| Parameter | Value |
|-----------|-------|
| Model | `/models/Qwen3-32B-AWQ` |
| Quantization | AWQ (explicit `--quantization awq`) |
| GPUs | 2x RTX 5070 Ti (TP=2) |
| VRAM per GPU | ~14.9 GB / 16.3 GB used |
| Port | 8000 |
| vLLM flags | `--enforce-eager`, `--kv-cache-dtype fp8_e5m2`, `--max-model-len 8192`, `--gpu-memory-utilization 0.85`, `--tool-call-parser hermes`, `--enable-prefix-caching`, `--swap-space 16` |
| Container | `vllm-reasoning` |

### Results

#### Streaming (TTFT measurement)

| Run | TTFT (ms) | Total (ms) | Chunks |
|-----|-----------|------------|--------|
| 1 | 646 | 7,671 | 200 |
| 2 | 670 | 7,821 | 200 |
| 3 | 664 | 7,745 | 200 |
| 4 | 662 | 7,772 | 200 |
| 5 | 651 | 7,551 | 200 |

#### Non-streaming (accurate token counts)

| Run | Total (ms) | Prompt Tokens | Completion Tokens | E2E TPS |
|-----|------------|---------------|-------------------|---------|
| 1 | 7,561 | 18 | 200 | 26.5 |
| 2 | 7,579 | 18 | 200 | 26.4 |
| 3 | 7,766 | 18 | 200 | 25.8 |
| 4 | 7,747 | 18 | 200 | 25.8 |
| 5 | 7,569 | 18 | 200 | 26.4 |

### Summary

| Metric | Value |
|--------|-------|
| **Avg TTFT** | **659 ms** (min 646, max 670) |
| **Avg Total (streaming)** | 7,712 ms |
| **Avg Total (non-streaming)** | 7,644 ms |
| **Avg Completion Tokens** | 200 |
| **Avg End-to-End TPS** | **26.2 t/s** |
| **Decode-only TPS** | **~28.4 t/s** (200 tokens in ~7,053ms decode phase) |

### Notes

- All 200 completion tokens were consumed by `<think>` reasoning tokens at this token budget. Qwen3 always thinks first without `/no_think` instruction.
- TTFT is very consistent (646-670ms range, ~24ms spread) — indicates stable prefill performance.
- E2E TPS is stable at 25.8-26.5 across all runs — no thermal throttling or memory pressure variance.
- Using `--enforce-eager` (no CUDA graphs) — TPS would likely improve with CUDA graph compilation.
- Using `--kv-cache-dtype fp8_e5m2` — acceptable for Qwen3 (non-GDN architecture), but would corrupt Qwen3.5.
- `--tool-call-parser hermes` — correct for Qwen3 (Qwen3.5 needs `qwen3_coder` or `qwen3_xml`).

---

## WORKSHOP — Qwen3.5-35B-A3B-AWQ-4bit

| Parameter | Value |
|-----------|-------|
| Model | `/models/Qwen3.5-35B-A3B-AWQ-4bit` |
| Quantization | compressed-tensors (Marlin WNA16, 4-bit, group_size=32) |
| GPU | RTX 5090 (32 GB) |
| Port | 8000 (host networking, no port mapping) |
| vLLM version | v0.16.1rc1.dev32 (nightly) |
| vLLM flags | `--gpu-memory-utilization 0.90`, `--kv-cache-dtype auto`, `--max-model-len 32768`, `--enable-prefix-caching`, `--tool-call-parser qwen3_xml`, `--safetensors-load-strategy eager` |
| Container | `vllm-node2` |

### Results

**BENCHMARK FAILED — Triton autotuner OOM on every cold start.**

The container loads the model successfully (~22.5s for weights), but crashes with `RuntimeError: Triton Error [CUDA]: out of memory` on the first inference request. This happens consistently across container restarts.

### Root Cause

1. `--gpu-memory-utilization 0.90` leaves only ~3.2 GB free on the 32 GB 5090.
2. Triton autotuner for MoE kernels (Marlin WNA16) needs temporary workspace during first-run compilation.
3. No Triton cache volume mount (`~/.cache/triton` not persisted) — so every restart triggers fresh autotuning.
4. The autotuner's temporary buffers exceed the ~3.2 GB headroom, causing OOM.

### Recommended Fixes

1. **Mount Triton cache:** Add `-v /home/shaun/.cache/triton:/root/.cache/triton` to persist compiled kernels across restarts.
2. **Reduce GPU memory utilization:** Lower to `--gpu-memory-utilization 0.85` to give Triton ~4.9 GB headroom.
3. **Both together** is ideal — cache prevents recompilation, lower utilization prevents OOM if cache misses.

---

## Comparison & Analysis

| Metric | FOUNDRY (Qwen3-32B) | WORKSHOP (Qwen3.5-35B-A3B) |
|--------|---------------------|-----------------------------|
| Architecture | Dense 32B | MoE 35B (3B active) |
| GPUs | 2x 5070 Ti (TP=2) | 1x 5090 |
| VRAM Used | ~30 GB total | OOM (needs tuning) |
| TTFT | 659 ms avg | N/A (OOM) |
| E2E TPS | 26.2 t/s | N/A (OOM) |
| Status | Stable, production | Broken, needs config fix |

### Expected WORKSHOP Performance (when fixed)

Based on the hardware:
- RTX 5090 has ~1.8 PFLOPS FP4 / ~209 TFLOPS FP16 with 1.8 TB/s memory bandwidth.
- MoE with only 3B active parameters should have very fast decode.
- Expected decode TPS: 80-120+ t/s (MoE active parameter count is 10x smaller than FOUNDRY's dense 32B).
- Expected TTFT: <200ms (3B active params for prefill).
- This would make WORKSHOP the faster inference node once the OOM is resolved.

---

## Action Items

1. [ ] Fix WORKSHOP vllm-node2: add Triton cache mount + reduce GPU utilization to 0.85
2. [ ] Re-run WORKSHOP benchmark after fix
3. [ ] Consider enabling CUDA graphs on FOUNDRY (remove `--enforce-eager`) for potential TPS improvement
4. [ ] Test with `/no_think` instruction to measure non-thinking token generation
5. [ ] Run concurrent load test (multiple simultaneous requests) to measure throughput under load
