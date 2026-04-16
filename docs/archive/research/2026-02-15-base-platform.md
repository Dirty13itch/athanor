# Base Platform: OS + Workload Management

> Historical note: archived research retained for ADR-001 decision history. Current deployment and topology truth live in the registries, status docs, and generated reports.

**Date:** 2026-02-15
**Status:** Complete — recommendation ready for review
**Supports:** ADR-001 (Base Platform)
**Sources:** See inline citations throughout. Raw research in companion docs.

---

## The Question

What operating system and workload management model should Athanor use on its compute nodes?

This is the most consequential architectural decision. It determines:
- How every service gets deployed, updated, and debugged
- How NVIDIA GPUs are accessed by containers and applications
- How multiple nodes are managed (together or independently)
- What Shaun's daily operational experience looks like
- How easy it is to add new workloads in the future

## Evaluation Criteria

Derived from Athanor's principles (VISION.md):

1. **One-person maintainable** — Can Shaun understand, operate, debug, and fix this alone at 2am?
2. **Open scope** — Does this make it easy to add new workloads without rearchitecting?
3. **Practical over pure** — Does this work well in practice, not just in theory?
4. **GPU-first** — Does this handle NVIDIA GPUs (especially Blackwell) without friction?
5. **Sovereignty** — Does this keep control local without depending on external services?

## Hardware Context

This decision governs the compute nodes. VAULT (Unraid) and DEV (Windows) are fixed — their role in the full system is addressed in ADR-002 through ADR-004. The historical hardware ledger is in `docs/archive/hardware/hardware-inventory.md`, and current hardware truth is tracked in `config/automation-backbone/hardware-inventory.json` plus `docs/operations/HARDWARE-REPORT.md`.

| Node | CPU | RAM | GPUs | Role |
|------|-----|-----|------|------|
| Node 1 | EPYC 7663 56C/112T | 224 GB DDR4 ECC | 4x RTX 5070 Ti (64 GB VRAM) | Heavy multi-GPU compute |
| Node 2 | Ryzen 9 9950X 16C/32T | 128 GB DDR5 | RTX 5090 + RTX 4090 (56 GB VRAM) | Creative, rendering, secondary compute |

Both currently have Ubuntu Server 24.04.4 LTS installed (for auditing). This is not a committed choice.

The base platform must be compatible with VAULT (Unraid, Docker, NFS/SMB storage, 164 TB array) as a peer in the unified system. Detailed integration is addressed in later ADRs.

---

## Critical Constraint: NVIDIA Blackwell on Linux

This finding shapes the entire decision. The RTX 5070 Ti and RTX 5090 are Blackwell-architecture GPUs with specific Linux requirements.

### Hard Requirements

