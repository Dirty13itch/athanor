# GPU Resource Orchestration for Consumer Hardware

**Date:** 2026-02-25
**Status:** Research complete, recommendation ready
**Author:** Research Agent

---

## Context

Athanor has 7 consumer NVIDIA GPUs across 2 nodes with 136 GB total VRAM. Every GPU is allocated to a service, yet hardware utilization is low -- DCGM metrics show 10-27% compute utilization despite 100% VRAM allocation. The GPUs are busy holding model weights in memory but rarely saturating their compute capacity.

This research evaluates approaches to maximize GPU utilization through dynamic scheduling, focusing on technologies that work with consumer GPUs (no MIG, no datacenter-only features) at one-person-operable scale.

---

## Current Allocation

| GPU | Node | VRAM | Service | Utilization |
|-----|------|------|---------|-------------|
| GPU 0 (5070 Ti) | Node 1 | 16 GB | vLLM Qwen3-32B-AWQ TP=4 | 100% VRAM allocated, ~10-27% compute |
| GPU 1 (5070 Ti) | Node 1 | 16 GB | vLLM Qwen3-32B-AWQ TP=4 | 100% VRAM allocated, ~10-27% compute |
| GPU 2 (5070 Ti) | Node 1 | 16 GB | vLLM Qwen3-32B-AWQ TP=4 | 100% VRAM allocated, ~10-27% compute |
| GPU 3 (4090) | Node 1 | 24 GB | vLLM Qwen3-32B-AWQ TP=4 | 100% VRAM allocated, ~10-27% compute |
| GPU 4 (5070 Ti) | Node 1 | 16 GB | vLLM Embedding (Qwen3-Embedding-0.6B) | **1.2 GB of 16 GB used** (~7% VRAM, near-zero compute) |
| GPU 0 (5090) | Node 2 | 32 GB | vLLM Qwen3-14B | 100% VRAM allocated, low compute |
| GPU 1 (5060 Ti) | Node 2 | 16 GB | ComfyUI Flux dev FP8 | Loaded on demand, idle most of the time |

**The problem is clear:** 136 GB of VRAM is statically allocated. GPU 4 on Node 1 has 14.8 GB of free VRAM doing nothing. The TP=4 pool holds weights 24/7 but only processes requests during active agent tasks. The 5060 Ti sits idle until someone generates an image.

Static allocation made sense during initial deployment. Now that the system is stable, dynamic scheduling can unlock significant capacity without adding hardware.

---

## GPU Sharing Technologies Evaluated

### MIG (Multi-Instance GPU)

**What it is:** NVIDIA's hardware-level GPU partitioning. Splits a single GPU into up to 7 isolated instances, each with dedicated compute, memory, and cache.

**Availability:** Datacenter GPUs only -- A100, A30, H100, H200, B100, B200. Consumer GPUs (RTX 4090, 5070 Ti, 5090, 5060 Ti) do not have MIG hardware. The feature requires specific silicon (SM partitioning logic) that NVIDIA deliberately excludes from GeForce products.

**Verdict: Not applicable.** None of Athanor's GPUs support MIG. This is a hardware limitation, not a software one.

