# AI Inference Engine

> Historical note: archived research retained for ADR-005 decision history. Current inference deployment and routing truth lives in the model-deployment registry, topology, and generated reports.

**Date:** 2026-02-15
**Status:** Complete — recommendation ready
**Supports:** ADR-005 (AI Inference Engine)
**Depends on:** ADR-004 (Node Roles + Hardware Allocation)

---

## The Question

What inference engine(s) should Athanor use to serve LLMs across its hardware?

---

## Hardware Constraints (from ADR-004)

| Node | GPUs | VRAM | Parallelism | Architecture |
|------|------|------|-------------|--------------|
| Node 1 (Core) | 4x RTX 5070 Ti | 64 GB | Tensor parallel (identical GPUs) | Blackwell (sm_120) |
| Node 2 (Interface) | RTX 5090 + RTX 4090 | 32 + 24 GB | Independent (different GPUs) | Blackwell (sm_120) + Ada Lovelace (sm_89) |
| Cross-node | All 6 NVIDIA GPUs | 120 GB | Pipeline parallel via IB 56G | Mixed |

Key constraints:
- **No NVLink.** Consumer GPUs communicate via PCIe only. Node 1's EPYC platform provides PCIe 4.0 x16 per GPU (~32 GB/s per direction). Tensor parallelism works but won't scale as efficiently as datacenter NVLink setups.
- **Blackwell (sm_120) is new.** Standard releases of most inference engines don't support it yet. PyTorch sm_120 support is in nightly builds (2.9.0+cu128), not stable releases.
- **Heterogeneous Node 2.** The 5090 and 4090 are different architectures — they must run as separate inference instances, not tensor-parallel together.
- **Agents are the primary consumer.** Agents on Node 1 call the local vLLM API thousands of times. Latency matters. An OpenAI-compatible API is essential for agent framework compatibility.

---

## Candidates

### 1. vLLM

**GitHub:** 33k+ stars | **License:** Apache 2.0 | **Language:** Python/CUDA

vLLM is the most widely adopted open-source LLM serving framework. Key features:

- **PagedAttention** — memory-efficient KV cache management, reduces VRAM waste from fragmentation
- **Continuous batching** — serves multiple concurrent requests efficiently, critical for agent workloads
- **Tensor parallelism** — native support via `--tensor-parallel-size N`, uses NCCL for inter-GPU communication
- **Pipeline parallelism** — distribute model layers across nodes for models exceeding single-node VRAM
- **Multi-node** — Ray cluster coordination, NCCL over InfiniBand with `NCCL_IB_HCA=mlx5`
- **OpenAI-compatible API** — drop-in replacement for OpenAI's API, wide ecosystem compatibility
- **NVFP4 quantization** — native Blackwell 4-bit format, 1.6x throughput over BF16 with 2-4% quality loss
- **Docker support** — well-documented container deployment

**Blackwell (sm_120) status as of Feb 2026:**
- Standard pip installs do NOT work — pre-built wheels don't include sm_120
- Working setup requires: PyTorch 2.9.0+cu128 nightly, build vLLM from source, `TORCH_CUDA_ARCH_LIST="12.0"`, Flash Attention v2 (v3 triggers errors), FlashInfer backend instead of flash-attn
- Community-confirmed working: RTX 5090 running Qwen2.5-7B at 290+ tok/s with 31GB VRAM usage
- SymmMemCommunicator doesn't officially support sm_120 yet
- This is a build complexity issue, not a fundamental incompatibility. It will stabilize as PyTorch and CUDA mature.

**Multi-GPU tensor parallelism on consumer GPUs:**
- Works with `--tensor-parallel-size 4` for 4x identical GPUs
- PCIe 4.0 x16 inter-GPU bandwidth (~32 GB/s) is adequate for inference (not training)
- No NVLink means TP scaling is less efficient than datacenter, but inference activations are small relative to compute time
- Documented and tested on consumer RTX setups

