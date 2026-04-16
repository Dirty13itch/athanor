# Qwen3.5 Model Landscape — March 2026

*Research via local Research Agent, 2026-03-14. Comprehensive depth.*

## Key Findings

### Qwen3.5 Family (Available Now)
| Model | Architecture | Active Params | Total Params | VRAM AWQ 4-bit |
|-------|-------------|---------------|--------------|----------------|
| Qwen3.5-27B | Dense | 27B | 27B | ~14GB |
| Qwen3.5-35B-A3B | MoE | 3B | 35B | ~21GB |
| Qwen3.5-122B-A10B | MoE | 10B | 122B | ~74GB |
| Qwen3.5-397B-A17B | MoE (flagship) | 17B | 397B | ~200GB+ |

### Qwen3-Coder-Next (Exists!)
- **Qwen3-Coder-Next-80B-A3B** — coding-specialized MoE, 3B active, 256K context
- Released February 2026, built on Qwen3-Next-80B-A3B base
- AWQ 4-bit: ~45GB VRAM — too tight for TP=4 (4x16GB = 64GB) with context headroom
- Q3_K_XL: ~44GB at 256K context — borderline for TP=4, workable with reduced context
- Available from: `bullpoint/Qwen3-Coder-Next-AWQ-4bit`, `cyankiwi/Qwen3-Next-80B-A3B-Instruct-AWQ-4bit`

### Quantization Providers
| Provider | Format | Quality (KLD) | Best For |
|----------|--------|---------------|----------|
| cyankiwi | AWQ 4-bit | ~3% ppl degradation | vLLM deployment |
| Qwen-team | FP8 | near-lossless | FP8-capable hardware |
| Unsloth | Dynamic GGUF | 0.4097 KLD (Q4_K_XL) | llama.cpp, best quality per bit |
| bartowski | GGUF | 0.4681 KLD (Q4_K_M) | llama.cpp, traditional |

### NVFP4 vs FP8 vs AWQ
- NVFP4: best prompt processing (4758.9 t/s) but similar generation speed
- FP8: near-lossless quality, requires FP8 hardware
- AWQ 4-bit: ~3% ppl degradation, most widely compatible

## Recommendations for Athanor

1. **Keep current setup** — Qwen3.5-27B-FP8 on TP=4 is optimal for reasoning quality
2. **Coder slot**: Qwen3.5-35B-A3B-AWQ-4bit is the right model for single 4090
3. **Future upgrade path**: Qwen3-Coder-Next-80B-A3B Q3_K_XL on TP=4 (~44GB fits in 64GB) if coding quality needs exceed current model
4. **Monitor**: Qwen3.5-122B-A10B as potential coordinator upgrade (would need TP=4 + offloading)

## Sources
- https://huggingface.co/Qwen/Qwen3-Coder-Next-FP8
- https://insiderllm.com/guides/qwen-3-5-local-guide/
- https://huggingface.co/cyankiwi/Qwen3-Next-80B-A3B-Instruct-AWQ-4bit
- https://www.hardware-corner.net/qwen3-coder-next-hardware-requirements/
- https://forums.developer.nvidia.com/t/qwen3-next-awq-4bit-vs-fp8-vs-nvfp4-on-single-spark/361300
- https://unsloth.ai/docs/models/qwen3.5/gguf-benchmarks

Last updated: 2026-03-14