| Requirement | Detail | Source |
|-------------|--------|--------|
| Driver version | 570.86.16+ (open kernel modules) | [NVIDIA Dev Forums](https://forums.developer.nvidia.com/t/rtx-50-series-blackwell-gpu-drivers-on-linux/335669) |
| Kernel module type | **Open modules mandatory** — NVIDIA dropped proprietary module support for Blackwell entirely | [Medium guide](https://medium.com/@ttio2tech_28094/how-to-install-rtx-5090-5080-5070-ti-5070-drivers-on-linux-detailed-guide-d7069c7a0db7) |
| Kernel version | 6.11+ recommended | [Linux Mint Forums](https://forums.linuxmint.com/viewtopic.php?t=440870) |
| CUDA version | 12.8+ for Blackwell compute capability (sm_120) | [NixOS/nixpkgs #406675](https://github.com/NixOS/nixpkgs/issues/406675) |
| PyTorch | 2.7.0+ for RTX 5090 | Same source |
| Container Toolkit | NVIDIA Container Toolkit supports Docker, containerd, Podman via CDI | [NVIDIA CTK docs](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) |

### Installation Reality

Testing across 6 distros found that **only Manjaro and Windows installed NVIDIA drivers without problems**. Every other distro required manual intervention. This is the bleeding edge of hardware support — the driver path matters. ([NVIDIA Dev Forums](https://forums.developer.nvidia.com/t/install-of-rtx-5070-ti-problematic-on-linux/331240))

### What This Eliminates

- **Fedora CoreOS** — No official NVIDIA GPU support. GPU Operator doesn't support FCOS. Community workarounds are fragile and kernel-version-dependent. Dealbreaker. ([Fedora Discussion](https://discussion.fedoraproject.org/t/can-you-run-nvidia-gpu-workloads-on-fcos/35090))
- **Debian 12** — Kernel 6.1 is too old. Would need backports kernel at minimum.
- **Any OS with an old kernel** — 6.11+ is the floor for reliable Blackwell support.

---

## OS Candidates

Four viable candidates remain after the Blackwell filter. One eliminated outright.

### Ubuntu Server 24.04 LTS — The Known Path

| Factor | Assessment |
|--------|-----------|
| Kernel | 6.17 (HWE as of 24.04.4, released Feb 12, 2026) |
| Support life | 5 years standard, 10 years with Ubuntu Pro |
| NVIDIA path | `graphics-driver-ppa` → `apt install nvidia-driver-570-open`. Well-documented. |
| Container Toolkit | Fully tested on 24.04. Docker + NVIDIA CTK is the most-documented path in existence. |
| Maintenance | Low. `apt update && apt upgrade`. HWE kernel updates arrive automatically in point releases. |
| Community | Largest. Every self-hosted app documents Ubuntu install steps first. |
| Downsides | `snapd` bloat (~80MB RAM, removable). Higher base memory than Debian (~147MB vs ~67MB per base install). PPA required for Blackwell drivers. |

**Why it's strong:** The NVIDIA driver story is the best of any distro. The PPA path is well-documented, the Container Toolkit is first-class, and when something breaks at 2am, the answer is on StackOverflow. Five-year LTS means no forced upgrades.

**Why it might not win:** It's the boring choice. No declarative config, no atomic rollbacks, no infrastructure-as-code. Managing two nodes means managing two nodes independently (or adding Ansible).

Sources: [Atomic Object guide](https://spin.atomicobject.com/nvidia-rtx-50-ubuntu/), [Ubuntu HWE lifecycle](https://ubuntu.com/kernel/lifecycle), [Deployn benchmarks](https://deployn.de/en/blog/docker-benchmark-ubuntu-debian/)

### Debian 13 (Trixie) — The Leaner Path

| Factor | Assessment |
|--------|-----------|
| Kernel | 6.12 LTS |
| Support life | 3 years full + 2 years LTS (to ~2030) |
| NVIDIA path | `nvidia-open-kernel-dkms` from trixie-backports. More manual than Ubuntu. |
| Container Toolkit | Supported (Docker + Podman). |
| Maintenance | Very low. Debian stable is "set and forget." Lightest base footprint. |
| Community | Very large, very mature. Foundation of Ubuntu and Proxmox. |
| Downsides | NVIDIA driver setup more manual. SHA1 signature rejection since Feb 2026 complicates NVIDIA repo use. Less beginner-friendly docs. |

**Why it's strong:** Leanest base install, rock-solid stability, no corporate agenda, no snap. Knowledge transfers directly to Proxmox if we ever want it.

**Why it might not win:** NVIDIA driver path is clunkier. Kernel 6.12 is adequate but not as fresh as Ubuntu's 6.17 HWE. Same "manage each node independently" limitation as Ubuntu.

Sources: [Debian 13 release](https://www.debian.org/News/2025/20250809), [Server World — Debian 13 NVIDIA](https://www.server-world.info/en/note?f=1&os=Debian_13&p=nvidia)

### NixOS 25.11 — The Declarative Path

| Factor | Assessment |
|--------|-----------|
| Kernel | Varies by nixpkgs (latest stable kernels available) |
| Support life | 7 months per release (must upgrade every cycle) |
| NVIDIA path | Declarative: `hardware.nvidia.open = true` in configuration.nix. Clean. |
| Container Toolkit | Supported. Docker and Podman both available declaratively. |
| Maintenance | **Very high initial investment, very low ongoing.** Entire system defined in `.nix` files in a git repo. Atomic rollbacks built in. |
| Multi-node | **Excellent.** Single config repo defines all nodes. Deploy changes to all nodes from one place. |
| Community | Large and growing (2,742 contributors to 25.11 alone). Documentation improving but still a weak spot. |
| Downsides | Steepest learning curve of any option ("a mountain"). Nix language is unique. 7-month support window. CUDA/ML packages may lag for newest GPUs. Daily friction for simple tasks during learning phase. |

**Why it's strong:** This is the only candidate that solves the multi-node management problem natively. One git repo defines both nodes. Change a config, rebuild, deploy. Atomic rollback if it breaks. No Ansible, no manual SSH-into-each-box. The NVIDIA driver setup is cleaner than Ubuntu's (declarative, not PPA-based). Once learned, it dramatically reduces operational burden.

**Why it might not win:** The learning curve is real. Multiple experienced users describe months of frustration before it "clicks." The 7-month support window means mandatory upgrades twice a year. And when something goes wrong with a Nix expression, debugging is unlike anything else in Linux.

Real user quotes:
- "In just 10 months of using NixOS, the gains made on Linux far exceeded those of the past three years." ([This Cute World](https://thiscute.world/en/posts/my-experience-of-nixos/))
- "Once NixOS clicks, you'll never want to manage infrastructure any other way" ([Alex Rosenfeld](https://blog.arsfeld.dev/posts/2025/06/10/managing-homelab-with-nixos/))
- "The daily friction can be grating... simple things can be hard to figure out." ([Pierre Zemb](https://pierrezemb.fr/posts/nixos-good-bad-ugly/))

Sources: [NixOS 25.11 release](https://nixos.org/blog/announcements/2025/nixos-2511/), [NixOS Wiki — NVIDIA](https://wiki.nixos.org/wiki/NVIDIA), [Virtualization Howto](https://www.virtualizationhowto.com/2025/11/nixos-is-the-best-home-lab-os-you-havent-tried-yet/)

### Proxmox VE 9.x — The Virtualization Path

| Factor | Assessment |
|--------|-----------|
| Kernel | 6.12 (Debian 13 base), newer opt-in |
| Support life | Follows Debian (years) |
| NVIDIA path | **LXC:** shares host driver directly (no passthrough needed). **VMs:** VFIO passthrough, but RTX 5090 has documented stability bugs (host lockups on VM shutdown, reset issues). |
| Container runtime | LXC native + Docker inside VMs/LXC. PVE 9.1 adds OCI image support for LXC. |
| Maintenance | Moderate. Web UI simplifies many tasks, but it's another layer to understand. |
| Multi-node | Built-in clustering, migration, shared management. |
| Community | Large, active forum. Free tier fully functional. |
| Downsides | RTX 5090 VM passthrough has documented bugs. Hypervisor layer adds complexity. Memory overhead. Subscription nag. GPU passthrough to VMs adds latency vs bare metal. |

**Why it's strong:** Web UI, snapshots, backups, clustering, VM migration — all built in. LXC containers can access GPUs at near-bare-metal performance without VFIO. PVE 9.1's OCI support means you can run Docker images as LXC containers. Good if you want to run heterogeneous workloads (VMs for some things, containers for others).

**Why it might not win:** The RTX 5090 passthrough bugs are concerning — host lockups are not acceptable for a production system. And if you're primarily running containers (which Athanor likely is), Proxmox adds a hypervisor layer you don't need. The LXC GPU path is interesting but less documented than Docker + NVIDIA CTK.

Sources: [Proxmox Forum — RTX 5090 passthrough](https://forum.proxmox.com/threads/2025-proxmox-pcie-gpu-passthrough-with-nvidia.169543/), [Proxmox Forum — passthrough crashes](https://forum.proxmox.com/threads/passthrough-rtx-6000-5090-cpu-soft-bug-lockup-d3cold-to-d0-after-guest-shutdown.168424/)

### Eliminated: Fedora CoreOS

No official NVIDIA GPU support. GPU Operator doesn't support FCOS. Community workarounds exist but are fragile and kernel-version-dependent, breaking on auto-updates. For a system where GPUs are the entire point, this is a dealbreaker.

### Eliminated: Talos Linux

Kubernetes is mandatory — there is no way to run workloads without it. Whether Kubernetes is right for Athanor is a separate question (see Workload Management below), but coupling the OS choice to the orchestration choice reduces flexibility. If we want Kubernetes, we can run it on any OS. If we don't want Kubernetes, Talos is impossible. It only makes sense to choose Talos if Kubernetes is already decided — and it isn't.

---

## OS Comparison Matrix

| Factor | Ubuntu 24.04 | Debian 13 | NixOS 25.11 | Proxmox VE 9 |
|--------|-------------|-----------|-------------|--------------|
| NVIDIA Blackwell | PPA, well-documented | Backports, more manual | Declarative, clean | LXC: works. VM: buggy |
| Support life | 5 years | 5 years | 7 months | Years (Debian-based) |
| Learning curve | Low | Low-Medium | Very High | Medium |
| Multi-node mgmt | Manual / Ansible | Manual / Ansible | Single config repo | Built-in clustering |
| Rollback | No | No | Atomic, built-in | VM snapshots |
| Base memory | ~147 MB | ~67 MB | Varies | ~67 MB + Proxmox overhead |
| GPU in containers | NVIDIA CTK (best-documented) | NVIDIA CTK | NVIDIA CTK (declarative) | LXC host-driver sharing |
| Debugging at 2am | StackOverflow has the answer | Likely has the answer | Nix-specific, harder | Proxmox forums, decent |
| Infra-as-code | No (needs Ansible) | No (needs Ansible) | Native | No |

---

## Workload Management Candidates

How services, containers, and AI workloads actually run on the OS.

*Note: Detailed orchestration research still incoming. Preliminary analysis below.*

### Docker Compose on Bare Linux

The simplest multi-container model. Each node gets a `docker-compose.yml` that defines its services. No orchestration across nodes — each node is managed independently.

**Strengths:**
- Simplest mental model. One file per node, `docker compose up -d`.
- Best-documented NVIDIA GPU path (Docker + NVIDIA CTK).
- Virtually every self-hosted app provides a Docker Compose example.
- Easy to debug: `docker logs`, `docker exec`, standard Linux tools.

**Weaknesses:**
- No cross-node orchestration. Moving a service between nodes is manual.
- No automatic restart across nodes, no health-check-driven rescheduling.
- Managing many services across multiple compose files gets unwieldy at scale.
- No built-in secrets management, service discovery, or load balancing.

**One-person scale verdict:** Excellent. This is what most solo homelabbers actually use.

### Kubernetes (K3s / K0s)

Full container orchestration. Services are defined as Kubernetes resources and scheduled across nodes automatically.

**Strengths:**
- Automatic scheduling, health checks, restart, scaling.
- Service discovery and networking built in.
- Massive ecosystem (Helm charts for everything).
- K3s is lightweight (~512MB RAM) and designed for edge/small deployments.
- NVIDIA GPU Operator handles driver lifecycle in-cluster.

**Weaknesses:**
- Significant learning curve (kubectl, Helm, YAML manifests, CRDs, operators).
- Debugging is harder — more abstraction layers between you and the problem.
- Overkill for a 2-3 node homelab where you know exactly what runs where.
- When it breaks, it breaks in Kubernetes-specific ways that require Kubernetes-specific knowledge.
- etcd, API server, scheduler — more components that can fail.

**One-person scale verdict:** Marginal. K3s reduces the overhead but doesn't eliminate the conceptual complexity. The question is whether the automation benefits justify the operational complexity for 2-3 nodes.

### HashiCorp Nomad

Lighter-weight orchestrator. Schedules Docker containers (and other workloads) across nodes without Kubernetes' complexity.

**Strengths:**
- Simpler than Kubernetes (single binary, less YAML, fewer concepts).
- Multi-node scheduling without the K8s overhead.
- Supports Docker, podman, exec, and other task drivers.
- NVIDIA GPU device plugin available.
- Pairs with Consul (discovery) and Vault (secrets) but doesn't require them.

**Weaknesses:**
- Smaller ecosystem than Kubernetes (fewer pre-made job specs).
- HashiCorp license change (BSL since 2023) — not fully open source anymore.
- Less community momentum than either Docker Compose or Kubernetes.
- GPU support is less mature than Kubernetes GPU Operator.

**One-person scale verdict:** Good middle ground if you need cross-node scheduling but don't want Kubernetes. License change is a concern for sovereignty.

### Podman + systemd Quadlets

Daemonless containers managed as systemd services. No Docker daemon. Each container is a systemd unit.

**Strengths:**
- No daemon — each container is an independent process.
- Native systemd integration (start on boot, restart policies, journal logging).
- Rootless containers by default (better security).
- Quadlet files are simple and declarative.
- NVIDIA CDI support in NVIDIA Container Toolkit.

**Weaknesses:**
- Smaller community than Docker. Less documentation, fewer examples.
- No built-in multi-node orchestration.
- Some Docker Compose files need adjustment for Podman (mostly compatible but not 100%).
- GPU support via CDI is newer and less battle-tested than Docker's.

**One-person scale verdict:** Good for security-conscious setups. Similar operational simplicity to Docker Compose but with a thinner community safety net.

---

## Workload Management Comparison

| Factor | Docker Compose | K3s | Nomad | Podman Quadlets |
|--------|---------------|-----|-------|-----------------|
| Multi-node | No | Yes | Yes | No |
| GPU support maturity | Best | Good (GPU Operator) | Fair (device plugin) | Fair (CDI) |
| Learning curve | Very Low | High | Medium | Low |
| Debugging | Easy (docker logs/exec) | Hard (many layers) | Medium | Easy (journalctl) |
| Ecosystem | Massive | Massive (Helm) | Moderate | Growing |
| License | Apache 2.0 | Apache 2.0 | BSL (not OSS) | Apache 2.0 |
| Infra-as-code | Compose files | YAML manifests | HCL job specs | Quadlet unit files |
| Auto-scheduling | No | Yes | Yes | No |
| Community adoption | ~90% of homelabbers | Growing in homelab | Niche | Niche |

---

## Emerging Combinations

The OS and workload choices aren't independent. Certain combinations make more sense together:

### Ubuntu + Docker Compose (The Default)
What most homelabbers run. Maximum documentation, minimum friction, best NVIDIA GPU path. No multi-node orchestration — each node managed independently. Add Ansible if config drift bothers you.

### Ubuntu + K3s (The Orchestrated Default)
Same strong NVIDIA base, adds cross-node scheduling. K3s is lightweight enough for 2-3 nodes. But adds Kubernetes complexity. Most sensible if you genuinely need workload scheduling across nodes.

### NixOS + Docker Compose (Declarative Base, Simple Workloads)
Declarative OS management (one config repo for all nodes, atomic rollbacks) with the simplest container model. Gets the multi-node config management from NixOS without adding orchestration complexity. Steep initial learning curve but low ongoing maintenance.

### NixOS + Containers via Nix (Full Declarative)
NixOS can define containers declaratively in configuration.nix — no Docker needed. Or use Docker/Podman declaratively managed by Nix. The most "infrastructure as code" approach possible. Also the steepest learning curve.

### Proxmox + Docker in LXC (Virtualization + Containers)
Proxmox provides the management layer (web UI, snapshots, clustering). Docker runs inside LXC containers that share the host GPU. Good if you want VM capabilities alongside containers. Adds the hypervisor layer.

### Debian + Docker Compose (The Lean Default)
Like Ubuntu + Docker Compose but leaner. Less NVIDIA documentation but workable. Good if snapd and Ubuntu's overhead bother you.

---

## GPU-Specific Findings

### Hard Facts

- **Open kernel modules are mandatory** for all Blackwell GPUs (RTX 5070 Ti, 5090). NVIDIA dropped proprietary module support entirely for this architecture. This is settled across all OS choices.
- **Driver 570.86.16+** required. Kernel 6.11+ recommended. ([NVIDIA Forums](https://forums.developer.nvidia.com/t/rtx-50-series-blackwell-gpu-drivers-on-linux/335669))
- **CUDA 12.8+** required for Blackwell compute capability (sm_120). PyTorch 2.7+ required. ([NixOS/nixpkgs #406675](https://github.com/NixOS/nixpkgs/issues/406675))
- **NVIDIA Container Toolkit** works with Docker, Podman, and containerd via CDI on all viable OS candidates. ([NVIDIA CTK docs](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html))
- **Multi-GPU (4x 5070 Ti on Node 1):** No specific issues documented for bare-metal multi-GPU with open modules. The EPYC 7663 + ROMED8-2T has 7 PCIe slots — physical installation is the main constraint. Tensor parallelism in vLLM works across multiple GPUs on a single node.
- **RTX 5090 VM passthrough** has documented stability bugs on Proxmox — host lockups on VM shutdown, D3cold-to-D0 reset issues. ([Proxmox Forum](https://forum.proxmox.com/threads/passthrough-rtx-6000-5090-cpu-soft-bug-lockup-d3cold-to-d0-after-guest-shutdown.168424/))

### NixOS CUDA Lag Problem

This is the most significant finding against NixOS for Athanor:

- CUDA 12.8 was requested for nixpkgs in **February 2025**. At that time, only CUDA 12.6 was available. ([NixOS Discourse](https://discourse.nixos.org/t/cuda-12-8-support-in-nixpkgs/60645))
- The vLLM + RTX 5090 issue on NixOS (nixpkgs #406675) was filed because packaged PyTorch and vLLM versions lacked Blackwell support. A fix PR was submitted but the reporter noted they lacked hardware to verify.
- A user trying to run ComfyUI on NixOS 24.11 stable with NVIDIA couldn't get PyTorch to detect the GPU — root cause was nix-ld library path issues. ([NixOS Discourse](https://discourse.nixos.org/t/cant-get-comfyui-to-work-on-nvidia-graphics-card-nixos-24-11-stable/58612))
- **Bottom line:** NixOS CUDA/ML packages lag upstream by weeks to months. For cutting-edge GPUs, you're either waiting for nixpkgs to catch up or building custom derivations — which defeats the simplicity argument.

On Ubuntu, the same stack (driver PPA → CUDA toolkit → pip install vllm) works the same day NVIDIA publishes the driver.

---

## The Hardware-Pinning Argument

This is the key insight that simplifies the orchestration decision.

Athanor has 2 compute nodes with **very different hardware profiles**:

| | Node 1 | Node 2 |
|--|--------|--------|
| CPU | EPYC 7663 56C/112T | Ryzen 9 9950X 16C/32T |
| RAM | 224 GB DDR4 ECC | 128 GB DDR5 |
| GPUs | 4x RTX 5070 Ti (64 GB) | RTX 5090 + RTX 4090 (56 GB) |
| Strength | Multi-GPU inference, high parallelism | Single-GPU power, creative/rendering |

Most heavy workloads **can only run on one specific node**:
- 4-GPU tensor parallel inference → Node 1 only (only node with 4 GPUs)
- Large single-model inference (70B+) → Node 2's 5090 (32 GB single card) or Node 1 (64 GB split across 4)
- Image/video generation (ComfyUI) → Node 2 (5090 is fastest single GPU)
- General services (dashboards, databases, monitoring) → either node, but these are lightweight and don't need scheduling

**When workloads are physically pinned to specific hardware, automatic cross-node scheduling adds complexity without benefit.** You're not load-balancing across interchangeable workers — you're running specific workloads on specific machines. This is true whether you have 2 nodes or 20 nodes with heterogeneous GPUs.

Kubernetes, Nomad, and Docker Swarm all solve the problem of "I have N interchangeable nodes and need to distribute work." That's not this problem.

**What you actually need is:**
1. A way to define what runs on each node (Docker Compose does this)
2. A way to keep node configs in sync and reproducible (git + Ansible, or NixOS)
3. A way for services on different nodes to find each other (DNS, or a simple overlay network)

---

## Mapping Athanor's Vision to Platform Requirements

The previous sections compared candidates in the abstract. This section asks: **what does Athanor specifically need from its base platform?**

From VISION.md, Athanor's priorities (in order):

1. **Unification** — one system, not scattered tools. Services aware of each other, queryable from a central interface, accessible to agents that work across domains.
2. **The craft** — the building is the reward. The platform should be something worth building on.
3. **Capability** — force multiplier. AI inference, creative tools, agents, game dev.
4. **Sovereignty** — local-preferred, no vendor lock-in, uncensored inference.

### Requirement 1: AI-First GPU Support

> "AI is what makes Athanor more than a homelab. Everything else is supporting infrastructure." — VISION.md

Athanor's core mission is AI. Local inference with uncensored models. ComfyUI image generation. Video generation. Real-time AI for EoBQ gameplay. Agents that call inference endpoints continuously.

All of this runs on NVIDIA GPUs — specifically, bleeding-edge Blackwell GPUs (5070 Ti, 5090) that need:
- Open kernel modules (mandatory for Blackwell)
- CUDA 12.8+ (sm_120 compute capability)
- PyTorch 2.7+ (Blackwell support)
- vLLM latest (Blackwell optimizations)
- NVIDIA Container Toolkit (GPU access in containers)

**This is the single most important platform requirement.** If the OS makes GPU/CUDA setup harder, it directly conflicts with Athanor's reason for existing.

| Platform | How it handles this |
|----------|-------------------|
| Ubuntu 24.04 | PPA → `apt install nvidia-driver-570-open` → NVIDIA CTK. Best-documented path. Works same-day when NVIDIA publishes drivers. |
| Debian 13 | Backports, more manual. Workable but more friction. |
| NixOS | Declarative (`hardware.nvidia.open = true`), clean when it works. **But:** CUDA 12.8 was requested in nixpkgs Feb 2025 and only 12.6 was available. vLLM + RTX 5090 had compatibility issues (nixpkgs #406675). Packages lag upstream by weeks to months. |
| Proxmox | LXC shares host driver (works). VM passthrough has documented 5090 crash bugs. |

**Verdict:** Ubuntu wins clearly. For a system whose entire purpose is AI on bleeding-edge GPUs, the OS with the fastest, most reliable NVIDIA driver path is the right one.

### Requirement 2: Unification Across Nodes

> "There should be an integration layer that lets the pieces be aware of each other, queryable from a central interface, and accessible to AI agents that work across domains." — VISION.md

Athanor's agents span the whole system:
- Media agent talks to Plex on VAULT **and** inference on Node 1
- Creative agent uses ComfyUI on Node 2 **and** may fetch assets from VAULT
- Dashboard queries services on all nodes
- Chat interface routes to inference, triggers agents, queries state

This means services on Node 1, Node 2, and VAULT need to discover and communicate with each other over the network.

**Does this require cross-node orchestration (K8s, Nomad)?** No. Here's why:

The services that need to talk to each other do so via **HTTP APIs**. vLLM exposes a REST API. Plex has an API. Home Assistant has an API. ComfyUI has an API. The "integration layer" VISION.md describes is an application-level concern — a dashboard or agent framework that knows which services exist and where to reach them. The base platform just needs to run those services and let them reach each other over the network.

For 2-3 nodes, "service discovery" is: a config file that maps service names to addresses. Or a simple DNS setup. Or even just environment variables in compose files. Consul, etcd, and Kubernetes service meshes solve this problem at scales of hundreds of services — Athanor will have dozens at most, and the addresses don't change often.

| Platform | How it handles cross-node |
|----------|--------------------------|
| Docker Compose (per node) | Services find each other via IPs/hostnames in compose env vars. Manual but simple and transparent. |
| K3s | Built-in service discovery, DNS, load balancing. Powerful but adds significant complexity for a 2-3 node system. |
| Nomad | Consul integration for discovery. Lighter than K8s but still another system to operate. |
| NixOS | Same as Docker Compose — no inherent service discovery advantage. |

**Verdict:** Docker Compose per node with explicit service addresses. The unification happens at the application layer (dashboard, agent framework), not the infrastructure layer. This keeps the base platform simple and puts the integration logic where it belongs — in code we write and control.

### Requirement 3: Open Scope — Easy to Add New Things

> "New workloads, new agents, new services, new ideas will emerge over time. The architecture must make it easy to add new capabilities without rearchitecting what already exists." — VISION.md

Adding a new service to Athanor should be trivial: write a few lines of config, `docker compose up -d`, done.

| Platform | Adding a new service |
|----------|---------------------|
| Docker Compose | Add entry to `docker-compose.yml`, run `docker compose up -d`. Nearly every self-hosted app provides a compose example. |
| K3s | Write a Kubernetes manifest or find a Helm chart. Apply with kubectl. More ceremony, but large ecosystem. |
| Nomad | Write an HCL job spec. Less ecosystem than K8s. |
| NixOS containers | Define in `configuration.nix`, rebuild. Clean but Nix-specific. |

**Verdict:** Docker Compose is the path of least resistance. Every self-hosted app documents Docker install steps first. The ecosystem is massive. No orchestrator to appease, no manifest format to learn beyond basic YAML.

### Requirement 4: One-Person Maintainable at 2am

> "If the system requires a team to operate, it's overengineered. Every component must be understandable, debuggable, and fixable by Shaun alone." — VISION.md

When something breaks, the debugging path matters:

| Platform | 2am debugging |
|----------|---------------|
| Ubuntu + Docker | `docker logs`, `docker exec`, `journalctl`, StackOverflow. The most-answered-questions stack in existence. |
| NixOS | Nix evaluation errors, derivation debugging, nix-specific tooling. Smaller community, nix-specific knowledge required. |
| K3s | `kubectl logs`, `kubectl describe`, CrashLoopBackOff, pod scheduling failures. K8s-specific failure modes. |
| Proxmox | Proxmox forums, LXC/QEMU debugging, passthrough troubleshooting. |

**Verdict:** Ubuntu + Docker. Not because the others are bad, but because when you're alone and something is broken, the size and quality of the community that's had the same problem before is the deciding factor.

### Requirement 5: The Craft

> "The process of building Athanor is as valuable as the system itself." — VISION.md

This is where NixOS has a genuine appeal — the declarative paradigm is intellectually interesting, and the "one config repo defines the whole system" concept is elegant.

But the craft of Athanor isn't the craft of the OS layer. It's the craft of:
- The dashboard (design, UX, the Cormorant Garamond aesthetic)
- The agent framework (orchestration, autonomy, tool access)
- EoBQ (interactive cinematic experience with AI)
- The integration layer (making everything aware of everything)

These are application-layer crafts. The OS is the foundation — it should be solid and invisible, not the thing you're tinkering with. Time spent debugging Nix expressions is time not spent building the agents, the dashboard, the game.

**Verdict:** The platform that gets out of the way fastest lets the real craft happen. That's Ubuntu + Docker.

### VAULT and the Rest of the System

VAULT (Unraid, non-negotiable) and DEV (Windows) are fixed. The base platform decision is about the compute nodes. But the choice must be **compatible** with a heterogeneous system where containers on different nodes (with different OSes and management tools) communicate via HTTP APIs and shared storage.

Ubuntu + Docker Compose satisfies this — it's the same container ecosystem Unraid uses, exposing the same APIs on the same network. The details of how VAULT shares storage (ADR-003), how the network connects everything (ADR-002), and what services run where (ADR-004) are addressed in their respective ADRs using the full hardware inventory.

---

### Does NixOS offer anything Athanor can't get elsewhere?

The honest answer: **one thing — declarative node management.** One config repo, atomic rollbacks, reproducible builds. This is genuinely valuable and not available on Ubuntu without significant tooling (Ansible approximates it but isn't truly declarative).

But Athanor can get a good-enough version of this with:
- Git repo containing all compose files and Ansible playbooks
- Ansible for pushing config to both nodes
- Docker Compose for defining services

It's not as elegant as NixOS. But it works, it's well-understood, and it doesn't come with the CUDA lag problem or the learning curve. For 2 heterogeneous nodes, the configs are different anyway — the "one config for everything" promise of NixOS is less relevant when the nodes are fundamentally different.

If Athanor grows to 5+ nodes, or if the Nix ecosystem matures its CUDA/ML support, this calculus changes. But starting from NixOS when the primary use case is bleeding-edge GPU inference is optimizing for the wrong thing.

---

## Recommendation

**Ubuntu Server 24.04 LTS + Docker Compose + Ansible**

Evaluated against Athanor's actual vision and requirements:

| Athanor Requirement | How This Satisfies It |
|---------------------|----------------------|
| **AI-first** | Best NVIDIA driver path. PPA → `apt install nvidia-driver-570-open` → NVIDIA CTK → `docker run --gpus all`. Same-day support when NVIDIA publishes new drivers. |
| **Unification** | Services on each node communicate via HTTP APIs. Dashboard and agent framework (built by us) provide the integration layer. Service addresses managed in compose env vars and a shared config. |
| **Open scope** | Adding a service = adding a compose entry. Massive ecosystem of pre-built Docker images for every self-hosted app. |
| **Craft** | Platform gets out of the way so craft energy goes into dashboard, agents, EoBQ, and the integration layer — not the OS. |
| **Sovereignty** | All open source (Apache 2.0). No BSL licenses. No cloud dependencies. Full local control. |
| **One-person at 2am** | Most documented stack in existence. Every problem has a StackOverflow answer. |
| **Agent communication** | Agents make HTTP calls to services across nodes. No special infrastructure needed — just network connectivity and known endpoints. |
| **Creative pipeline** | Docker + NVIDIA CTK is the most tested path for ComfyUI, vLLM, and Wan2.x containers with GPU access. |

### What this looks like in practice

```
athanor/
  ansible/
    inventory.yml          # Node 1, Node 2, VAULT IPs and SSH keys
    playbooks/
      common.yml           # Shared: users, firewall, SSH keys, NFS mounts
      node1.yml            # Node 1: Docker, NVIDIA drivers, multi-GPU config, NVMe
      node2.yml            # Node 2: Docker, NVIDIA drivers, 5090+4090 config
      vault.yml            # VAULT: NFS exports, firewall, non-Unraid config
  compose/
    node1/
      docker-compose.yml   # Inference services, multi-GPU workloads
    node2/
      docker-compose.yml   # Creative tools, single-GPU workloads, secondary inference
    shared/
      .env                 # Service addresses across all nodes (Node 1, Node 2, VAULT)
```

VAULT and DEV are outside this decision's scope (fixed OSes), but the compute node setup is designed to integrate with them. How the full system connects is addressed in ADR-002 (Network), ADR-003 (Storage), and ADR-004 (Node Roles).

### What we're NOT choosing, and why (from Athanor's perspective)

| Option | Why Not For Athanor |
|--------|-------------------|
| NixOS | CUDA/ML packages lag behind upstream by weeks to months. For a system whose entire purpose is AI on bleeding-edge GPUs, this is a direct conflict with the core mission. The declarative node management advantage doesn't justify the AI-first penalty. |
| Debian 13 | Viable but strictly weaker NVIDIA documentation. No advantage over Ubuntu that matters for Athanor's use cases. |
| Proxmox VE | Adds a hypervisor layer Athanor doesn't need — this is a container-primary system. RTX 5090 VM passthrough has documented crash bugs. The web UI is nice but Portainer or the custom dashboard serve the same purpose. |
| Kubernetes (K3s) | Cross-node scheduling doesn't add value when workloads are hardware-pinned (see Hardware-Pinning Argument). Adds significant complexity to debugging and operations. |
| Nomad | BSL license conflicts with sovereignty. Smaller ecosystem. Same hardware-pinning issue as K8s. |
| Podman Quadlets | Smaller community, less documentation, newer GPU path. No advantage that matters for Athanor. |

### Confidence and what needs validation

**High confidence on Ubuntu + Docker Compose.** This is well-trodden ground. The risk is low.

**Medium confidence on Ansible scope.** Ansible is the right tool for config management at this scale. But how much to automate vs. leave manual should emerge from use. Start simple — a common playbook for shared setup, per-node playbooks for hardware-specific config. Grow as needed.

**One hands-on spike before writing the ADR:**

**Install NVIDIA drivers on Node 1 (4x RTX 5070 Ti).** This is the highest-risk hardware config. Four Blackwell GPUs on an EPYC server board with open kernel modules. If this works, everything else is lower risk. If there are issues, we need to know before committing.

---

## Sources

All claims in this document are sourced inline. Key references:

- [NVIDIA RTX 50-series Linux driver thread](https://forums.developer.nvidia.com/t/rtx-50-series-blackwell-gpu-drivers-on-linux/335669)
- [NVIDIA Container Toolkit install guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- [NixOS nixpkgs vLLM/5090 issue #406675](https://github.com/NixOS/nixpkgs/issues/406675)
- [NixOS Discourse — CUDA 12.8 support](https://discourse.nixos.org/t/cuda-12-8-support-in-nixpkgs/60645)
- [Proxmox RTX 5090 passthrough bugs](https://forum.proxmox.com/threads/passthrough-rtx-6000-5090-cpu-soft-bug-lockup-d3cold-to-d0-after-guest-shutdown.168424/)
- [selfh.st 2025 Self-Hosting Survey](https://selfh.st/surveys/2025/)
- [Ubuntu HWE kernel lifecycle](https://ubuntu.com/kernel/lifecycle)
- [Atomic Object — NVIDIA RTX 50 on Ubuntu](https://spin.atomicobject.com/nvidia-rtx-50-ubuntu/)
- [Deployn — Docker benchmark Ubuntu vs Debian](https://deployn.de/en/blog/docker-benchmark-ubuntu-debian/)
- [NixOS 25.11 release notes](https://nixos.org/blog/announcements/2025/nixos-2511/)
- [Nomad BSL license change](https://www.hashicorp.com/en/blog/hashicorp-adopts-business-source-license)
- [Alex Rosenfeld — Managing homelab with NixOS](https://blog.arsfeld.dev/posts/2025/06/10/managing-homelab-with-nixos/)
- [Virtualization Howto — NixOS homelab](https://www.virtualizationhowto.com/2025/11/nixos-is-the-best-home-lab-os-you-havent-tried-yet/)