**Multi-node InfiniBand:**
- Uses Ray for cluster coordination across nodes
- NCCL communicates via InfiniBand when configured: `NCCL_IB_HCA=mlx5`, `NCCL_DEBUG=TRACE` to verify
- Look for `[send] via NET/IB/GDRDMA` in NCCL logs to confirm IB+GPUDirect RDMA
- Pipeline parallelism (`--pipeline-parallel-size`) distributes layers across nodes
- Well-documented for enterprise; homelab setups less documented but technically identical

**Sources:**
- [vLLM parallelism docs](https://docs.vllm.ai/en/stable/serving/parallelism_scaling/)
- [vLLM RTX 5090 working setup guide](https://discuss.vllm.ai/t/vllm-on-rtx5090-working-gpu-setup-with-torch-2-9-0-cu128/1492)
- [vLLM distributed serving docs](https://docs.vllm.ai/en/v0.8.0/serving/distributed_serving.html)
- [RTX 5070 Ti NCCL issue report](https://github.com/vllm-project/vllm/issues/20282)
- [vLLM sm_120 support request](https://github.com/vllm-project/vllm/issues/13306)
- [NVFP4 MoE kernel sm_120 request](https://github.com/vllm-project/vllm/issues/31085)
- [vLLM on Debian 12 & RTX 5070 Ti guide](https://ligma.blog/post1/)
- [Private LLM Inference on Consumer Blackwell GPUs (arxiv)](https://arxiv.org/html/2601.09527v1)

---

### 2. SGLang

**GitHub:** 7.3k stars | **License:** Apache 2.0 | **Language:** Python/CUDA

SGLang is a high-performance serving framework from LMSYS (the LMSYS Chatbot Arena team). Key features:

- **RadixAttention** — prefix-aware KV cache sharing, ~10% throughput boost for multi-turn conversations with shared prefixes
- **Chunked pipeline parallelism** — >80% scaling efficiency up to PP4, 81% TTFT reduction for ultra-long prompts
- **Full parallelism matrix** — TP, PP, DP, EP (expert parallelism for MoE) — all composable
- **Continuous batching** — comparable to vLLM
- **OpenAI-compatible API** — same API surface as vLLM
- **NVFP4 support** — Release 25.10 includes Blackwell NVFP4

**Benchmark comparison with vLLM:**
- SGLang shows ~29% higher throughput in some benchmarks (16,215 vs 12,553 tok/s on H100)
- More stable per-token latency (4-21ms vs more variable)
- RadixAttention gives ~10% benefit for multi-turn conversations (agent workloads)
- vLLM has faster time-to-first-token (TTFT) and better scaling at very high concurrency (100+)
- SGLang serves ~1.5x request volume in some 2-GPU benchmarks

**Concerns for Athanor:**
- Smaller community — less homelab documentation, fewer Docker examples, fewer community-reported fixes
- Blackwell consumer GPU support status is unclear — most documentation targets datacenter GPUs
- Moving fast but less stable than vLLM — API changes, breaking updates
- Multi-node IB support exists (`NCCL_IB_DISABLE=0`) but less documented for consumer hardware

**Sources:**
- [SGLang pipeline parallelism blog](https://lmsys.org/blog/2026-01-15-chunked-pipeline/)
- [SGLang vs vLLM benchmark (Kanerika)](https://kanerika.com/blogs/sglang-vs-vllm/)
- [SGLang vs vLLM KV cache comparison (RunPod)](https://www.runpod.io/blog/sglang-vs-vllm-kv-cache)
- [vLLM vs SGLang H100 benchmark](https://rawlinson.ca/articles/vllm-vs-sglang-performance-benchmark-h100)
- [SGLang multi-node parallelism docs issue](https://github.com/sgl-project/sglang/issues/8164)
- [SGLang distributed execution (DeepWiki)](https://deepwiki.com/sgl-project/sglang/5-distributed-execution-strategies)

---

### 3. llama.cpp / ik_llama.cpp

**GitHub:** 75k+ stars (llama.cpp) | **License:** MIT | **Language:** C/C++/CUDA

llama.cpp is the original local inference engine. ik_llama.cpp is a performance-optimized fork with breakthrough multi-GPU support.

- **GGUF format** — widest model format support, most models available in GGUF
- **CPU+GPU hybrid** — can offload layers to CPU RAM when VRAM is insufficient (Node 1's 224 GB RAM is useful here)
- **Split-mode-graph (ik_llama.cpp)** — true tensor parallelism at the GGML graph level, 3-4x speedup over standard layer splitting
- **Simple to run** — single binary, no Python environment, no Ray cluster

**Why not for primary serving:**
- **No continuous batching** — serves one request at a time (or with limited concurrency). Fatal for a system where agents make concurrent calls.
- **No native OpenAI API** — needs a wrapper (llama-server, LiteLLM, etc.)
- **Blackwell workaround** — requires `GGML_CUDA_FORCE_CUBLAS=1` on RTX 5090 (custom kernels crash on sm_120)
- **No multi-node** — single machine only
- **Tensor parallelism is recent** — ik_llama.cpp's split-mode-graph is promising but from a fork, not mainline

**Appropriate use:** Quick model testing, CPU-offloaded inference for models that barely exceed VRAM, development on DEV machine.

**Sources:**
- [llama.cpp multi-GPU performance breakthrough](https://medium.com/@jagusztinl/llama-cpp-performance-breakthrough-for-multi-gpu-setups-04c83a66feb2)
- [Don't use llama.cpp for multi-GPU (Ahmad Osman)](https://www.ahmadosman.com/blog/do-not-use-llama-cpp-or-ollama-on-multi-gpus-setups-use-vllm-or-exllamav2/)
- [llama.cpp multi-GPU scaling discussion](https://github.com/ggml-org/llama.cpp/discussions/11236)

---

### 4. Ollama

**GitHub:** 120k+ stars | **License:** MIT

Ollama wraps llama.cpp in a user-friendly CLI and API.

- **Best UX** — `ollama run llama3` and you're chatting
- **Growing ecosystem** — Open WebUI, many integrations
- **NOT designed for multi-GPU tensor parallelism** — layers are split across GPUs (pipeline parallel), not tensor parallel
- **Inherits llama.cpp limitations** — no continuous batching, limited concurrency

**Why not for Athanor:** Node 1's 4-GPU tensor parallelism is the core architecture. Ollama can't do it. For a system serving agents, dashboard, and creative pipelines simultaneously, Ollama's single-request model is a non-starter.

**Appropriate use:** None in production. Could be useful for quick model pulls during development.

**Sources:**
- [Ollama multi-GPU guide](https://dasroot.net/posts/2025/12/ollama-multi-gpu-setup-larger-models/)
- [Multi-GPU comparison: vLLM vs llama.cpp vs Ollama](https://www.arsturn.com/blog/multi-gpu-showdown-benchmarking-vllm-llama-cpp-ollama-for-maximum-performance)

---

### 5. ExLlamaV2

**GitHub:** ~4k stars | **License:** MIT | **Language:** Python/CUDA

ExLlamaV2 is optimized for consumer GPU inference with its own EXL2 quantization format.

- **EXL2 quantization** — high-quality variable-bit quantization, often better quality than GGUF at same size
- **Tensor parallelism** — added in v0.3.2+, `--gpu_split auto` for multi-GPU
- **Fast on consumer GPUs** — 250-350 tok/s reported on batched RTX 3090 setups
- **No multi-node** — single machine only
- **Needs API wrapper** — TabbyAPI or similar for OpenAI-compatible serving

**Why not primary:** No continuous batching, no multi-node, smaller ecosystem. The EXL2 format is excellent but model availability is lower than GGUF or HuggingFace formats.

**Appropriate use:** Could serve Node 2's single-GPU workloads if vLLM proves problematic on the 4090. Not a primary candidate.

**Sources:**
- [ExLlamaV2 GitHub](https://github.com/turboderp-org/exllamav2)
- [ExLlamaV2 on consumer GPUs (Medium)](https://medium.com/@shouke.wei/exllamav2-revolutionizing-local-llm-inference-on-consumer-gpus-e14213f610bf)
- [ExLlamaV2 tensor parallelism issue](https://github.com/turboderp-org/exllamav2/issues/571)

---

### 6. TensorRT-LLM

**License:** Apache 2.0 | NVIDIA's own optimization framework

- **Maximum theoretical performance** — NVIDIA's compiler optimizations
- **Native Blackwell support** — NVIDIA controls the stack end-to-end
- **Extremely complex** — requires model conversion, engine building, version-locked to specific CUDA/driver combos
- **Poor documentation** for consumer hardware configurations
- **API changes frequently** — NVIDIA rewrites things between releases

**Why not for Athanor:** Decisively fails the one-person scale test. The setup, debugging, and maintenance overhead is enterprise-grade. When something breaks (and it will, on consumer hardware), diagnosing the issue requires deep NVIDIA stack knowledge. vLLM and SGLang both use TensorRT-LLM components internally where beneficial — there's no need to manage it directly.

---

## Comparison Matrix

| Criterion | vLLM | SGLang | llama.cpp | Ollama | ExLlamaV2 | TRT-LLM |
|-----------|------|--------|-----------|--------|-----------|---------|
| Multi-GPU tensor parallel | Yes | Yes | Fork only | No | Yes (recent) | Yes |
| Multi-node (InfiniBand) | Yes (Ray) | Yes (NCCL) | No | No | No | Yes |
| Continuous batching | Yes | Yes | No | No | Limited | Yes |
| OpenAI-compatible API | Native | Native | Wrapper | Partial | Wrapper | Wrapper |
| Blackwell (sm_120) | Build from source | Claimed | Workaround | Via llama.cpp | Unknown | Native |
| NVFP4 quantization | Yes | Yes | No | No | No (EXL2 instead) | Yes |
| Community size | 33k stars | 7.3k stars | 75k stars | 120k stars | 4k stars | N/A |
| Docker documentation | Extensive | Growing | Basic | Good | Minimal | Complex |
| One-person maintainable | Yes | Yes | Yes | Yes | Yes | No |
| Consumer GPU documentation | Good | Limited | Excellent | Excellent | Good | Poor |

---

## NVFP4: The Blackwell Advantage

NVFP4 is NVIDIA's native 4-bit floating-point format exclusive to Blackwell GPUs. It deserves special attention because it fundamentally changes the model sizing math:

| Model | FP16 Size | NVFP4 Size | Fits on Node 1 (64 GB)? | Quality Loss |
|-------|-----------|------------|--------------------------|--------------|
| Llama 3.1 70B | ~140 GB | ~35 GB | Yes (with KV cache room) | 2-4% |
| Llama 3.1 8B | ~16 GB | ~4 GB | Yes (single GPU) | 2-4% |
| Mistral 7B | ~14 GB | ~3.5 GB | Yes (single GPU) | 2-4% |
| Qwen 72B | ~144 GB | ~36 GB | Yes (tight with KV cache) | 2-4% |

At NVFP4, Node 1's 64 GB VRAM comfortably holds a 70B model with room for KV cache — something that requires ~140 GB at FP16. This is the primary quantization target for Blackwell GPUs.

Additionally, NVFP4 provides 1.6x throughput over BF16 and 41% energy reduction. This isn't just about fitting models — they run faster and cooler too.

Both vLLM and SGLang support NVFP4.

**Sources:**
- [NVFP4: Same Accuracy with 2.3x Higher Throughput (Kaitchup)](https://kaitchup.substack.com/p/nvfp4-same-accuracy-with-23-higher)
- [NVIDIA Blackwell NVFP4 Impact (Edge AI)](https://www.edge-ai-vision.com/2025/10/nvidia-blackwell-the-impact-of-nvfp4-for-llm-inference/)
- [Private LLM Inference on Consumer Blackwell GPUs](https://arxiv.org/html/2601.09527v1)
- [RTX 4090 vs 5090 vs PRO 6000 benchmark](https://www.cloudrift.ai/blog/benchmarking-rtx-gpus-for-llm-inference)

---

## PCIe Bandwidth Reality Check

Node 1's EPYC 7663 provides PCIe 4.0 (not 5.0). Each RTX 5070 Ti gets PCIe 4.0 x16:

| Metric | Value |
|--------|-------|
| Per-GPU bandwidth | ~32 GB/s per direction (PCIe 4.0 x16) |
| All-reduce across 4 GPUs | Bottlenecked by PCIe, not NVLink |
| Impact on inference | Manageable — activations are small vs compute |
| Impact on training | Significant — would hurt fine-tuning throughput |

For inference, the activation tensor at each layer boundary is small (proportional to batch_size × hidden_dim, typically a few MB). The matrix multiply compute time dominates over the PCIe transfer time. Benchmarks show consumer 4-GPU TP working well for inference at PCIe 4.0 speeds.

For fine-tuning (LoRA/QLoRA), gradient synchronization is heavier. This will be slower than NVLink but still functional. Acceptable for Athanor's occasional fine-tuning needs.

Node 2's RTX 5090 gets PCIe 5.0 x16 (~64 GB/s per direction) on the ProArt X870E board. The 4090 gets PCIe 4.0 x16. Since they run independently (not in TP), PCIe bandwidth isn't a concern for Node 2.

---

## Cost Validation

From the arxiv paper on consumer Blackwell inference:

> Self-hosted inference costs $0.001–0.04 per million tokens (electricity only) — 40-200x cheaper than budget-tier cloud APIs.

For Athanor's agent-heavy workloads (thousands of inference calls per task), local inference is not just more capable (uncensored, low-latency, private) — it's dramatically cheaper per token.

---

## Open Questions

1. **When will sm_120 land in stable PyTorch?** Currently nightly only. This determines when vLLM/SGLang work out-of-the-box without building from source. Expected within months, not a blocker.

2. **vLLM vs SGLang for agent workloads?** SGLang's RadixAttention gives ~10% benefit for multi-turn conversations with shared system prompts — exactly what agents do. If Athanor's agent workloads are heavily multi-turn (likely), SGLang may eventually win on throughput. But vLLM's larger community and better documentation win on maintainability today.

3. **NVFP4 model availability?** NVFP4 models must be pre-quantized or quantized on load. HuggingFace is starting to host NVFP4 variants. For models without NVFP4 versions, vLLM can quantize on-the-fly but this adds load time.

4. **ConnectX-3 with consumer GPUs for NCCL?** vLLM's multi-node InfiniBand documentation targets datacenter hardware. ConnectX-3 (IB FDR 56G) with consumer GPUs may need specific NCCL configurations. This is a spike/validation task, not a research question.

---

## Recommendation

### Primary engine: vLLM

vLLM is the right choice for Athanor's primary inference engine because:

1. **It handles every deployment pattern we need** — 4-GPU tensor parallelism on Node 1, independent single-GPU instances on Node 2, multi-node pipeline parallelism over InfiniBand
2. **OpenAI-compatible API** — agents, dashboard, tools, and any future integration all speak the same API
3. **Continuous batching** — serves agents, chat, and creative workloads concurrently without blocking
4. **NVFP4 support** — unlocks Blackwell's quantization advantage for 70B+ models on 64 GB VRAM
5. **Largest community** — most bug reports, most fixes, most Docker examples, most Stack Overflow answers
6. **One-person maintainable** — complex to build from source today (Blackwell), but the API and operations model are well-understood

### Watch: SGLang

SGLang is the strongest alternative. If any of these happen, re-evaluate:
- SGLang's community grows significantly (>15k stars)
- SGLang's Blackwell consumer GPU documentation catches up to vLLM's
- Athanor's agent workloads prove to be heavily bottlenecked by KV cache reuse (where RadixAttention shines)
- vLLM hits a fundamental limitation for Athanor's use case

### Utility: llama.cpp

Keep llama.cpp available for:
- Quick model testing without starting vLLM
- CPU-offloaded inference when a model barely exceeds VRAM
- Development/testing on DEV machine (RTX 3060)

### Not used: Ollama, ExLlamaV2, TensorRT-LLM

- Ollama: Can't tensor-parallel, can't batch — not suitable
- ExLlamaV2: Good but vLLM covers its use cases with better ecosystem
- TensorRT-LLM: Fails one-person scale test
