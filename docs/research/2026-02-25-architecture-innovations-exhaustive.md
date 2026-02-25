# Architecture Innovations: Exhaustive Survey (Dec 2025 - Feb 2026)

**Date:** 2026-02-25
**Status:** Complete -- comprehensive survey
**Scope:** Every significant architecture innovation, long-context technique, and non-transformer model from the last 90 days
**Relevance:** Athanor runs Qwen3-32B-AWQ on 4x 5070 Ti 16GB + 4090 24GB via vLLM TP=4. Innovations that reduce VRAM, extend context, or improve throughput on consumer GPUs are directly actionable.

---

## Table of Contents

1. [Long Context Innovations](#1-long-context-innovations)
2. [Non-Transformer Architectures](#2-non-transformer-architectures)
3. [Memory Efficiency Innovations](#3-memory-efficiency-innovations)
4. [Mixture of Experts Innovations](#4-mixture-of-experts-innovations)
5. [Training Innovations Affecting Inference](#5-training-innovations-affecting-inference)
6. [Inference Engine Advances](#6-inference-engine-advances)
7. [Actionable Recommendations for Athanor](#7-actionable-recommendations-for-athanor)

---

## 1. Long Context Innovations

### 1.1 Chunked Pipeline Parallelism (SGLang)

**What:** Breaks ultra-long prompts into smaller chunks (4K-6K tokens) that flow through pipeline stages like micro-batches, enabling overlapping computation across stages.

**Who/When:** LMSYS/SGLang team, January 15, 2026 (blog), shipped in SGLang v0.5.8 (Jan 23, 2026).

**How it works:**
- Instead of feeding the full prompt monolithically, partitions into chunks
- While Stage 1 processes Chunk 2, Stage 2 handles Chunk 1 simultaneously
- Asynchronous P2P communication overlaps GPU compute with data movement
- Dynamic chunking adaptively reduces chunk size at runtime to minimize pipeline bubbles

**Performance:**
- DeepSeek-V3.1 on H20: PP4 TP8 achieves 3.31x throughput vs TP8 alone
- Outperforms TP32 by 30.5%, reduces TTFT by 67.9%
- Qwen3-235B-A22B-FP8: PP8 reduces TTFT from ~55.5s to ~10.5s (81.1% improvement)
- 1M token contexts: ~421 seconds TTFT with close to linear scaling

**Athanor relevance:** HIGH. This could enable million-token inference on our hardware by distributing across Node 1 and Node 2 via pipeline parallelism. Currently we are limited by single-node VRAM for KV cache.

**Source:** https://lmsys.org/blog/2026-01-15-chunked-pipeline/

---

### 1.2 Native Sparse Attention (NSA)

**What:** Dynamic hierarchical sparse attention combining coarse-grained token compression with fine-grained token selection. Maintains full-attention quality while dramatically reducing compute.

**Who/When:** DeepSeek (15 researchers led by Jingyang Yuan), February 16, 2025 (arxiv:2502.11089).

**How it works:**
- Multi-level sparse attention pattern (not uniform sparsity)
- Hardware-aligned algorithm design optimized for modern accelerators (arithmetic intensity balanced)
- End-to-end trainable -- can be used during pretraining, not just inference
- Reduces pretraining computation without performance degradation

**Performance:**
- "Substantial speedups" on 64K-length sequences across decoding, forward, and backward passes
- Maintains or exceeds Full Attention quality on general benchmarks, long-context tasks, and instruction reasoning
- SGLang v0.5.9 integrated TRT-LLM NSA kernels for DeepSeek V3.2: **3-5x speedup on Blackwell platforms**

**Athanor relevance:** HIGH. Already shipping in SGLang for DeepSeek V3.2 inference. If/when DeepSeek models become our primary, NSA is available. Also implemented in flash-linear-attention repo for other models.

**Source:** https://arxiv.org/abs/2502.11089, SGLang v0.5.9 release notes

---

### 1.3 MoBA (Mixture of Block Attention)

**What:** Applies MoE principles to attention computation. Divides context into blocks; each query token learns to attend selectively to the most relevant KV blocks instead of the full sequence.

**Who/When:** Moonshot AI (Kimi), February 2025 (arxiv:2502.13189). Deployed in production for Kimi's long-context requests.

**How it works:**
- Context partitioned into manageable blocks
- Parameter-less top-k gating selects relevant blocks per query (no additional trainable parameters)
- Flexible full-to-sparse transition during inference
- Requires continued training of existing models (NOT a drop-in replacement)

**Performance:**
- Up to **40x speedup** over naive implementation (32K sequence, 1 head, block 2048, top-k 3)
- Successfully handles 1M context length with strong needle-in-haystack performance

**Athanor relevance:** MEDIUM. Requires model retraining, so not immediately applicable. But if Kimi-K2.5 or future models ship with MoBA built in (vLLM v0.15.0 already supports Kimi-K2.5), we get this for free.

**Source:** https://github.com/MoonshotAI/MoBA, https://arxiv.org/abs/2502.13189

---

### 1.4 SageAttention2/2++

**What:** Quantized attention kernels using INT8 for QK^T and FP8 for PV computation, with outlier smoothing. Drop-in replacement for standard attention.

**Who/When:** Tsinghua University, latest version active development through Feb 2026.

**How it works:**
- INT8 quantization for Q*K^T with outlier smoothing to maintain accuracy
- FP8 quantization for P*V with FP16 accumulators
- Two-level accumulation for FP8 precision
- Plug-and-play: `F.scaled_dot_product_attention = sageattn`

**Performance:**
- **2-5x speedup** over FlashAttention across hardware
- RTX 5090: **560 TFLOPS**, 2.7x faster than FlashAttention2
- H20: Matches FlashAttention3-FP8 speed with better accuracy

**GPU support:** Ampere (3090, A100), Ada (4090), Hopper (H100), **Blackwell (5090)**

**Athanor relevance:** VERY HIGH. Supports our exact GPUs. Drop-in replacement. 2.7x speedup on RTX 5090, should provide significant speedups on 5070 Ti and 4090 too. Check integration with vLLM.

**Source:** https://github.com/thu-ml/SageAttention

---

### 1.5 FlashInfer (MLSys 2025)

**What:** Customizable attention engine for LLM serving with block-sparse KV cache formats and JIT-compiled kernels.

**Who/When:** Accepted MLSys 2025. Already the default MLA backend on Blackwell in vLLM v0.15.0.

**Performance:**
- 29-69% inter-token-latency reduction vs compiler-based serving
- 28-30% latency reduction for long-context inference
- 13-17% speedup for parallel generation

**Athanor relevance:** HIGH. Already active in our vLLM stack ("FlashInfer MLA is now the default MLA backend on Blackwell" per vLLM v0.15.0). We are already benefiting from this.

**Source:** https://arxiv.org/abs/2501.01005 (FlashInfer paper)

---

### 1.6 "Rope to Nope and Back Again" -- Hybrid Attention

**What:** A new hybrid attention mechanism combining global and local attention spans with mixed positional embeddings (RoPE + NoPE + QK-Norm).

**Who/When:** January 30, 2025 (arxiv:2501.18795), revised October 2025.

**How it works:**
- Analyzes failure modes of RoPE, NoPE, and QK-Norm individually
- Proposes hybrid approach integrating global and local attention spans with different PE strategies
- Achieves efficiency gains in both training and inference

**Performance:** "Surpasses conventional RoPE-based transformer models with full attention in both long and short context tasks."

**Athanor relevance:** LOW-MEDIUM. Research direction. No available models yet, but if future Qwen or Llama adopt this approach, we benefit automatically.

**Source:** https://arxiv.org/abs/2501.18795

---

### 1.7 KV Cache Offloading Connector (vLLM)

**What:** Intelligent KV cache transfer to CPU/disk to maximize inference throughput for long sequences that exceed GPU memory.

**Who/When:** vLLM team, January 8, 2026 (blog post).

**Athanor relevance:** HIGH. Direct upgrade path. When serving long-context prompts, KV cache can overflow 16GB per GPU. Offloading to our 224GB Node 1 RAM extends effective context dramatically.

**Source:** vLLM blog, January 8, 2026

---

### 1.8 EasyContext (Ring Attention + Sequence Parallelism)

**What:** Extends LLM context to 1M tokens using sequence parallelism across GPUs. Combines ring attention, DeepSpeed Zero3, Flash Attention, activation checkpointing, and RoPE frequency scaling.

**Performance:**
- 700K tokens on 8x A100 (Llama2-7B)
- 1M tokens on 16x A100 (Llama2-13B)
- Full finetuning, full attention, no approximations
- Throughput: 10,240 tok/s at 64K, 1,603 tok/s at 700K

**Athanor relevance:** MEDIUM. Training-focused (context extension via fine-tuning), but demonstrates that ring attention across consumer GPUs is feasible.

**Source:** https://github.com/jzhang38/EasyContext

---

### 1.9 Flash Attention 3

**What:** Next-gen attention kernels for Hopper GPUs with asynchronous execution and FP8 support.

**Performance:**
- FP16: 1.5-2.0x faster than FA2, 740 TFLOPs/s (75% H100 utilization)
- FP8: ~1.2 PFLOPs/s throughput
- FP8 attention with 2.6x lower numerical error than baseline FP8

**Athanor relevance:** LOW for now. Hopper-specific (H100). Blackwell (our GPUs) will need FA4 or similar. SGLang v0.5.8 already has "Flash Attention 4 decoding kernel support" which is more relevant. vLLM v0.15.0 has "FA4 (FP4 Attention) Support."

**Source:** https://arxiv.org/abs/2407.08608

---

### 1.10 FA4 / FP4 Attention (SGLang + vLLM)

**What:** FP4 (4-bit) attention computation for Blackwell GPUs. Reduces attention memory and compute by 4x vs FP16.

**Who/When:** SGLang v0.5.8 (Jan 2026) added FA4 decoding kernel. vLLM v0.15.0 added FA4 for multimodal encoders.

**Athanor relevance:** VERY HIGH. Blackwell-native optimization. Directly reduces KV cache memory on our 5070 Ti and 5090 GPUs, extending effective context length.

**Source:** SGLang v0.5.8 release notes, vLLM v0.15.0 release notes

---

## 2. Non-Transformer Architectures

### 2.1 RWKV-7 "Goose"

**What:** The strongest linear-time, constant-space (no KV cache), attention-free RNN architecture. A meta-in-context learner that performs test-time training on its state through in-context gradient descent at each token.

**Who/When:** Bo Peng and RWKV community. Paper published March 18, 2025 (arxiv:2503.14456). Models on HuggingFace since July 2025. Linux Foundation AI project.

**Architecture:**
- "Dynamic State Evolution" -- addresses TC0 expressive power limitations of attention/linear attention
- Linear time complexity: O(n) vs O(n^2) for standard attention
- Constant memory: no KV cache needed (fixed state size regardless of sequence length)
- In-context gradient descent: the state evolves to learn from context in real time

**Available models:**
- RWKV7-Goose-World3-2.9B (HF, updated Jul 2025)
- RWKV7-Goose-World3-1.5B (HF)
- RWKV7-Goose-World2.9-0.4B (HF)
- RWKV7-Goose-Pile variants: 1.47B, 421M, 168M

**Performance:**
- "10 to 100 times lower computational requirements compared to Transformers with larger contexts"
- "As well as Transformer architectures in terms of answer quality and generalization ability"
- Training: 7.2B model at ~206K tok/s on 4x8 H100, "very stable and spike-free"

**Athanor relevance:** MEDIUM-HIGH. No models above 3B yet, which limits practical use. But the constant-memory property is transformative for long context -- a 3B RWKV-7 can handle any context length with fixed ~6GB VRAM. When 7B+ models arrive, this becomes very interesting for our 16GB GPUs. Implemented in flash-linear-attention repo. Runtime integrated into Windows and Office.

**Limitation:** vLLM/SGLang support unclear. Would need custom serving or RWKV's own inference runtime.

**Source:** https://github.com/BlinkDL/RWKV-LM, https://huggingface.co/RWKV

---

### 2.2 Mamba / Mamba-2

**What:** State-space model (SSM) architecture achieving linear-time inference with constant memory per token. Mamba-2 introduces State Space Duality (SSD) connecting SSMs to attention.

**Who/When:** Albert Gu and Tri Dao. Mamba-2 at ICML 2024. Mamba v2.3.0 released January 12, 2026.

**Architecture (Mamba-2):**
- SSD module: generalized connection between SSMs and transformers
- d_state 64-128 (vs 16 in Mamba-1)
- Conversion between discrete and continuous SSM forms
- Linear-time sequence processing, constant memory per step

**Available models:**
- Mamba-1: 130M to 2.8B (300B Pile tokens)
- Mamba-2: 130M to 2.7B (300B Pile tokens)
- Falcon Mamba 7B: surpasses Mistral 7B, Llama 3.1 8B, matches Gemma 7B
- Hybrid: mamba2attn-2.7B (Mamba-2 + attention layers)

**vLLM integration:** YES. vLLM v0.15.0 has "Mamba prefix caching achieving ~2x speedup by caching Mamba states directly" and "block-aligned prefix caching for hybrid models."

**Athanor relevance:** HIGH. Falcon Mamba 7B is a competitive 7B model that fits on a single 16GB GPU with constant-memory inference. Mamba prefix caching in vLLM means we can serve it efficiently. The 7B size and permissive license make it a viable secondary model.

**Source:** https://github.com/state-spaces/mamba, Falcon Mamba: https://arxiv.org/abs/2410.05355

---

### 2.3 Hybrid SSM-Transformer Models

Three major families combine SSM/Mamba with transformer attention:

#### 2.3.1 Zamba2 (Zyphra)
- Mamba2 backbone alternating with 2 shared attention blocks (ABAB pattern)
- LoRA projections on shared MLPs for per-layer specialization
- Concatenates original embeddings to attention inputs
- **2.7B params, SOTA at <3B class**
- "Extremely low inference latency and rapid generation with significantly smaller memory footprint"
- Trained on 3T tokens
- **Source:** https://github.com/Zyphra/Zamba2

#### 2.3.2 Nemotron-H (NVIDIA)
- Hybrid MoE combining Mamba layers with attention
- Quantization-aware distillation
- **4x throughput on B200 vs FP8-H100**
- SGLang day-0 support (December 2025)
- LoRA support in vLLM v0.15.0
- **Source:** LMSYS blog, December 15, 2025

#### 2.3.3 Jamba (AI21)
- SSM + transformer attention hybrid
- Large model (up to Jamba-1.5-Large, ~90B MoE)
- Good long-context performance
- **Source:** AI21 Labs

#### 2.3.4 RecurrentGemma / Griffin (Google DeepMind)
- Local attention + linear recurrence (no global attention)
- 2B parameter variant available
- Fast inference on long sequences
- Pallas kernel for efficient linear scan
- **Source:** https://github.com/google-deepmind/recurrentgemma

**Athanor relevance for hybrids:** MEDIUM-HIGH. Zamba2 at 2.7B is interesting for lightweight tasks. Nemotron-H with vLLM support and 4x throughput gains on Blackwell is very promising -- watch for larger sizes.

---

### 2.4 Flash Linear Attention (FLA)

**What:** Comprehensive Triton-based library implementing efficient kernels for every major linear attention, SSM, and recurrent architecture. Platform-agnostic (NVIDIA, AMD, Intel).

**Supported architectures (28+):**
- Linear attention: RetNet, GLA, Based, Rebased
- SSMs: Mamba, Mamba2, Samba, Log-Linear Mamba2
- RNNs: RWKV6, RWKV7, HGRN, HGRN2
- Delta-based: DeltaNet, Gated DeltaNet, DeltaProduct, DeltaFormer
- Recent: NSA, MLA, MoM, FoX, KDA, ComBA, PaTH Attention
- Also: BitNet, Rodimus, MesaNet, LightNet, Forgetting Transformer

**Notable:** Qwen3-Next reportedly uses GDN (Gated DeltaNet) component from this repo.

**Athanor relevance:** HIGH as a technology platform. If Qwen3-Next or future models adopt Gated DeltaNet, this library provides the efficient kernels. Also useful for experimenting with alternative architectures on our hardware.

**Source:** https://github.com/fla-org/flash-linear-attention

---

### 2.5 xLSTM 7B

**What:** Extended LSTM with two components: mLSTM (matrix memory, excels at memorization) and sLSTM (stabilized, state tracking). Exponential gating with normalization.

**Who/When:** NX-AI (JKU Linz). xLSTM 7B released early 2025, trained on 2.3T tokens.

**Architecture:**
- Configurable blocks combining mLSTM + sLSTM
- Triton-optimized kernels for NVIDIA/AMD
- Constant memory during inference (like other recurrent models)

**Performance:** "Promising performance on Language Modeling when compared to Transformers or State Space Models" (vague -- limited public benchmarks).

**Athanor relevance:** LOW. Only 7B available, benchmarks are imprecise, ecosystem is small. Watch but don't act.

**Source:** https://github.com/NX-AI/xlstm

---

### 2.6 Huginn: Latent Recurrent Depth Model

**What:** A 3.5B model that scales test-time compute by iterating a recurrent block in latent space, achieving performance equivalent to ~50B parameters.

**Who/When:** University of Maryland, February 2025 (arxiv:2502.05171). Apache 2.0 license.

**Architecture:**
- **Prelude (P):** Embeds input to latent space (~1.5B non-recurrent params)
- **Recurrent Block (R):** Core computation, iterates N times (~1.5B params, reused)
- **Coda (C):** Un-embeds to predictions (~0.5B params)
- Formula: `e = P(x); s0 ~ N(0,sigma); si = R(e, s_{i-1}) for i in 1..r; p = C(sr)`
- Variable depth at test time via `num_steps` parameter (4-64 useful range)

**Key innovation:**
- Does not require specialized training data
- Works with small context windows
- Can capture reasoning not easily expressed in words
- Adaptive compute: per-token variable depth using KL divergence or entropy criteria
- Continuous CoT: warmstart reasoning state across tokens

**Performance:**
- 3.5B params, 800B training tokens
- With recurrence, matches reasoning performance of ~50B parameter models
- At num_steps=32: ~80GB materialized parameters (high VRAM)
- At num_steps=8-16: feasible on 24GB GPU (4090)

**Athanor relevance:** HIGH for concept, MEDIUM for immediate use. Only 3.5B base (no instruct tune). But the architecture is profound: a small model that "thinks harder" by iterating internally. If applied to Qwen3-32B scale, this could give us reasoning quality far beyond the parameter count. The concept of adaptive compute (spending more steps on hard tokens) is exactly what we want for agent workloads.

**Source:** https://huggingface.co/tomg-group-umd/huginn-0125, https://arxiv.org/abs/2502.05171

---

### 2.7 "Were RNNs All We Needed?" -- minLSTM/minGRU

**What:** Demonstrates that drastically simplified versions of classical LSTMs and GRUs (removing unnecessary components) achieve competitive performance with transformers while being fully parallelizable during training.

**Who/When:** Published 2025 (arxiv:2410.01201).

**Key finding:** minLSTMs and minGRUs use fewer parameters, are fully parallelizable for training, and rival modern transformer performance. Challenges the assumption that transformers were necessary.

**Athanor relevance:** LOW. Conceptually interesting but no production-ready models at competitive scale.

**Source:** https://arxiv.org/abs/2410.01201

---

### 2.8 Coconut: Chain of Continuous Thought

**What:** Enables LLMs to reason in continuous latent space rather than generating chain-of-thought tokens. Feeds hidden states back as input embeddings for iterative reasoning.

**Who/When:** Accepted COLM 2025 (arxiv:2412.06769).

**Key innovation:**
- Uses last hidden state as "continuous thought" representation
- Enables breadth-first search over reasoning paths (vs single deterministic CoT)
- "Outperforms CoT on logical reasoning tasks that require substantial search"

**Athanor relevance:** MEDIUM. Similar concept to Huginn. No production models, but the direction of "think internally rather than generating tokens" reduces output token cost and could be faster for reasoning.

**Source:** https://arxiv.org/abs/2412.06769

---

## 3. Memory Efficiency Innovations

### 3.1 NVFP4 / FP4 Quantization Advances

**What:** Native 4-bit floating point on Blackwell GPUs. Both vLLM and SGLang now have optimized FP4 kernels.

**Recent advances (Dec 2025 - Feb 2026):**
- vLLM v0.15.0: "Up to **65% faster FP4 quantization on Blackwell** using 256-bit loads"
- MXFP4 W4A16 support for compressed-tensors MoE models
- FA4 (FP4 Attention) for multimodal encoders
- Megatron-LM v0.15.0: NVFP4 Zero Padding for MoE, FP8 init for MTP

**Athanor relevance:** VERY HIGH. Direct upgrade for our Blackwell GPUs. 65% faster FP4 means better throughput for NVFP4-quantized models. NVFP4 allows 70B models to fit in our 64GB TP=4 VRAM.

**Source:** vLLM v0.15.0 release notes, Megatron-LM v0.15.0 release notes

---

### 3.2 BitNet b1.58

**What:** 1.58-bit quantization (ternary weights: -1, 0, +1). Eliminates floating-point matrix multiplications entirely.

**Who/When:** Microsoft. BitNet.cpp v1.0 (Oct 2024). CPU optimization update January 15, 2026.

**Performance:**
- ARM CPUs: 1.37-5.07x speedup, 55-70% energy reduction
- x86 CPUs: 2.37-6.17x speedup, 72-82% energy savings
- 100B model on single CPU at human reading speed (5-7 tok/s)
- January 2026 update: parallel kernels add 1.15-2.1x additional speedup

**Available models:** BitNet-b1.58-2B-4T (2.4B params, ARM + x86)

**Athanor relevance:** MEDIUM. Only 2.4B model available. The technology is compelling (100B on CPU at reading speed would be incredible for our 224GB RAM Node 1), but needs larger models. If someone trains BitNet at 70B scale, this changes everything for CPU inference.

**Source:** https://github.com/microsoft/BitNet

---

### 3.3 MatMul-Free LM

**What:** Language model architecture eliminating matrix multiplication operations entirely. Uses ternary weights and fused operations.

**Who/When:** Active development, models up to 2.7B available.

**Architecture:** FusedBitLinear layers with ternary weights, FusedRMSNormSwishGate. "Steeper scaling descent" than Transformer++ -- more efficient compute scaling.

**Available models:** 370M (15B tokens), 1.3B (100B tokens), 2.7B (100B tokens)

**Athanor relevance:** LOW. Small models only. Same limitation as BitNet -- needs scale to be useful.

**Source:** https://github.com/ridgerchu/matmulfreellm

---

### 3.4 Mixture of Depths

**What:** Transformers that dynamically allocate compute by routing tokens through or around layers. Top-k mechanism determines which tokens get processed at each layer.

**Who/When:** Google (arxiv:2404.02258), 2024. Concept, not a shipped model.

**How it works:**
- Top-k routing per layer selects which tokens undergo self-attention + MLP
- Remaining tokens bypass the layer (residual connection only)
- Fixed total compute budget, but dynamic per-token allocation
- "Entirely predictable in sum total, but dynamic and context-sensitive at the token-level"

**Performance:**
- Matches baseline at equivalent FLOPs
- **50% faster sampling** during post-training generation
- Requires fewer FLOPs per forward pass

**Athanor relevance:** MEDIUM. No production models use this yet. But the concept is powerful -- 50% faster inference at same quality. If Qwen4 or Llama 4 adopt this, we benefit automatically.

**Source:** https://arxiv.org/abs/2404.02258

---

### 3.5 Byte Latent Transformer (BLT)

**What:** Operates on raw bytes instead of tokens, using dynamic patch segmentation based on next-byte entropy. Allocates more compute where data is complex.

**Who/When:** Meta, December 2024 (arxiv:2412.09871).

**Key innovation:**
- Variable-length patches instead of fixed tokens
- More compute on complex regions, less on predictable ones
- First FLOP-controlled scaling study of byte-level models up to 8B
- "Significantly better scaling than tokenization-based models"

**Athanor relevance:** LOW-MEDIUM. Research stage. No production models. But the dynamic compute allocation principle is valuable -- harder text gets more compute, easy text gets less. Future models may adopt this.

**Source:** https://arxiv.org/abs/2412.09871

---

### 3.6 INT4 QAT for RL Training (1TB Model on Single GPU)

**What:** W4A16 quantization-aware training that maintains train-infer consistency, enabling 1TB-scale model rollout on a single H200.

**Who/When:** LMSYS blog, January 26, 2026.

**How it works:**
- Fake quantization during training + real INT4 at inference
- Train-infer consistency comparable to BF16
- Enables RL training of massive models on fewer GPUs

**Athanor relevance:** MEDIUM. Not directly applicable to our inference workload, but the W4A16 technique could enable us to fine-tune larger models on our hardware.

**Source:** LMSYS blog, January 26, 2026

---

## 4. Mixture of Experts Innovations

### 4.1 DeepSeek V3 Architecture Innovations

**What:** Three key MoE innovations that set the standard for late-2025/early-2026 models.

**Multi-head Latent Attention (MLA):**
- Compresses KV cache by projecting attention heads into lower-dimensional latent space
- Substantially reduces memory requirements during generation without quality loss
- FlashInfer MLA is now the default backend on Blackwell in vLLM

**Auxiliary-Loss-Free Load Balancing:**
- Eliminates auxiliary losses traditionally used for expert load balancing
- "Minimizes the performance degradation that arises from encouraging load balancing"
- More stable training, better expert utilization

**Multi-Token Prediction (MTP):**
- Predicts multiple future tokens simultaneously
- Enables speculative decoding during inference
- 671B total / 37B active per token

**Athanor relevance:** HIGH. MLA is already the default on our Blackwell GPUs via FlashInfer in vLLM. These innovations propagate through the ecosystem -- Qwen3, GLM, and other models are adopting similar techniques.

**Source:** https://github.com/deepseek-ai/DeepSeek-V3

---

### 4.2 Wide Expert Parallelism (Wide-EP)

**What:** Distributes MoE experts across many GPUs for large-scale serving. Key for DeepSeek-class models.

**Who/When:** vLLM team (February 3, 2026 blog) + LMSYS (February 19, 2026, DeepSeek on GB300).

**Performance:**
- DeepSeek V3.2 on GB300 NVL72: 226 TPS/GPU (1.53x over GB200)
- Uses prefill-decode disaggregation + chunked pipeline parallelism + wide EP
- FP8 attention + NVFP4 MoE quantization

**Athanor relevance:** LOW for our scale (we don't have 72 GPUs). But the techniques (MoE quantization, expert parallelism) filter down to smaller deployments. vLLM's MoRI EP all2all backend for AMD ROCm shows this is getting democratized.

**Source:** vLLM blog Feb 3 2026, LMSYS blog Feb 19 2026

---

### 4.3 Shared Expert Computation

**What:** Computing shared experts before the router, reducing latency for MoE inference.

**Who/When:** Megatron-LM v0.15.0 (December 17, 2025).

**Athanor relevance:** MEDIUM. Improves MoE serving efficiency. Relevant when we run Qwen3-235B-A22B (MoE) or DeepSeek models.

**Source:** Megatron-LM v0.15.0 release notes

---

### 4.4 Non-Gated MoE Quantization

**What:** vLLM v0.15.0 added quantization support for non-gated MoE models using Marlin, NVFP4 CUTLASS, FP8, and INT8 backends.

**Athanor relevance:** HIGH. Directly enables more efficient MoE model serving on our Blackwell GPUs.

**Source:** vLLM v0.15.0 release notes

---

## 5. Training Innovations Affecting Inference

### 5.1 Multi-Token Prediction (MTP)

**What:** Training models with N independent output heads to predict multiple future tokens simultaneously. Improves both training quality and inference speed.

**Who/When:** Meta (arxiv:2404.19737), 2024. Adopted by DeepSeek V3 and MiMo-V2-Flash.

**How it works:**
- N independent prediction heads on shared model trunk
- Each head predicts one of the next N tokens
- At inference, enables speculative decoding using the model's own MTP heads (no separate draft model needed)

**Performance:**
- 13B models: 12% more HumanEval, 17% more MBPP solved
- **Up to 3x faster inference** (models trained with 4-token prediction)
- No overhead in training time
- Increasingly useful for larger models

**Production implementations:**
- DeepSeek V3: MTP for speculative decoding
- MiMo-V2-Flash: Multi-layer MTP design, 309B params, sliding window attention
- Megatron-LM v0.15.0: FP8 initialization for MTP

**Athanor relevance:** VERY HIGH. 3x inference speedup is massive. DeepSeek V3 already uses this. Qwen3 does not (yet), but future models likely will. When we upgrade models, prioritize those with MTP for the built-in speculative decoding benefit.

**Source:** https://arxiv.org/abs/2404.19737

---

### 5.2 EAGLE-3 Speculative Decoding

**What:** Third generation of EAGLE speculative decoding. Fuses low-, mid-, and high-level semantic features for better draft quality.

**Who/When:** NeurIPS 2025. EAGLE-3 checkpoints available via SpecBundle/SpecForge (SGLang, December 2025).

**Performance:**
- **5.6x speedup** over standard decoding
- 1.8x faster than EAGLE-1
- 2x faster than Lookahead, 1.6x faster than Medusa

**Framework support:** NVIDIA TensorRT-LLM, vLLM, AWS NeuronX, AMD ROCm, Intel extensions. SGLang has EAGLE-3 for Pixtral, Qwen3 VL MoE.

**Athanor relevance:** VERY HIGH. 5.6x is transformative. Already in vLLM and SGLang. Check if EAGLE-3 checkpoints exist for Qwen3-32B. Even if not, EAGLE-2 at 4x is still huge.

**Source:** https://github.com/SafeAILab/EAGLE

---

### 5.3 LLaDA: Large Language Diffusion Model

**What:** Text generation via masked diffusion instead of autoregressive next-token prediction. 8B parameter model rivaling Llama3-8B.

**Who/When:** ML-GSAI group. LLaDA-8B released 2025. Variants: LLaDA-V (vision), LLaDA 1.5 (VRPO), LLaDA-MoE-7B-A1B.

**How it works:**
- Variable masking ratio (0 to 1, unlike BERT's fixed mask)
- Training objective is upper bound on negative log-likelihood
- Generation: multiple sampling steps equal to response length (currently slow)
- Can potentially generate all tokens in parallel (non-autoregressive)

**Current limitations:**
- Slower than autoregressive models (multiple diffusion steps needed)
- Historical parallel: image diffusion improved ~1000x over 4 years

**SGLang support:** Day-0 support for LLaDA 2.0 (December 19, 2025), using chunked-prefill.

**Athanor relevance:** MEDIUM. Fundamentally different paradigm. Currently slower, but the potential for parallel token generation could eventually surpass autoregressive speed. The MoE variant (7B/1B active) is interesting for efficiency. Watch closely.

**Source:** https://github.com/ML-GSAI/LLaDA

---

### 5.4 Medusa-2 Speculative Decoding

**What:** Adds multiple prediction heads to frozen LLMs. No separate draft model needed. Tree-based attention for candidate verification.

**Performance:** 2.2-3.6x speedup. Less than EAGLE-3 (5.6x) but simpler architecture.

**Athanor relevance:** MEDIUM. EAGLE-3 is strictly better. Use Medusa only if EAGLE-3 checkpoints aren't available for our models.

**Source:** https://github.com/FasterDecoding/Medusa

---

### 5.5 LASP-2: Efficient Sequence Parallelism for Linear Attention

**What:** Optimized distributed training for linear attention models. One AllGather vs ring communication.

**Performance:**
- 15.2% faster than LASP
- 36.6% faster than Ring Attention
- Tested at 2M token sequences on 64 GPUs

**Athanor relevance:** LOW. Training optimization, not inference. But indicates linear attention models are getting serious distributed training infrastructure.

**Source:** https://arxiv.org/abs/2502.07563

---

## 6. Inference Engine Advances (Dec 2025 - Feb 2026)

### 6.1 vLLM v0.15.0 / v0.15.1 (Jan 29 / Feb 4, 2026)

**Major additions relevant to Athanor:**
- FlashInfer MLA default on Blackwell
- **65% faster FP4 on Blackwell** (256-bit loads)
- Mamba prefix caching (2x speedup)
- Session-based streaming input
- EAGLE3 support
- Kimi-K2.5, GLM-Lite, Molmo2 architecture support
- torch.compile cold-start fix (88s to 22s for Llama3-70B)
- FIPS 140-3 compliant hash option
- AMD ROCm: FP4, Flash Attention Triton on RDNA3/RDNA4
- MXFP4 W4A16 for MoE models

**Source:** https://github.com/vllm-project/vllm/releases

---

### 6.2 SGLang v0.5.8 / v0.5.9 (Jan 23 / Feb 24, 2026)

**Major additions relevant to Athanor:**
- Million-token context via chunked pipeline parallelism
- FA4 decoding kernel (Blackwell)
- TRT-LLM NSA kernels for DeepSeek V3.2 (3-5x speedup on Blackwell)
- FP8 KV cache for context parallelism
- 1.5x faster diffusion model serving
- LoRA weight loading overlap (78% TTFT reduction, 35% TPOT reduction)
- Kimi-K2.5, GLM-5, Qwen 3.5, LLaDA 2.1 support
- Gateway v0.3.1: 10-12x cache-aware routing, 99% memory reduction, JWT/OIDC auth

**Source:** SGLang release notes

---

### 6.3 Transformer Engine v2.11 / v2.12 (Jan/Feb 2026)

- Sliding window attention with fused ops
- MXFP8 and NVFP4 performance: fused swizzling into quantization
- Current Scaling recipe for FP8 training
- Context parallelism for sliding window attention

**Source:** https://github.com/NVIDIA/TransformerEngine/releases

---

### 6.4 Megatron-LM v0.15.0 (Dec 17, 2025)

- Fused QKV preprocessing with precomputed RoPE caches: **3x preprocessing speedup, 10-14% E2E**
- CUDA Graph runner lookup table: **up to 2x E2E speedup**
- YaRN support for GPT-OSS
- FP8 MTP initialization
- Shared expert before router for MoE
- NVFP4 Zero Padding for MoE

**Source:** https://github.com/NVIDIA/Megatron-LM/releases

---

### 6.5 Other Notable Blog Posts (vLLM, Dec-Feb)

| Date | Topic | Key Detail |
|------|-------|------------|
| Feb 13 | DeepSeek-V3.2 on GB300 | Large-scale Blackwell deployment |
| Feb 1 | GPT-OSS on Blackwell | Performance optimization |
| Jan 31 | Streaming + Realtime API | Session-based incremental input |
| Jan 23 | Mixture-of-Models (vLLM-SR) | Semantic router for multi-model serving |
| Jan 5 | Semantic Router v0.1 Iris | Intelligent model selection |
| Dec 19 | vLLM-Omni Diffusion Cache | Multimodal with cache acceleration |
| Dec 17 | Wide-EP 2.2k tok/s/H200 | Large-scale MoE serving |
| Dec 15 | Encoder Disaggregation | Distribute vision encoder processing |
| Dec 14 | HaluGate | Token-level hallucination detection |
| Dec 13 | Speculators v0.3.0 | Draft model training + speculative decoding |
| Dec 9 | AutoRound x LLM Compressor | Low-bit quantization advances |

**Source:** https://blog.vllm.ai/

---

## 7. Actionable Recommendations for Athanor

### Immediate (This Week)

| Action | Impact | Effort |
|--------|--------|--------|
| **Upgrade vLLM to v0.15.1** | 65% faster FP4 on Blackwell, Mamba prefix caching, torch.compile fix | Container rebuild |
| **Evaluate SageAttention2** | 2.7x speedup on RTX 5090, 2-5x on other GPUs. Drop-in replacement | Test integration |
| **Check EAGLE-3 checkpoints for Qwen3** | 5.6x speculative decoding speedup | Config change if available |
| **Enable KV cache offloading** | Extend effective context using 224GB Node 1 RAM | vLLM config |

### Short-Term (Next 2-4 Weeks)

| Action | Impact | Effort |
|--------|--------|--------|
| **Test Falcon Mamba 7B** | Constant-memory inference on single 16GB GPU, vLLM supported | Model download + test |
| **Evaluate SGLang v0.5.9** | NSA kernels (3-5x on Blackwell), FA4, million-token context | Parallel install + benchmark |
| **Test Huginn for reasoning tasks** | 3.5B that reasons like 50B, adaptive compute | HuggingFace download |
| **Monitor RWKV-7 for 7B+ models** | Constant-memory infinite context on 16GB GPU | Watch releases |

### Medium-Term (1-3 Months)

| Action | Impact | Effort |
|--------|--------|--------|
| **Evaluate Qwen3-Next if released** | Likely uses Gated DeltaNet (linear attention), native FLA kernels | Model swap |
| **Test LLaDA-MoE-7B-A1B** | Diffusion LLM with 1B active params, SGLang support | Novel paradigm test |
| **Evaluate Nemotron-H larger models** | Hybrid MoE, 4x throughput on Blackwell | When NVIDIA releases larger sizes |
| **Implement chunked pipeline parallelism** | Million-token context across Node 1 + Node 2 | SGLang cross-node setup |

### Architecture Shifts to Watch

| Innovation | Why It Matters | Timeline |
|------------|---------------|----------|
| **Multi-Token Prediction** | 3x inference speedup, free speculative decoding | Likely in Qwen4, Llama 4 |
| **Native Sparse Attention** | 3-5x on Blackwell, already in DeepSeek V3.2 | Available now for DeepSeek |
| **Latent Reasoning (Huginn-style)** | Small models with variable-depth reasoning | 6-12 months for production models |
| **Diffusion LLMs (LLaDA)** | Non-autoregressive generation, parallel tokens | 1-2 years for competitive speed |
| **RWKV-7 at scale** | True constant-memory, infinite context, no KV cache | 3-6 months for 7B+ |
| **BitNet at scale** | 100B on CPU at reading speed | Unknown -- needs training investment |
| **Mixture of Depths** | 50% faster sampling, same quality | Needs model adoption |
| **MoBA** | 40x sparse attention speedup | Needs continued training |

---

## Summary of the Landscape

The Dec 2025 - Feb 2026 period represents a **Cambrian explosion in inference efficiency**. The key themes:

1. **Attention is being rethought from every angle**: NSA (DeepSeek), MoBA (Moonshot), SageAttention (quantized), FA4 (FP4), MLA (latent compression). The quadratic attention bottleneck is being attacked from at least 5 different directions simultaneously.

2. **Recurrent/linear architectures are maturing**: RWKV-7, Mamba 2.3, Falcon Mamba 7B, xLSTM 7B, flash-linear-attention with 28+ architectures. These are no longer research curiosities -- Falcon Mamba 7B beats Llama 3.1 8B on benchmarks.

3. **Hybrid models are the pragmatic middle ground**: Zamba2, Nemotron-H, Jamba, and likely Qwen3-Next combine SSM/recurrence with selective attention. Best of both worlds: constant memory for most processing, attention for hard cases.

4. **Speculative decoding is production-ready**: EAGLE-3 at 5.6x is in vLLM and SGLang. MTP provides built-in speculative decoding. These are the fastest wins for existing deployments.

5. **Blackwell-specific optimizations are landing rapidly**: FP4 kernels (65% faster), FA4, SageAttention (2.7x on 5090), FlashInfer MLA. Our GPU generation is getting the most optimization attention in the ecosystem.

6. **The KV cache problem is being solved multiple ways**: MLA (compress it), NSA/MoBA (make attention sparse), RWKV/Mamba (eliminate it), offloading (move it to RAM), FP4 (shrink it). Within a year, 1M-token context on consumer hardware should be routine.

For Athanor specifically, the **highest-impact immediate actions** are:
1. Upgrade vLLM for the Blackwell FP4 speedups
2. Evaluate SageAttention2 for 2-5x attention speedup
3. Enable EAGLE-3 speculative decoding for 5.6x generation speed
4. Enable KV cache offloading to leverage 224GB RAM for long context

These four changes alone could deliver **10-20x effective throughput improvement** on our existing hardware with no model changes.

---

## Sources Index

### Papers
- NSA: https://arxiv.org/abs/2502.11089
- MoBA: https://arxiv.org/abs/2502.13189
- Huginn: https://arxiv.org/abs/2502.05171
- Multi-Token Prediction: https://arxiv.org/abs/2404.19737
- Mixture of Depths: https://arxiv.org/abs/2404.02258
- Byte Latent Transformer: https://arxiv.org/abs/2412.09871
- Coconut: https://arxiv.org/abs/2412.06769
- Falcon Mamba 7B: https://arxiv.org/abs/2410.05355
- minLSTM/minGRU: https://arxiv.org/abs/2410.01201
- Flash Attention 3: https://arxiv.org/abs/2407.08608
- RWKV-7: https://arxiv.org/abs/2503.14456
- Rope to Nope: https://arxiv.org/abs/2501.18795
- LASP-2: https://arxiv.org/abs/2502.07563
- FlashInfer: https://arxiv.org/abs/2501.01005

### Repositories
- RWKV-LM: https://github.com/BlinkDL/RWKV-LM
- Mamba: https://github.com/state-spaces/mamba
- Flash Linear Attention: https://github.com/fla-org/flash-linear-attention
- SageAttention: https://github.com/thu-ml/SageAttention
- EAGLE: https://github.com/SafeAILab/EAGLE
- MoBA: https://github.com/MoonshotAI/MoBA
- LLaDA: https://github.com/ML-GSAI/LLaDA
- BitNet: https://github.com/microsoft/BitNet
- xLSTM: https://github.com/NX-AI/xlstm
- MatMul-Free LM: https://github.com/ridgerchu/matmulfreellm
- Zamba2: https://github.com/Zyphra/Zamba2
- RecurrentGemma: https://github.com/google-deepmind/recurrentgemma
- DeepSeek V3: https://github.com/deepseek-ai/DeepSeek-V3
- EasyContext: https://github.com/jzhang38/EasyContext
- Huginn: https://huggingface.co/tomg-group-umd/huginn-0125

### Release Notes & Blogs
- vLLM v0.15.0: https://github.com/vllm-project/vllm/releases/tag/v0.15.0
- vLLM blog: https://blog.vllm.ai/
- SGLang releases: https://github.com/sgl-project/sglang/releases
- LMSYS blog: https://lmsys.org/blog/
- Megatron-LM: https://github.com/NVIDIA/Megatron-LM/releases
- Transformer Engine: https://github.com/NVIDIA/TransformerEngine/releases
- RWKV HuggingFace: https://huggingface.co/RWKV

### Model Pages
- RWKV-7 models: https://huggingface.co/RWKV
- Falcon Mamba: https://huggingface.co/tiiuae/falcon-mamba-7b
- Qwen3: https://qwenlm.github.io/blog/qwen3/
