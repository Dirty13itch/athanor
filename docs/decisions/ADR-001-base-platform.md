# ADR-001: Base Platform (OS + Workload Management)

**Date:** 2026-02-15
**Status:** Accepted
**Research:** [docs/archive/research/2026-02-15-base-platform.md](../archive/research/2026-02-15-base-platform.md)
**Depends on:** Hardware inventory (complete)

---

## Context

This is the most consequential architectural decision in Athanor. It determines how every service gets deployed, updated, and debugged — how NVIDIA GPUs are accessed — how multiple nodes are managed — and what Shaun's daily operational experience looks like.

Athanor has two compute nodes with bleeding-edge Blackwell GPUs (RTX 5070 Ti, RTX 5090) that have specific Linux requirements. VAULT (Unraid) and DEV (Windows 11) are fixed — this decision governs the compute nodes only.

### Critical Constraint: NVIDIA Blackwell on Linux

| Requirement | Detail |
|-------------|--------|
| Driver version | 570.86.16+ (open kernel modules) |
| Kernel module type | **Open modules mandatory** — NVIDIA dropped proprietary module support for Blackwell entirely |
| Kernel version | 6.11+ recommended |
| CUDA version | 12.8+ for Blackwell compute capability (sm_120) |
| PyTorch | 2.7.0+ for RTX 5090 |
| Container Toolkit | NVIDIA Container Toolkit supports Docker, containerd, Podman via CDI |

This constraint eliminates Fedora CoreOS (no NVIDIA GPU support), Debian 12 (kernel too old), and Talos Linux (Kubernetes-only, couples OS to orchestration choice).

---

## Decision

### Ubuntu Server 24.04 LTS + Docker Compose + Ansible on both compute nodes.

#### Why Ubuntu

| Factor | Assessment |
|--------|-----------|
| Kernel | 6.17 (HWE as of 24.04.4, released Feb 12, 2026) |
| Support life | 5 years standard, 10 years with Ubuntu Pro |
| NVIDIA path | `graphics-driver-ppa` → `apt install nvidia-driver-570-open`. Best-documented path in existence. |
| Container Toolkit | Fully tested on 24.04. Docker + NVIDIA CTK is the most-documented GPU container path. |
| Maintenance | Low. `apt update && apt upgrade`. HWE kernel updates arrive automatically. |
| Community | Largest. Every self-hosted app documents Ubuntu install steps first. |
| 2am debugging | StackOverflow has the answer. Every problem someone else has had too. |

Ubuntu wins because **Athanor's entire purpose is AI on bleeding-edge GPUs**, and Ubuntu has the fastest, most reliable NVIDIA driver path of any Linux distribution. On Ubuntu, PPA → apt install → NVIDIA CTK → `docker run --gpus all` works the same day NVIDIA publishes a driver. On NixOS, CUDA/ML packages lag upstream by weeks to months. That's a direct conflict with Athanor's core mission.

#### Why Docker Compose

The hardware-pinning argument eliminates the need for cross-node orchestration:

| | Node 1 | Node 2 |
|--|--------|--------|
| CPU | EPYC 7663 56C/112T | Ryzen 9 9950X 16C/32T |
| RAM | 224 GB DDR4 ECC | 128 GB DDR5 |
| GPUs | 4x RTX 5070 Ti (64 GB) | RTX 5090 + RTX 4090 (56 GB) |
| Strength | Multi-GPU inference, high parallelism | Single-GPU power, creative/rendering |

Most heavy workloads **can only run on one specific node** — 4-GPU tensor parallelism → Node 1 only, ComfyUI → Node 2's 5090, etc. When workloads are physically pinned to specific hardware, automatic cross-node scheduling (Kubernetes, Nomad) adds complexity without benefit. You're not load-balancing across interchangeable workers — you're running specific workloads on specific machines.

Docker Compose provides:
- One file per node, `docker compose up -d`
- Best-documented NVIDIA GPU path (Docker + NVIDIA CTK)
- Virtually every self-hosted app provides a compose example
- Easy debugging: `docker logs`, `docker exec`, standard Linux tools

#### Why Ansible

Two heterogeneous nodes need consistent base configuration (users, SSH keys, firewall, NFS mounts, NVIDIA drivers) without manual SSH-into-each-box drift. Ansible handles this at the right scale — simple playbooks in a git repo, push to both nodes, done. Not as elegant as NixOS declarative config, but no learning curve tax and no CUDA lag.

#### Repository Structure

```
athanor/
  ansible/
    inventory.yml          # Node 1, Node 2, VAULT IPs and SSH keys
    playbooks/
      common.yml           # Shared: users, firewall, SSH keys, NFS mounts
      node1.yml            # Node 1: Docker, NVIDIA drivers, multi-GPU config
      node2.yml            # Node 2: Docker, NVIDIA drivers, 5090+4090 config
      vault.yml            # VAULT: NFS exports, firewall
  compose/
    node1/
      docker-compose.yml   # Inference services, multi-GPU workloads
    node2/
      docker-compose.yml   # Creative tools, single-GPU workloads, secondary inference
    shared/
      .env                 # Service addresses across all nodes
```

