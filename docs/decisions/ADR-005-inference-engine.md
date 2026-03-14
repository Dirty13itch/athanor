# ADR-005: AI Inference Engine

**Date:** 2026-02-15
**Status:** Accepted
**Research:** [docs/research/2026-02-15-inference-engine.md](../research/2026-02-15-inference-engine.md)
**Depends on:** ADR-004 (Node Roles + Hardware Allocation)

---

## Context

Athanor needs to serve LLMs to agents, a dashboard chat interface, creative pipelines, and game AI — concurrently, from consumer Blackwell GPUs, across two compute nodes connected by InfiniBand. The inference engine is the most critical software choice in the stack: it determines what models can run, how fast they respond, and how many workloads can share the GPUs.

Six candidates were evaluated: vLLM, SGLang, llama.cpp, Ollama, ExLlamaV2, and TensorRT-LLM. The evaluation focused on: multi-GPU tensor parallelism (Node 1's 4x RTX 5070 Ti), multi-node InfiniBand support, continuous batching for concurrent requests, OpenAI API compatibility, Blackwell (sm_120) support, NVFP4 quantization, and one-person maintainability.

---

## Decision

### vLLM as the primary inference engine across all nodes.

#### Node 1 — Large Model Serving (4-GPU Tensor Parallel)

```bash
vllm serve meta-llama/Llama-3.1-70B-Instruct \
  --tensor-parallel-size 4 \
  --quantization nvfp4 \
  --host 0.0.0.0 \
  --port 8000
```

- 4x RTX 5070 Ti in tensor parallelism via NCCL over PCIe 4.0
- NVFP4 quantization: 70B model in ~35 GB VRAM, leaving ~29 GB for KV cache across 4 GPUs
- Agents on Node 1 call `localhost:8000` — zero network latency
- Dashboard and Node 2 services call via 10GbE (`node1:8000`)

#### Node 2 — Dual Independent Instances

```bash
# Instance 1: Creative/large single-GPU models on RTX 5090
CUDA_VISIBLE_DEVICES=0 vllm serve meta-llama/Llama-3.1-70B-Instruct \
  --quantization nvfp4 \
  --host 0.0.0.0 \
  --port 8000

# Instance 2: Fast chat model on RTX 4090
CUDA_VISIBLE_DEVICES=1 vllm serve mistralai/Mistral-7B-Instruct-v0.3 \
  --host 0.0.0.0 \
  --port 8001
```

- RTX 5090 (32 GB): Serves larger models or creative-adjacent inference. NVFP4 puts 70B in 32 GB.
- RTX 4090 (24 GB): Fast interactive chat with small/medium models (7B-13B). Ada Lovelace — no NVFP4, uses standard quantization (GPTQ, AWQ, or FP16 for small models).
- Both instances run simultaneously in separate Docker containers with `NVIDIA_VISIBLE_DEVICES` isolation.

#### Multi-Node (When Needed)

For models exceeding either node's capacity, vLLM's Ray-based multi-node serving distributes layers via pipeline parallelism over InfiniBand:

```bash
# Node 1 (head)
ray start --head
vllm serve large-model \
  --tensor-parallel-size 4 \
  --pipeline-parallel-size 2

# Node 2 (worker)
ray start --address=node1:6379
```

Environment for InfiniBand:
```bash
NCCL_IB_HCA=mlx5
NCCL_IB_DISABLE=0
NCCL_DEBUG=TRACE  # verify IB usage in logs
```

This is the exception, not the default. Most workloads fit on a single node with NVFP4.

---

## API Architecture

Every inference consumer speaks the same API:

```
┌──────────────────────────────────────────────────┐
│  OpenAI-compatible API (vLLM)                    │
│                                                  │
│  Node 1:8000  — Large models (4-GPU TP)          │
│  Node 2:8000  — Creative/overflow (5090)         │
│  Node 2:8001  — Fast chat (4090)                 │
└──────────────────────────────────────────────────┘
         ▲              ▲              ▲
    Agents (Node 1)  Dashboard    Game AI (EoBQ)
    localhost:8000   10GbE        10GbE or localhost
```

Benefits:
- Any agent framework that supports OpenAI's API works out-of-the-box
- Dashboard chat sends requests to any endpoint based on model selection
- Load balancing / failover can be added later via a thin proxy (HAProxy, nginx) without changing any client code
- External API clients (Claude Code tool calls, custom scripts) work identically

---

## NVFP4: Blackwell's Quantization Advantage

NVFP4 is NVIDIA's native 4-bit floating-point format exclusive to Blackwell architecture. It runs in hardware on the tensor cores — not a software approximation.

| Metric | Value |
|--------|-------|
| Throughput vs BF16 | 1.6x faster |
| Energy reduction | 41% less power |
| Quality loss | 2-4% on standard benchmarks |
| Cost per million tokens | $0.001-0.04 (electricity only) |

**Impact on model sizing:**

| Model | FP16 | NVFP4 | Fits Node 1 (64 GB)? |
|-------|------|-------|----------------------|
| Llama 3.1 70B | ~140 GB | ~35 GB | Yes, with KV cache room |
| Qwen 72B | ~144 GB | ~36 GB | Yes, tight |
| Mistral 7B | ~14 GB | ~3.5 GB | Single GPU |

NVFP4 means Node 1 can comfortably serve 70B models that would otherwise require multi-node. This makes the 4-GPU TP configuration significantly more capable than raw VRAM numbers suggest.

The RTX 4090 on Node 2 does NOT support NVFP4 (Ada Lovelace architecture). It uses standard quantization formats (GPTQ, AWQ, GGUF via vLLM).

---

## Build Requirements (Temporary)

As of February 2026, running vLLM on Blackwell requires building from source:

```bash
# CUDA 12.8 + PyTorch nightly
pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu128

# Build vLLM from source
TORCH_CUDA_ARCH_LIST="12.0" pip install -e .

# Use FlashInfer backend (flash-attn has undefined symbol issues on sm_120)
export VLLM_ATTENTION_BACKEND=FLASHINFER
```

This complexity is temporary. PyTorch stable will include sm_120 support within months. Once it does, standard `pip install vllm` will work on Blackwell. The Dockerfile should pin versions and document the build process until then.

---

## Secondary Tools

### llama.cpp — Development & Testing

Keep available for:
- Quick model testing without starting vLLM (`./llama-cli -m model.gguf`)
- CPU-offloaded inference for models that barely exceed VRAM
- Development testing on DEV machine (RTX 3060)

Not for production serving — no continuous batching, no native OpenAI API.

### SGLang — Watch List

SGLang is the strongest alternative to vLLM. Re-evaluate if:
- Community grows past 15k GitHub stars (currently 7.3k)
- Blackwell consumer GPU documentation matures
- Agent workloads prove bottlenecked by KV cache reuse (SGLang's RadixAttention advantage)
- vLLM hits a fundamental limitation

SGLang's ~29% throughput advantage and RadixAttention's multi-turn benefits are compelling. But vLLM's community size, documentation depth, and homelab track record win today.

---

## What This Enables

- **70B models on Node 1** via NVFP4 + 4-GPU tensor parallelism — the core inference capability
- **Simultaneous chat + creative inference** on Node 2 — two models, two GPUs, no contention
- **Agents calling localhost:8000** — thousands of inference calls with zero network overhead
- **Multi-node 120 GB VRAM** via InfiniBand pipeline parallelism — for the rare model that exceeds 64 GB
- **One API for everything** — agents, dashboard, game AI, scripts all speak OpenAI-compatible
- **Future-proof** — when PyTorch stable supports sm_120, the build complexity disappears but the architecture stays

---

## Alternatives Considered

| Alternative | Why Not |
|-------------|---------|
| SGLang as primary | Smaller community (7.3k vs 33k stars), less Docker/homelab documentation, Blackwell consumer GPU support less proven. Performance advantage is real but maintainability wins for one-person operation. |
| llama.cpp for everything | No continuous batching — fatal for concurrent agents + chat + creative. No multi-node. Tensor parallelism only in fork (ik_llama.cpp). |
| Ollama | Cannot do tensor parallelism. Single-request serving. Not designed for production workloads. |
| ExLlamaV2 | Good for consumer GPUs but vLLM covers the same use cases with better ecosystem, continuous batching, and multi-node support. |
| TensorRT-LLM | Fails the one-person scale test. Setup and maintenance complexity is enterprise-grade. vLLM uses TRT-LLM components internally where beneficial. |
| Different engines per node | Unnecessary complexity. vLLM handles all three deployment patterns (multi-GPU TP, single-GPU, multi-node PP). One engine = one API = one set of skills to maintain. |

---

## Risks

- **Blackwell build complexity.** Building vLLM from source with PyTorch nightly is fragile — version mismatches break things. Mitigated by Docker (pin all versions in Dockerfile) and the fact that this is temporary (stable PyTorch sm_120 coming).
- **PCIe 4.0 TP scaling.** Without NVLink, 4-GPU tensor parallelism on Node 1 won't scale as efficiently as datacenter setups. For inference (not training), benchmarks show this is manageable. Monitor actual throughput after deployment and adjust batch sizes if needed.
- **ConnectX-3 + consumer GPU NCCL.** Multi-node InfiniBand with consumer GPUs is less tested than datacenter configurations. GPUDirect RDMA may not work (consumer GPUs lack BAR1 size for full GPU memory mapping). Fallback: NCCL over IB without RDMA, which still beats 10GbE. This is a validation spike, not a blocker.
- **vLLM API stability.** vLLM moves fast and occasionally introduces breaking changes. Pin versions in Docker and test upgrades before deploying.

---

## Implementation Order

1. **Install NVIDIA drivers** on both nodes (535+ for Blackwell, or 570+ for NVFP4)
2. **Build vLLM Docker image** with PyTorch 2.9.0+cu128 and sm_120 support
3. **Deploy single-GPU test** on Node 2's RTX 4090 (known-good architecture, validates vLLM setup)
4. **Deploy 4-GPU TP** on Node 1 — the critical validation that TP works on 4x 5070 Ti over PCIe 4.0
5. **Test NVFP4** on Node 1 with a 70B model — validates the primary use case
6. **Deploy Node 2 dual-instance** — 5090 and 4090 running simultaneously
7. **Test multi-node** (defer until a model requires it) — Ray + NCCL over IB

---

## Sources

- [vLLM documentation](https://docs.vllm.ai/en/stable/)
- [vLLM RTX 5090 setup guide](https://discuss.vllm.ai/t/vllm-on-rtx5090-working-gpu-setup-with-torch-2-9-0-cu128/1492)
- [vLLM distributed serving](https://docs.vllm.ai/en/v0.8.0/serving/distributed_serving.html)
- [Private LLM Inference on Consumer Blackwell GPUs (arxiv)](https://arxiv.org/html/2601.09527v1)
- [RTX GPU benchmark: 4090 vs 5090 vs PRO 6000](https://www.cloudrift.ai/blog/benchmarking-rtx-gpus-for-llm-inference)
- [NVFP4 throughput analysis](https://kaitchup.substack.com/p/nvfp4-same-accuracy-with-23-higher)
- [SGLang pipeline parallelism](https://lmsys.org/blog/2026-01-15-chunked-pipeline/)
- [SGLang vs vLLM benchmarks](https://rawlinson.ca/articles/vllm-vs-sglang-performance-benchmark-h100)
- [llama.cpp multi-GPU breakthrough](https://medium.com/@jagusztinl/llama-cpp-performance-breakthrough-for-multi-gpu-setups-04c83a66feb2)
- [Multi-GPU comparison: vLLM vs llama.cpp vs Ollama](https://www.arsturn.com/blog/multi-gpu-showdown-benchmarking-vllm-llama-cpp-ollama-for-maximum-performance)
- [ExLlamaV2 for consumer GPUs](https://github.com/turboderp-org/exllamav2)
- [vLLM on Debian 12 & RTX 5070 Ti](https://ligma.blog/post1/)
