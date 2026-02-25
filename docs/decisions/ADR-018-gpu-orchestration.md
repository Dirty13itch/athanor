# ADR-018: Custom GPU Orchestrator

**Date:** 2026-02-25
**Status:** Accepted
**Deciders:** Shaun, Claude

## Context

7 consumer GPUs across 2 nodes are allocated but underutilized (~10-27% compute utilization). VRAM is fully allocated to always-running models, but compute is near-zero when no requests arrive. Specific inefficiencies:

- GPU 4 on Node 1 runs a 1.2GB embedding model on a 16GB card (14.8GB wasted VRAM)
- ComfyUI GPU on Node 2 is idle >95% of the time
- No mechanism to time-share GPUs between workloads
- No way to dynamically reassign freed VRAM to other tasks

## Options Evaluated

1. **MIG (Multi-Instance GPU)** -- Hardware GPU partitioning
2. **MPS (Multi-Process Service)** -- CUDA time-slicing with shared memory
3. **vLLM Production Stack** -- Official vLLM deployment with Kubernetes
4. **Ray Serve / SLURM** -- Distributed compute frameworks
5. **Custom FastAPI Orchestrator** -- Lightweight Python service with vLLM sleep mode integration

## Decision

**Option 5: Custom FastAPI orchestrator with vLLM Sleep Mode integration.**

A single Python service (~1000 lines) running on Node 1 that tracks GPU state, manages vLLM sleep/wake cycles, and coordinates container lifecycle across both nodes.

## Rationale

1. **MIG is unavailable.** Multi-Instance GPU requires A100/H100-class hardware. Consumer GPUs (5070 Ti, 5090, 4090) do not support MIG.
2. **MPS lacks isolation.** On consumer GPUs, MPS provides time-slicing but no memory isolation. A fault in one process takes down all processes sharing the GPU. Unacceptable for mixed workloads.
3. **vLLM Production Stack requires Kubernetes.** The official production deployment assumes K8s with operators, service mesh, and cluster autoscaling. Wrong scale entirely.
4. **Ray Serve and SLURM are wrong paradigm.** Ray is designed for distributed ML training clusters. SLURM is designed for HPC batch scheduling. Both add massive operational complexity for a 7-GPU homelab.
5. **Custom orchestrator fits the one-person scale filter.** A FastAPI service that Shaun can read, debug, and modify. Uses well-understood libraries (pynvml, Docker SDK, httpx). The key enabler is vLLM's Sleep Mode (v0.10.0+): models can be slept to free VRAM and woken sub-second, making temporal GPU multiplexing practical.

### vLLM Sleep Mode (key enabler)

vLLM v0.10.0+ supports sleep levels:
- **Level 1:** Offload KV cache to CPU, free ~80% of VRAM, wake in <1s
- **Level 2:** Offload model weights to CPU, free ~100% of VRAM, wake in ~5-10s

This turns static VRAM allocation into dynamic scheduling. The embedding model on GPU 4 can sleep when not in use, freeing 14.8GB for batch inference. ComfyUI can be stopped to run a second vLLM instance during off-hours.

## Implementation

### Service Architecture
- FastAPI service on Node 1, port 9100
- Single process, async event loop
- State stored in Redis (shared with meta-orchestrator, ADR-017)

### GPU State Tracking
- `pynvml` for real-time GPU metrics (utilization, VRAM, temperature, power)
- DCGM-exporter data via Prometheus API for historical trends
- Per-GPU state machine: `active | sleeping | available | reserved | offline`

### Priority-Based Scheduling
Workload priority tiers (highest to lowest):
1. **Interactive** -- User-initiated inference (chat, API calls)
2. **Agent** -- Meta-orchestrator triggered agent tasks
3. **Creative** -- ComfyUI image generation
4. **Batch** -- Bulk embedding, document processing, re-indexing
5. **Training** -- Fine-tuning, LoRA training

Higher priority workloads can preempt lower priority ones. Preemption triggers sleep (not kill) for vLLM workloads.

### vLLM Sleep/Wake Management
- REST API calls to vLLM instances: `POST /sleep` and `POST /wake`
- TTL-based auto-sleep: 30 minutes idle triggers sleep level 1
- Wake-on-request: incoming inference request wakes sleeping model before routing
- LiteLLM routing updates: dynamically add/remove model endpoints as GPUs shift

### Container Lifecycle
- Docker SDK for Python to start/stop containers on both nodes
- SSH tunnel to Node 2's Docker socket for remote management
- Workflow example: detect ComfyUI idle >2hr, stop container, launch batch vLLM instance, restore ComfyUI when creative request arrives

### KV Cache CPU Offloading
- vLLM sleep level 1 offloads KV cache to system RAM
- Node 1 has 224GB RAM, Node 2 has 128GB -- massive CPU cache capacity
- Extends effective KV cache from ~28GB VRAM to ~200GB+ system RAM
- Enables longer context retention across sleep/wake cycles

## Consequences

### Positive
- Temporal GPU multiplexing: use ComfyUI's GPU for batch jobs during idle periods
- VRAM efficiency: sleeping models free VRAM for other workloads
- KV cache CPU offloading extends effective cache capacity by ~7x
- Priority scheduling ensures interactive requests always get immediate GPU access
- Single Python file -- debuggable with curl, readable in an editor

### Negative
- Adds one Python service to Node 1 (minimal operational overhead)
- Wake latency (~1-10s depending on sleep level) adds to first-request latency after idle
- Requires monitoring to prevent resource conflicts between nodes
- Docker socket access to Node 2 needs SSH tunnel (adds network dependency)

### Observability
- `curl localhost:9100/status` for full GPU state across both nodes
- Prometheus metrics: GPU utilization, sleep/wake events, preemption counts, scheduling latency
- Dashboard integration: GPU state visualization, workload queue, scheduling history
- Alerting: GPU temperature, failed wake attempts, scheduling conflicts