---

## What This Enables

- **Same-day GPU driver support** — when NVIDIA publishes a new driver, Ubuntu can use it immediately
- **Trivial service addition** — new service = new compose entry, `docker compose up -d`
- **Reproducible node setup** — Ansible playbooks define base state, versioned in git
- **Cross-node communication** — services find each other via HTTP APIs and explicit addresses in compose env vars
- **Massive ecosystem** — every self-hosted app documents Docker install steps first
- **One-person debuggable** — `docker logs`, `docker exec`, `journalctl`, StackOverflow

---

## Alternatives Considered

| Alternative | Why Not |
|-------------|---------|
| NixOS 25.11 | CUDA/ML packages lag upstream by weeks to months. vLLM + RTX 5090 had compatibility issues (nixpkgs #406675). PyTorch GPU detection issues reported on stable. For a system whose entire purpose is AI on bleeding-edge GPUs, same-day driver support outweighs declarative elegance. Revisit if Nix CUDA ecosystem matures. |
| Debian 13 (Trixie) | Viable but strictly weaker NVIDIA documentation. Kernel 6.12 adequate but less fresh than Ubuntu's 6.17 HWE. SHA1 signature rejection since Feb 2026 complicates NVIDIA repo use. No advantage over Ubuntu for Athanor's use cases. |
| Proxmox VE 9.x | Adds a hypervisor layer Athanor doesn't need — this is a container-primary system. RTX 5090 VM passthrough has documented host lockup bugs on shutdown. LXC GPU sharing is interesting but less documented than Docker + NVIDIA CTK. |
| Kubernetes (K3s) | Cross-node scheduling doesn't add value when workloads are hardware-pinned. Significant complexity overhead for debugging and operations. Every K8s failure is a K8s-specific failure requiring K8s-specific knowledge. |
| HashiCorp Nomad | BSL license conflicts with sovereignty principle. Smaller ecosystem. Same hardware-pinning issue as K8s. |
| Podman + systemd Quadlets | Smaller community, less documentation, newer GPU path (CDI). No advantage that matters for Athanor. |
| Talos Linux | Kubernetes-mandatory — couples OS choice to orchestration choice. Carried over from previous project (Kaizen) with zero weight in Athanor decisions. |

---

## Risks

- **Ubuntu snap bloat.** snapd uses ~80 MB RAM and runs unwanted auto-updates. Mitigated: remove snapd on first boot via Ansible (`apt purge snapd`).
- **No atomic rollback.** Ubuntu doesn't support NixOS-style rollbacks. Mitigated: Ansible makes reprovisioning fast. Docker volumes survive OS reinstall. Critical data lives on VAULT.
- **Config drift.** Two manually-managed nodes can diverge. Mitigated: Ansible playbooks define desired state, run periodically or on change. Compose files in git.
- **NVIDIA driver breakage.** New driver versions can break CUDA workloads. Mitigated: pin driver version in apt, test updates on one node before the other.

---

## Validation Required

Before accepting this ADR, one hands-on spike:

**Install NVIDIA drivers on Node 1 (4x RTX 5070 Ti).** Four Blackwell GPUs on an EPYC server board with open kernel modules is the highest-risk hardware config. If this works, everything else is lower risk. If there are issues, we need to know before committing.

---

## Sources

- [NVIDIA RTX 50-series Linux driver thread](https://forums.developer.nvidia.com/t/rtx-50-series-blackwell-gpu-drivers-on-linux/335669)
- [RTX 5090/5080/5070 Ti Linux driver install guide](https://medium.com/@ttio2tech_28094/how-to-install-rtx-5090-5080-5070-ti-5070-drivers-on-linux-detailed-guide-d7069c7a0db7)
- [NVIDIA Container Toolkit install guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- [NixOS nixpkgs vLLM/5090 issue #406675](https://github.com/NixOS/nixpkgs/issues/406675)
- [NixOS CUDA 12.8 support discussion](https://discourse.nixos.org/t/cuda-12-8-support-in-nixpkgs/60645)
- [Proxmox RTX 5090 passthrough crash bugs](https://forum.proxmox.com/threads/passthrough-rtx-6000-5090-cpu-soft-bug-lockup-d3cold-to-d0-after-guest-shutdown.168424/)
- [Atomic Object — NVIDIA RTX 50 on Ubuntu](https://spin.atomicobject.com/nvidia-rtx-50-ubuntu/)
- [Ubuntu HWE kernel lifecycle](https://ubuntu.com/kernel/lifecycle)
- [Deployn — Docker benchmark Ubuntu vs Debian](https://deployn.de/en/blog/docker-benchmark-ubuntu-debian/)
- [selfh.st 2025 Self-Hosting Survey](https://selfh.st/surveys/2025/)