**Source:** [NVIDIA MIG User Guide -- Supported GPUs](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/index.html#supported-gpus)

---

### MPS (Multi-Process Service)

**What it is:** NVIDIA's CUDA MPS allows multiple CUDA processes to share a single GPU concurrently, multiplexing their kernels onto the same hardware. Replaces the default time-slicing behavior (where processes take turns) with true concurrent execution.

**Availability:** Compute capability 3.5+ for basic MPS, Volta+ (sm_70+) for full features. All Athanor GPUs qualify:
- RTX 5070 Ti: sm_120 (Blackwell)
- RTX 4090: sm_89 (Ada Lovelace)
- RTX 5090: sm_120 (Blackwell)
- RTX 5060 Ti: sm_120 (Blackwell)

**How it works:**
- An `nvidia-cuda-mps-control` daemon runs on the host
- Client CUDA processes connect to the daemon instead of the GPU driver directly
- The daemon multiplexes their work onto the GPU's SMs
- Maximum 48 clients on Volta+ GPUs
- Clients share GPU memory address space (no hardware isolation)

**The catch on consumer GPUs:** Pre-Volta consumer GPUs have no memory protection between MPS clients. A segfault in one process can corrupt another's memory. On Volta+ (which includes all our GPUs), there is limited memory protection, but it is not full hardware isolation like MIG provides. A rogue CUDA kernel can still cause GPU-wide faults.

**Practical concern for vLLM:** vLLM already manages its own GPU memory via PagedAttention and manages concurrency via continuous batching. Running multiple vLLM instances on the same GPU via MPS would create two competing memory managers -- each trying to allocate VRAM without awareness of the other. This is a recipe for OOM crashes.

**Verdict: Not recommended for production multi-tenant vLLM.** MPS is designed for HPC workloads (e.g., many small CUDA programs sharing a GPU), not for inference engines that already manage their own memory. The lack of memory isolation on consumer GPUs makes it unsuitable for running independent services on the same GPU.

**Sources:**
- [NVIDIA MPS Documentation](https://docs.nvidia.com/deploy/mps/index.html)
- [NVIDIA MPS Design Guide](https://docs.nvidia.com/deploy/pdf/CUDA_Multi_Process_Service_Overview.pdf)
- [MPS on consumer GPUs -- Reddit discussion](https://www.reddit.com/r/LocalLLaMA/comments/1b45y8e/nvidia_mps_for_multiple_llm_instances/)

---

### vLLM Production Stack (vllm-stack)

**What it is:** NVIDIA's reference deployment of vLLM on Kubernetes, using the GPU Operator, KServe, and Kubernetes-native scheduling.

**Why it exists:** Provides autoscaling, health checking, model versioning, and multi-tenant GPU scheduling -- all the things a production ML platform needs.

**Why not for Athanor:** Requires a full Kubernetes cluster. Athanor runs Docker Compose on bare metal. Introducing Kubernetes to manage 7 GPUs across 2 nodes violates the one-person scale filter decisively. Kubernetes is a full-time job. Shaun has a day job.

**Verdict: Overkill.** The operational overhead of Kubernetes exceeds the benefit of its GPU scheduling for this scale.

**Source:** [vLLM Production Stack -- GitHub](https://github.com/vllm-project/production-stack)

---

### Ray Serve

**What it is:** A scalable model serving framework built on Ray, used by many companies for multi-model GPU serving. vLLM uses Ray internally for multi-node tensor parallelism.

**Why not for Athanor:** Ray is a distributed computing framework designed for clusters. Running a Ray cluster for 2 nodes is like buying a semi truck to move a couch. The operational complexity (Ray head node, worker nodes, autoscaler, dashboard, GCS) is disproportionate to the scale. vLLM already uses Ray internally for TP coordination -- adding Ray Serve on top adds a layer of abstraction with no proportional benefit.

**Verdict: Wrong scale.** Ray Serve solves multi-team, multi-model serving across large GPU fleets. Athanor has one operator and 7 GPUs.

**Source:** [Ray Serve Documentation](https://docs.ray.io/en/latest/serve/index.html)

---

### SLURM

**What it is:** The dominant job scheduler for HPC clusters. Manages GPU allocation via `gres` (generic resources), supports preemption, job queues, fair-share scheduling.

**Why not for Athanor:** SLURM is designed for multi-user HPC environments with hundreds to thousands of GPUs. It requires a controller node, a database (slurmdbd), user accounting, and cgroup configuration. The mental model is batch jobs submitted to a queue -- not interactive inference behind an API. Athanor's workload is "always-on inference with dynamic load," not "submit job, wait for allocation."

**Verdict: Wrong paradigm.** SLURM manages batch workloads for multi-user clusters. Athanor needs dynamic inference scheduling for a single operator.

**Source:** [SLURM Documentation](https://slurm.schedmd.com/documentation.html)

---

### NVIDIA Dynamo

**What it is:** NVIDIA's inference orchestration framework (open-sourced February 2025). Designed for disaggregated serving -- separating prefill (prompt processing) and decode (token generation) phases across different GPU pools. Uses NATS for messaging, etcd for state, and a custom planner for GPU routing.

**Why not for Athanor:** Dynamo's architecture assumes a large GPU fleet where prefill and decode can be physically separated across different machines. With 7 consumer GPUs, there aren't enough GPUs to meaningfully disaggregate phases. The infrastructure dependencies (NATS, etcd, planner service) add operational complexity without proportional benefit at this scale. Additionally, Dynamo targets datacenter GPUs with NVLink/NVSwitch -- consumer PCIe-only setups are not a tested configuration.

**Verdict: Wrong scale.** Dynamo solves GPU fleet orchestration for inference at datacenter scale. Overkill for 7 GPUs.

**Source:** [NVIDIA Dynamo -- GitHub](https://github.com/ai-dynamo/dynamo)

---

### Custom FastAPI Orchestrator

**What it is:** A purpose-built Python service (~500-1000 lines) that monitors GPU state, manages vLLM instance lifecycle via Sleep Mode, and routes requests based on availability and priority.

**Components:**
- `pynvml` for real-time GPU state (utilization, VRAM, temperature, power draw)
- Docker SDK for Python for container lifecycle management (start, stop, health check)
- vLLM Sleep Mode API for model lifecycle (sleep/wake without container restart)
- FastAPI for the orchestrator's own API (status, manual overrides, health)
- Prometheus client for metrics export (integrates with existing DCGM/Grafana stack)

**Why it fits:**
- Single Python file, debuggable with `curl`
- Uses tools already in the stack (Docker, Prometheus, vLLM)
- No new infrastructure dependencies
- Shaun can read, understand, and modify every line
- Fails visibly (HTTP errors, Prometheus alerts) -- no silent failures

**Verdict: Right solution at this scale.** Simple enough to understand, powerful enough to solve the problem.

---

## Key Discovery: vLLM Sleep Mode (v0.10.0+)

vLLM introduced native Sleep Mode in v0.10.0, designed specifically for the problem Athanor has: models that are loaded 24/7 but only serve requests intermittently.

### How It Works

Sleep Mode has two levels:

**Level 0 -- VRAM Retained (Compute Sleep):**
- Model weights stay in VRAM
- GPU compute resources are released (CUDA contexts freed)
- Wake time: ~0.1 seconds
- Use case: Short idle periods (minutes). Frees compute for other CUDA processes on the same GPU while keeping the model warm.

**Level 1 -- CPU Offload (Deep Sleep):**
- Model weights are offloaded from VRAM to CPU RAM
- VRAM is fully freed for other workloads
- Wake time: 0.6-0.8 seconds (limited by PCIe bandwidth for weight transfer)
- CPU RAM required: ~equal to model size (Qwen3-32B-AWQ = ~18 GB in system RAM)
- Node 1 has 224 GB DDR4 -- can hold multiple models in CPU RAM simultaneously
- Use case: Longer idle periods (>30 min). Fully frees the GPU.

### API

```bash
# Put model to sleep (Level 1 = full VRAM offload)
curl -X POST http://localhost:8000/sleep?level=1

# Wake model up
curl -X POST http://localhost:8000/wake_up

# Check if model is sleeping
curl http://localhost:8000/is_sleeping
```

### Tensor Parallelism Compatibility

Sleep Mode works with tensor-parallel deployments. When a TP=4 vLLM instance sleeps, all 4 GPUs offload their shard of the weights to CPU RAM. When it wakes, all 4 GPUs reload simultaneously. The 0.6-0.8s wake time applies to the TP=4 case -- all shards load in parallel, so wake time does not scale linearly with GPU count.

### What This Enables for Athanor

1. **Node 1 TP=4 (Qwen3-32B-AWQ):** Sleep during extended idle periods. Frees 4 GPUs for other workloads (fine-tuning, batch processing, alternative models). Wake sub-second when an agent sends a request.

2. **Node 1 GPU 4 (Embedding):** The 0.6B embedding model uses 1.2 GB of 16 GB VRAM. Even without Sleep Mode, this GPU is 92% free. Sleep Mode lets it fully release even that 1.2 GB when not in use. More importantly, it signals the orchestrator that this GPU is available for other work.

3. **Node 2 GPU 0 (Qwen3-14B):** Sleep when Node 2 is not handling chat/inference. Frees 32 GB VRAM on the 5090 for ComfyUI overflow, video generation experiments, or larger model loading.

**Source:** [vLLM Sleep Mode Documentation](https://docs.vllm.ai/en/latest/features/sleep_mode.html)

---

## Key Discovery: KV Cache CPU Offloading (v0.11.0+)

vLLM v0.11.0 introduced native KV cache CPU offloading, allowing the key-value cache to spill from VRAM to system RAM transparently.

### How It Works

```bash
vllm serve Qwen/Qwen3-32B-AWQ \
    --tensor-parallel-size 4 \
    --kv-connector native \
    --kv-buffer-size 16       # GB of CPU RAM for KV spillover
```

When VRAM KV cache is full, vLLM transparently moves cold KV entries to CPU RAM and brings them back when needed. This extends the effective context window without additional VRAM.

### Impact for Athanor

**Node 1 (224 GB DDR4):**
- Current: KV cache limited to ~28 GB VRAM (after model weights on 4 GPUs)
- With CPU offloading: Effective KV cache extends to ~28 GB VRAM + up to 200 GB DDR4
- Enables: Longer contexts, more concurrent requests, reduced KV evictions

**Performance characteristics:**
- Cache hit (VRAM): No change -- same speed as today
- Cache miss → CPU RAM: 2-22x TTFT improvement vs recomputing the KV cache from scratch
- The improvement is most dramatic for long prompts and multi-turn conversations with shared history -- exactly what agents do

**Cost:** Zero hardware cost. It is a configuration flag. Node 1's 224 GB DDR4 is massively underutilized (system + containers use ~20-30 GB). This turns idle RAM into inference acceleration.

**Source:** [vLLM KV Cache Offloading](https://docs.vllm.ai/en/latest/features/kv_offloading.html)

---

## GPU Orchestrator Design

### Architecture

A single FastAPI service running on Node 1 (alongside the agent server) that manages GPU lifecycle across both nodes.

```
                    ┌─────────────────────┐
                    │   GPU Orchestrator   │
                    │   (FastAPI, Node 1)  │
                    └──────┬──────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  pynvml  │ │ Docker   │ │  vLLM    │
        │  (GPU    │ │ SDK      │ │  Sleep   │
        │  state)  │ │ (contrs) │ │  Mode    │
        └──────────┘ └──────────┘ └──────────┘
              │            │            │
              ▼            ▼            ▼
        ┌──────────────────────────────────┐
        │       Node 1 GPUs 0-4            │
        └──────────────────────────────────┘
        ┌──────────────────────────────────┐
        │   Node 2 GPUs 0-1 (via SSH/API)  │
        └──────────────────────────────────┘
```

### GPU Allocation Zones

| Zone | GPUs | Default Workload | Flex Policy |
|------|------|-----------------|-------------|
| **Primary Inference** | Node 1 GPUs 0-3 (3x 5070 Ti + 4090) | vLLM Qwen3-32B-AWQ TP=4 | Sleep/wake on demand. Can be fully freed for fine-tuning or alternative models. |
| **Flex 1** | Node 1 GPU 4 (5070 Ti, 16 GB) | vLLM Embedding (uses 1.2 GB) | Most underutilized GPU. Available for: secondary models, batch jobs, fine-tuning offload. Embedding can coexist with other workloads (1.2 GB footprint is tiny). |
| **Flex 2** | Node 2 GPU 0 (5090, 32 GB) | vLLM Qwen3-14B | Sleep when idle. 32 GB VRAM is the single largest GPU -- ideal for loading larger models on demand (e.g., 70B at AWQ/NVFP4). |
| **Creative** | Node 2 GPU 1 (5060 Ti, 16 GB) | ComfyUI Flux dev FP8 | Default creative workload. Reassignable to inference or batch when image gen is not in use. |

### TTL-Based Auto-Sleep

```python
# Per-GPU idle tracking
SLEEP_TTL = {
    "primary_inference": 1800,  # 30 min idle → sleep level 1
    "flex_1": 600,              # 10 min idle → sleep level 1
    "flex_2": 1800,             # 30 min idle → sleep level 1
    "creative": 900,            # 15 min idle → sleep level 1
}
```

The orchestrator tracks the last request timestamp per GPU zone. When a zone exceeds its TTL without a request, it triggers vLLM Sleep Mode (level 1, full VRAM offload). When a new request arrives, it wakes the zone (<1s) before routing the request.

### Priority-Based Preemption

When a high-priority workload needs a GPU that is occupied by a lower-priority workload:

| Priority | Workload Type | Examples | Preemption Behavior |
|----------|--------------|----------|---------------------|
| 1 (highest) | Interactive inference | Agent tasks, chat | Wakes sleeping models immediately. Cannot be preempted. |
| 2 | Agent background | Research agent, knowledge indexing | Can preempt creative and batch. Sleeps after TTL. |
| 3 | Creative | ComfyUI image generation | Can preempt batch. Sleeps after TTL. |
| 4 | Batch processing | Embedding re-index, bulk inference | Runs on available GPUs only. Preempted by anything. |
| 5 (lowest) | Training/Fine-tuning | LoRA fine-tuning jobs | Runs only when GPUs are free. Checkpoints and yields on preemption. |

### LiteLLM Integration

The orchestrator updates LiteLLM's routing dynamically:

1. When a model sleeps, the orchestrator marks it as `unavailable` in LiteLLM
2. When a request hits LiteLLM for a sleeping model, LiteLLM returns a retry-after header
3. The agent framework retries after a short delay (the model wakes in <1s)
4. Alternatively, the orchestrator can intercept requests, wake the model, then proxy the request -- adding <1s latency but requiring zero agent-side changes

Option 2 (intercept + wake) is preferable because it is transparent to all consumers. No agent code changes, no LiteLLM configuration changes. The orchestrator sits between consumers and vLLM.

### Flex GPU Scheduling

Node 1 GPU 4 (the embedding GPU) is the primary candidate for flex scheduling. With 14.8 GB of free VRAM:

**Possible secondary workloads:**
- A small inference model (e.g., Qwen3-0.6B for draft/speculative decoding) -- ~1.5 GB
- LoRA fine-tuning offload -- adapters fit in 2-4 GB
- Batch embedding re-indexing (already colocated)
- Whisper (speech-to-text) -- ~3 GB for large-v3
- A coding model for local code assistance

The embedding model (0.6B) is so small that it can coexist with almost any workload. The orchestrator just needs to reserve 1.2 GB and let the remaining 14.8 GB be scheduled freely.

---

## Immediate Wins (No Orchestrator Required)

Before building a full orchestrator, two configuration changes deliver significant value:

### 1. Enable KV Cache CPU Offloading

Add to Node 1 vLLM launch args:
```
--kv-connector native --kv-buffer-size 32
```

Impact: Extends effective KV cache by ~32 GB using idle system RAM. Zero downside, zero risk, pure upside. Can be done in the Ansible role today.

### 2. Enable Sleep Mode on Node 2 vLLM

Add to Node 2 vLLM launch args:
```
--enable-sleep-mode
```

Then add a cron job or systemd timer:
```bash
# Sleep Node 2 vLLM after 30 min idle (check every 5 min)
*/5 * * * * curl -s http://localhost:8000/metrics | grep -q 'vllm:num_requests_running 0' && \
    [ $(stat -c %Y /tmp/vllm-last-request) -lt $(( $(date +%s) - 1800 )) ] && \
    curl -X POST http://localhost:8000/sleep?level=1
```

Impact: Frees 32 GB VRAM on the 5090 during idle periods. The model wakes in <1s on next request.

---

## One-Person Scale Check

| Criterion | Assessment |
|-----------|------------|
| Can Shaun understand it? | Single Python file. FastAPI endpoints. `curl` to debug. |
| Can Shaun operate it? | Prometheus metrics visible in existing Grafana. Docker logs for troubleshooting. |
| Can Shaun debug it? | `curl http://localhost:PORT/gpu/status` shows all GPU states. pynvml errors are self-explanatory. |
| Can Shaun fix it alone? | No external dependencies. If the orchestrator crashes, vLLM instances continue running -- they just don't auto-sleep/wake. Graceful degradation. |
| New infrastructure? | None. FastAPI runs in an existing Docker container (or alongside agents). pynvml and docker-py are pip packages. |
| Failure mode? | If the orchestrator dies, the system reverts to current behavior (static allocation). No data loss, no service outage. |

---

## Implementation Phases

### Phase 1: Configuration Wins (1 hour, no new code)
- Enable KV cache CPU offloading on Node 1 vLLM
- Enable Sleep Mode on both vLLM instances
- Add idle-sleep cron on Node 2
- Validate via Prometheus/Grafana

### Phase 2: Basic Orchestrator (4-6 hours)
- FastAPI service with pynvml GPU state monitoring
- vLLM Sleep Mode API integration (sleep/wake per zone)
- TTL-based auto-sleep
- `/gpu/status` endpoint for debugging
- Prometheus metrics export
- Deploy as Docker container on Node 1

### Phase 3: Dynamic Scheduling (4-6 hours)
- Priority-based preemption logic
- LiteLLM request interception (wake-before-route)
- Flex GPU assignment for GPU 4
- Node 2 remote management via SSH/API
- Dashboard integration (GPU states visible in Athanor dashboard)

### Phase 4: Advanced Features (future, as needed)
- Model swapping (load different models on demand based on request routing)
- Fine-tuning job scheduling (submit LoRA jobs that run on idle GPUs)
- Cross-node load balancing (route inference to whichever node has capacity)
- Power management (GPU power-limit adjustment based on load)

---

## Comparison: Build vs Buy

| Approach | Complexity | Operational Overhead | Fit for Athanor |
|----------|-----------|---------------------|----------------|
| Kubernetes + vllm-stack | Very High | Full-time job | No |
| Ray Serve | High | Ray cluster ops | No |
| SLURM | High | HPC admin skills | No |
| NVIDIA Dynamo | High | Datacenter paradigm | No |
| Custom FastAPI orchestrator | Low-Medium | One Python service | **Yes** |
| Manual sleep/wake scripts | Very Low | Cron + curl | Yes (Phase 1) |

The custom orchestrator is the only option that fits the one-person scale filter while providing meaningful GPU utilization improvement. The "manual scripts" approach (Phase 1) is even simpler and delivers ~60% of the benefit with ~10% of the effort.

---

## Open Questions

1. **vLLM Sleep Mode + mixed TP (5070 Ti + 4090):** Sleep Mode documentation covers homogeneous TP. Athanor's TP=4 pool mixes 3x 5070 Ti (sm_120) + 1x 4090 (sm_89) using `--quantization awq`. Does Sleep Mode's CPU offload handle the different VRAM sizes correctly (16 GB vs 24 GB per shard)? Needs testing.

2. **Docker SDK remote access to Node 2:** The orchestrator runs on Node 1 but needs to manage containers on Node 2. Options: (a) Docker remote API over TCP (expose Docker socket on Node 2), (b) SSH + docker commands, (c) a lightweight agent service on Node 2. Option (b) is simplest and most secure.

3. **Sleep wake latency under TP=4:** The documented 0.6-0.8s is for single-GPU. With TP=4 over PCIe 4.0, all 4 GPUs reload in parallel, but the effective bandwidth is limited by the PCIe bus. With ~18 GB model (AWQ) split across 4 GPUs, each GPU reloads ~4.5 GB at ~32 GB/s = ~0.14s theoretical. Real-world overhead will be higher. Needs benchmarking.

4. **LiteLLM wake-before-route latency budget:** If the orchestrator intercepts requests and wakes sleeping models, the total added latency is: wake time + request routing. For sub-second wake, this adds <1.5s to TTFT. Is this acceptable for interactive chat? For agents (which batch calls and tolerate latency), almost certainly yes. For real-time chat, maybe not -- the solution might be to never sleep models that serve interactive chat.

---

## Recommendation

**Start with Phase 1 immediately.** KV cache CPU offloading and Sleep Mode are configuration flags on existing vLLM instances. Zero risk, zero new code, meaningful improvement. This can be done in the next Ansible convergence run.

**Build the basic orchestrator (Phase 2) as a P2 item.** The orchestrator is simple enough to build in a single session, and the payoff is significant: automated GPU lifecycle management, visibility into GPU states, and the foundation for dynamic scheduling.

**Defer Phase 3-4 until Phase 2 proves its value.** Dynamic scheduling and flex GPU assignment are powerful but add complexity. Let the basic orchestrator run for a week. If the auto-sleep/wake pattern works well and the metrics show clear utilization improvement, extend it.

**Do not adopt Kubernetes, Ray Serve, SLURM, or Dynamo.** These are solutions for organizations with dedicated platform teams managing hundreds of GPUs. Athanor has one person and 7 GPUs. The custom approach is not a compromise -- it is the correct architecture for this scale.

---

## Sources

- [vLLM Sleep Mode Documentation](https://docs.vllm.ai/en/latest/features/sleep_mode.html) -- Sleep/wake API, levels, TP compatibility
- [vLLM KV Cache Offloading](https://docs.vllm.ai/en/latest/features/kv_offloading.html) -- CPU spillover for KV cache
- [vLLM Sleep Mode PR #12605](https://github.com/vllm-project/vllm/pull/12605) -- Original implementation, design rationale
- [vLLM Sleep Mode discussion](https://github.com/vllm-project/vllm/discussions/14455) -- Community experience reports
- [pynvml -- PyPI](https://pypi.org/project/pynvml/) -- Python bindings for NVIDIA Management Library
- [Docker SDK for Python](https://docker-py.readthedocs.io/) -- Container lifecycle management
- [NVIDIA MPS Documentation](https://docs.nvidia.com/deploy/mps/index.html) -- Multi-Process Service limitations on consumer GPUs
- [NVIDIA MIG User Guide](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/index.html) -- MIG hardware requirements (datacenter only)
- [NVIDIA Dynamo -- GitHub](https://github.com/ai-dynamo/dynamo) -- Disaggregated inference orchestration
- [vLLM Production Stack -- GitHub](https://github.com/vllm-project/production-stack) -- Kubernetes-based vLLM deployment
- [Ray Serve Documentation](https://docs.ray.io/en/latest/serve/index.html) -- Scalable model serving on Ray
- [SLURM GPU Scheduling](https://slurm.schedmd.com/gres.html) -- GPU resource scheduling in SLURM
- [FastAPI Documentation](https://fastapi.tiangolo.com/) -- Modern Python web framework
- [Prometheus Python Client](https://github.com/prometheus/client_python) -- Metrics export for monitoring integration
