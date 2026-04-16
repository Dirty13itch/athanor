# Inference Backend Comparison — March 2026

*Research via local Research Agent, 2026-03-14. Comprehensive depth.*

## SGLang vs vLLM for Qwen3.5

### Performance
- SGLang: ~16,200 tok/s on H100 (29% faster raw throughput vs vLLM's ~12,500)
- At 128 concurrent requests: SGLang beats vLLM by 17% with GPTQ-INT4
- Multi-turn conversational workloads: SGLang's RadixAttention adds 10-20% gain via automatic KV cache reuse across partial prefix overlaps

### RadixAttention vs PagedAttention
- **RadixAttention (SGLang)**: Radix tree for flexible prefix matching, automatic KV cache reuse across partial overlaps
- **PagedAttention (vLLM)**: Requires exact prefix matches for cache hits
- RadixAttention wins for multi-turn/agentic workflows with repeated prompt prefixes

### Qwen3.5 Specifics
- Both support Qwen3.5's Gated Delta Networks (GDN) hybrid attention architecture
- **vLLM**: New `qwen35_coder` tool parser (PR #35347) — fixes JSON malformation vs older `qwen3_coder`
- **SGLang**: Has `qwen3_coder` parser, `qwen25` deprecated → `qwen`
- **CRITICAL**: SGLang has NVFP4 NaN output issues on Blackwell sm_120 (issue #18954) — bf16 KV cache required
- vLLM has working NVFP4 on Blackwell, achieving 8,033 tok/s on RTX PRO 6000

### Verdict: Stick with vLLM
- Better Blackwell sm_120 support (our hardware)
- Working NVFP4 quantization
- New `qwen35_coder` tool parser (worth investigating vs our current `qwen3_xml`)
- Larger community, more mature ecosystem
- SGLang is worth revisiting when Blackwell NVFP4 issues are fixed

## llama.cpp for Lightweight Inference

### Qwen3.5-9B on 16GB GPU (5060 Ti)
- Qwen3.5-9B-UD-Q4_K_XL GGUF: fits in 10.6GB VRAM on 16GB GPU
- Qwen3.5-35B Q3_K_S: fits in 15.7GB with 256K context
- Performance: 119-124 tok/s for 35B models (on high-end hardware)

### Use Cases for Athanor
- DEV .189 has 5060 Ti 16GB — currently running embedding + reranker (4.8GB)
- Could co-host Qwen3.5-9B GGUF for lightweight tasks (autocomplete, quick queries)
- llama.cpp server supports OpenAI-compatible API

## Action Items

1. **Check vLLM PR #35347** — is `qwen35_coder` parser in our nightly? Better than `qwen3_xml`?
2. **Test Qwen3.5-9B GGUF on DEV** — would give us a 3rd inference endpoint for simple tasks
3. **Monitor SGLang Blackwell fixes** — track issue #18954 for NVFP4 NaN resolution
4. **Benchmark opportunity**: When SGLang fixes Blackwell, run head-to-head on our actual workloads

## Sources
- https://blog.premai.io/vllm-vs-sglang-vs-lmdeploy-fastest-llm-inference-engine-in-2026/
- https://www.runpod.io/blog/sglang-vs-vllm-kv-cache
- https://docs.sglang.io/basic_usage/qwen3_5.html
- https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html
- https://github.com/sgl-project/sglang/issues/18954
- https://github.com/vllm-project/vllm/pull/35347
- https://github.com/willbnu/Qwen-3.5-16G-Vram-Local
- https://joshua8.ai/llm-inference-benchmark/

Last updated: 2026-03-14
