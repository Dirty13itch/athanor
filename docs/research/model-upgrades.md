# Model Upgrade Research (2026-03-19)

## 1. Qwen3.5-122B-A10B-FP8 on FOUNDRY TP=4

**Verdict: NOT FEASIBLE with current hardware.**

- FP8: ~234GB — exceeds total cluster VRAM
- Q4_K_M: ~70GB — fits 5-GPU (88GB) but leaves no room for KV cache
- TP=4 on 5070 Tis (64GB): cannot fit even Q4
- Current Qwen3.5-27B-FP8 (all params active, 72.4% SWE-bench) is optimal for 64GB TP=4
- Would need FOUNDRY GPU upgrade (4x 5090 = 128GB) or DGX Spark

## 2. Huihui-Qwen3.5-35B-A3B-abliterated on WORKSHOP

**Verdict: VIABLE — direct drop-in replacement for WORKSHOP vLLM.**

- Same architecture as current Qwen3.5-35B-A3B-AWQ (256 experts, 3B active)
- Abliteration removes safety refusals without RLHF degradation
- Same VRAM: fits RTX 5090 32GB easily
- Better than JOSIEFIED-Qwen3-8B (8B vs 35B with 3B active = more capable)
- Would replace both: WORKSHOP vLLM worker AND JOSIEFIED uncensored
- HuggingFace: huihui-ai/Huihui-Qwen3.5-35B-A3B-abliterated
- Ollama: huihui_ai/qwen3.5-abliterated:35b
- AWQ version needed for vLLM: needs quantizing or find pre-quantized

**Action:** Pull Ollama version for quick test, then find/create AWQ quant for vLLM deployment.

## Sources
- https://huggingface.co/huihui-ai/Huihui-Qwen3.5-35B-A3B-abliterated
- https://apxml.com/models/qwen35-35b-a3b
- https://forums.developer.nvidia.com/t/qwen3-5-122b-a10b-nvfp4-quantized-for-dgx-spark
