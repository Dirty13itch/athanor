# Linux Operating Systems for Homelab/Self-Hosted Server Use

**Date:** 2026-02-15
**Status:** Raw research findings — no recommendations made
**Purpose:** Inform ADR on base OS selection for Athanor nodes

---

## Critical Cross-Cutting Finding: NVIDIA Blackwell (RTX 50 Series) on Linux

This affects every OS candidate. The RTX 5090 and RTX 5070 Ti are Blackwell-architecture GPUs. Their Linux driver situation is unique and constraining.

### Requirements
- **Driver version:** 570.86.16 minimum (open kernel modules). Current versions: 570.x and 575.x series.
- **Open kernel modules MANDATORY:** NVIDIA has dropped proprietary kernel module support for Blackwell entirely. The closed-source `.run` installer is explicitly rejected by the kernel for RTX 5090. You must use the `-open` driver variant. ([NVIDIA Developer Forums](https://forums.developer.nvidia.com/t/rtx-50-series-blackwell-gpu-drivers-on-linux/335669), [Medium guide](https://medium.com/@ttio2tech_28094/how-to-install-rtx-5090-5080-5070-ti-5070-drivers-on-linux-detailed-guide-d7069c7a0db7))
- **Kernel version:** 6.11+ recommended for proper support. ([Linux Mint Forums](https://forums.linuxmint.com/viewtopic.php?t=440870))
- **CUDA ecosystem:** Still catching up. PyTorch 2.7.0+ required for 5090 (sm_120 compute capability). vLLM and other ML frameworks need specific versions. ([NixOS/nixpkgs issue #406675](https://github.com/NixOS/nixpkgs/issues/406675))

### Installation Difficulty
Testing across multiple distros (Debian 12.10, Devuan 5.0.1, Mint 22.1, Ubuntu 25.04, Fedora 42, Manjaro 24.0.5), **only Manjaro and Windows 11 installed without problems**. All others required manual intervention. ([NVIDIA Developer Forums — 5070 Ti problematic](https://forums.developer.nvidia.com/t/install-of-rtx-5070-ti-problematic-on-linux/331240))

On Ubuntu 24.04 specifically, the 570 driver is only available via the `graphics-driver-ppa` (not default repos). Install with `apt install nvidia-driver-570-open`. ([Ubuntu RTX 50 guide](https://spin.atomicobject.com/nvidia-rtx-50-ubuntu/), [GitHub gist](https://gist.github.com/LogCreative/71c78d90b5317f5468413b374b8bbc21))

On Debian 13, driver packages from the trixie-backports repo (`nvidia-open-kernel-dkms`) work. However, since 2026-02-01, Debian 13 rejects SHA1 signatures used in NVIDIA's Debian-12 repo, complicating cross-repo installs. ([Server World — Debian 13 NVIDIA](https://www.server-world.info/en/note?f=1&os=Debian_13&p=nvidia))

### NVIDIA Container Toolkit
Supports Docker, containerd, CRI-O, and Podman. Available for Ubuntu 24.04 and Debian 13. Uses CDI (Container Device Interface) for Podman. ([NVIDIA Container Toolkit docs](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html))

---

## 1. Ubuntu Server 24.04 LTS (Noble Numbat)

### Version & Release
- **Current:** 24.04.4 LTS (released February 12, 2026)
- **Kernel:** 6.8 (GA), 6.17 (HWE as of 24.04.4). Next HWE in August 2026 brings 6.20/7.0.
- **Support:** Standard until April 2029. Extended (Ubuntu Pro) until 2034/2036.

Sources: [OMG Ubuntu — 24.04.4 HWE](https://www.omgubuntu.co.uk/2026/02/ubuntu-24-04-4-lts-hwe-now-available), [Ubuntu kernel lifecycle](https://ubuntu.com/kernel/lifecycle), [Phoronix — 24.04.4](https://www.phoronix.com/news/Ubuntu-24.04.4-LTS)

### NVIDIA GPU Support
- 570-open driver available via `graphics-driver-ppa` or `.run` installer.
- HWE kernel 6.17 provides good hardware support for Blackwell.
- NVIDIA Container Toolkit fully documented and tested on 24.04 (CUDA 12.9, toolkit 1.17.7 confirmed May 2025).
- **Gotcha:** Default repos do not include 570 driver. PPA required.

Sources: [Atomic Object guide](https://spin.atomicobject.com/nvidia-rtx-50-ubuntu/), [Lindevs — Container Toolkit](https://lindevs.com/install-nvidia-container-toolkit-on-ubuntu), [Server World — Ubuntu NVIDIA Container](https://www.server-world.info/en/note?os=Ubuntu_24.04&p=nvidia&f=3)

### Container Runtime Support
- **Docker:** First-class support. Official Docker repo for Ubuntu.
- **Podman:** Available but not default. Docker is the community standard.
- **containerd:** Supported via Docker or standalone.
- **LXD/LXC:** Canonical's own container solution, deeply integrated.

### Workload Management
- Traditional: systemd services, apt packages.
- Containers: Docker Compose, Podman quadlets, Kubernetes (snap or apt).
- Snap ecosystem for some server apps (can be removed).

### Community & Support
- Largest Linux community. Extensive documentation, tutorials, StackOverflow coverage.
- Commercial support available via Canonical/Ubuntu Pro.
- Virtually every self-hosted app documents Ubuntu install steps first.

### Maintenance Burden (Solo Operator)
- Low. `apt update && apt upgrade` handles most things.
- HWE kernel upgrades happen automatically within point releases.
- 5-year LTS means infrequent major upgrades.
- **Gotcha:** `snapd` installed by default, uses extra RAM. Can be removed but some things depend on it.
- Memory overhead: ~147MB per base VM vs ~67MB for Debian (before workloads). ([Deployn benchmark](https://deployn.de/en/blog/docker-benchmark-ubuntu-debian/))

### Pros
- Best NVIDIA driver support path (PPA + Container Toolkit well-documented)
- Largest community = easiest to troubleshoot
- 5-year LTS with HWE kernel updates
- Every self-hosted tool targets Ubuntu first

### Cons
- `snapd` bloat (removable but annoying)
- Higher base memory usage than Debian
- Canonical's commercial decisions occasionally controversial (snap push, Ubuntu Pro nags)
- PPA needed for cutting-edge NVIDIA drivers

---

## 2. Debian 12 (Bookworm) / Debian 13 (Trixie)

### Version & Release
- **Debian 12 (Bookworm):** Released June 2023. Current point release 12.10. Kernel 6.1 LTS. Support until June 2026 (full) / June 2028 (LTS).
- **Debian 13 (Trixie):** Released August 9, 2025. Current point release 13.3 (January 10, 2026). **Kernel 6.12 LTS.** Support until August 2028 (full) / June 2030 (LTS).

Sources: [Debian Trixie release](https://www.debian.org/News/2025/20250809), [9to5Linux — Debian 13](https://9to5linux.com/debian-13-trixie-is-now-available-for-download-heres-whats-new), [GamingOnLinux — kernel 6.12](https://www.gamingonlinux.com/2025/08/debian-13-trixie-released-with-linux-kernel-6-12/)

### NVIDIA GPU Support
- **Debian 12:** Kernel 6.1 is too old for good Blackwell support. Would need backports kernel.
- **Debian 13:** Kernel 6.12 is adequate (6.11+ recommended). `nvidia-open-kernel-dkms` from trixie-backports works.
- **Gotcha:** Since 2026-02-01, Debian 13 rejects SHA1 signatures from NVIDIA's Debian-12 repo. Must use trixie-native packages or backports.
- Driver v590+ drops Maxwell/Pascal/Volta support. Older GPUs need pinned driver versions.

Sources: [Server World — Debian 13 NVIDIA](https://server-world.info/en/note?f=1&os=Debian_13&p=nvidia), [NVIDIA Forums — 5090 on Debian](https://forums.developer.nvidia.com/t/5090-on-linux-debian/335639), [Debian Wiki — NVIDIA](https://wiki.debian.org/NvidiaGraphicsDrivers/)

### Container Runtime Support
- **Docker:** Officially supported on Debian 13, 12, 11. Docker's own repo.
- **Podman:** 5.4 in Debian 13. Supports Docker Compose compatibility. Systemd integration via quadlets.
- **containerd:** Available standalone or via Docker.

Sources: [Docker — Debian install](https://docs.docker.com/engine/install/debian), [Server World — Debian 13 Podman](https://www.server-world.info/en/note?os=Debian_13&p=podman&f=1)

### Workload Management
- systemd services, apt packages. Classic Linux server administration.
- No snap, no proprietary package managers.

### Community & Support
- Very large, very mature community. Debian is the foundation for Ubuntu, Proxmox, Raspberry Pi OS.
- No commercial entity controlling direction.
- Documentation is comprehensive but more technical/less beginner-friendly than Ubuntu.

### Maintenance Burden (Solo Operator)
- Very low. Debian stable is famously "set and forget."
- Packages are older but extensively tested.
- ~67MB base memory per VM (vs ~147MB Ubuntu with snapd). ([Deployn benchmark](https://deployn.de/en/blog/docker-benchmark-ubuntu-debian/))
- Major upgrades every ~2 years, well-documented upgrade path.

### Docker Performance vs Ubuntu
Benchmark results are hardware-dependent:
- On Intel shared vCPU: Debian won in memory efficiency and build time.
- On AMD EPYC dedicated vCPU: Ubuntu dominated, winning 7/8 tests with nearly double write speed.
- Practical difference is minimal for most workloads.

Source: [Deployn — Docker benchmark Ubuntu vs Debian](https://deployn.de/en/blog/docker-benchmark-ubuntu-debian/)

### Pros
- Rock-solid stability, minimal bloat
- Lower memory overhead than Ubuntu
- No corporate agenda (free project)
- Debian 13's kernel 6.12 is adequate for Blackwell
- Foundation of Proxmox (knowledge transfers)

### Cons
- NVIDIA driver installation more manual than Ubuntu (no PPA equivalent)
- Packages are older at release (frozen for stability)
- Debian 12 kernel too old for Blackwell without backports
- SHA1 signature rejection complicates NVIDIA repo use on Debian 13
- Less beginner-friendly documentation

---

## 3. NixOS (Current Stable: 25.11)

### Version & Release
- **Current stable:** NixOS 25.11 (released November 2025). EOL: 2026-06-30 (7 months support).
- **Previous:** 25.05 "Warbler" (deprecated, EOL 2025-12-31).
- **Release cadence:** Every 6 months (May and November).

Sources: [NixOS 25.11 announcement](https://nixos.org/blog/announcements/2025/nixos-2511/), [endoflife.date — NixOS](https://endoflife.date/nixos), [Phoronix — NixOS 25.11](https://www.phoronix.com/news/NixOS-25.11-Released)

### Key Stats
- 25.11 release: 2742 contributors, 59,430 commits, 7,002 new packages, 6,338 removed.
- Nixpkgs: ~760,000 total commits, ~8,000 contributors, ~38,000 .nix files.
- Among the most active projects on GitHub.

Source: [NixOS 25.11 release notes](https://nixos.org/blog/announcements/2025/nixos-2511/)

### NVIDIA GPU Support
- Open kernel modules enabled by default on driver versions after 535.
- RTX 50 series requires 570+ drivers with open modules — NixOS handles this declaratively.
- Configuration: `hardware.nvidia.open = true` and `services.xserver.videoDrivers = ["nvidia"]` in configuration.nix.
- **Gotcha:** CUDA ecosystem packages (PyTorch, vLLM) may lag behind in nixpkgs for Blackwell support.

Sources: [NixOS Wiki — NVIDIA](https://wiki.nixos.org/wiki/NVIDIA), [nixpkgs issue #406675](https://github.com/NixOS/nixpkgs/issues/406675)

### Container Runtime Support
- **Docker:** Supported via `virtualisation.docker.enable = true`. Rootless mode available.
- **Podman:** Supported as alternative (default container runtime option).
- **containerd:** Available.
- **NixOS Containers:** Native lightweight containers using systemd-nspawn. Declaratively defined.
- **Nix + Docker:** Can build Docker images using `dockerTools` without Dockerfiles. `nix-snapshotter` reduces image duplication.

Sources: [NixOS Wiki — Docker](https://wiki.nixos.org/wiki/Docker), [nix.dev — Docker images](https://nix.dev/tutorials/nixos/building-and-running-docker-images.html)

### Workload Management
- **Declarative configuration:** Entire system defined in `.nix` files. Services, packages, users, networking — all in code.
- **Atomic upgrades and rollbacks:** If an update breaks something, reboot to previous generation in seconds.
- **Git-based workflow:** Configuration lives in a git repo. Full history of every system change.
- **Flakes:** Modern dependency management (still somewhat experimental but widely used).

### Community & Support
- Growing rapidly. 2,742 contributors to latest release alone.
- Active Discourse forum, Matrix/IRC channels.
- Documentation has historically been a weakness but improving significantly.
- No commercial backing (community project under NixOS Foundation).
- **Gotcha (governance):** The project experienced governance controversy in 2024 that led to some community fragmentation.

### Maintenance Burden (Solo Operator)
- **Initial investment: VERY HIGH.** The Nix language is functional and unlike anything else. Steep learning curve described as a "mountain."
- **Ongoing maintenance: LOW once configured.** Changes are version-controlled, reproducible, and rollback-safe.
- **Multi-node management:** Excellent. Same configuration repo can define all nodes. Changes to one can be replicated to others declaratively.
- **LLM assistance:** Has significantly reduced the learning curve. You can ask for config snippets and get working results.

Sources: [Virtualization Howto — NixOS homelab](https://www.virtualizationhowto.com/2025/11/nixos-is-the-best-home-lab-os-you-havent-tried-yet/), [Pierre Zemb — 3 years of NixOS](https://pierrezemb.fr/posts/nixos-good-bad-ugly/), [Eric Cheng — NixOS homelab](https://www.chengeric.com/homelab), [Alex Rosenfeld — multi-host NixOS](https://blog.arsfeld.dev/posts/2025/06/10/managing-homelab-with-nixos/)

### Real User Experiences
- "In just 10 months of using NixOS, the gains made on Linux far exceeded those of the past three years." ([This Cute World](https://thiscute.world/en/posts/my-experience-of-nixos/))
- "Once NixOS clicks, you'll never want to manage infrastructure any other way" — user managing 30+ services across multiple hosts. ([Alex Rosenfeld](https://blog.arsfeld.dev/posts/2025/06/10/managing-homelab-with-nixos/))
- "Setting up a home server from scratch using NixOS definitely requires much more prior knowledge, patience, and effort compared to purposefully built systems." ([Mario Sangiorgio](https://www.mariosangiorgio.com/post/homelab-2024-02/))
- "The daily friction can be grating... simple things can be hard to figure out." ([Pierre Zemb](https://pierrezemb.fr/posts/nixos-good-bad-ugly/))

### Pros
- Reproducible, version-controlled infrastructure as code
- Atomic rollbacks — can't brick the system
- Multi-node management from single config repo
- Massive package collection (nixpkgs)
- NVIDIA open modules work declaratively
- Once learned, dramatically reduces maintenance

### Cons
- Steepest learning curve of any candidate
- 7-month support window per release (must upgrade regularly)
- Nix language is unique and non-transferable
- Documentation still catching up (improving but not Ubuntu-level)
- CUDA/ML ecosystem packages may lag for newest GPUs
- Some NixOS-specific friction for every "simple" task
- Governance concerns (2024 controversy)

---

## 4. Fedora Server 42 / Fedora CoreOS

### Version & Release
- **Fedora Server 42:** Released April 16, 2025. EOL: May 13, 2026 (~13 months support).
- **Fedora CoreOS:** Follows Fedora release cycle. Three streams: stable, testing, next. Auto-updating.
- **Release cadence:** Every 6 months. Each release supported for ~13 months (until 4 weeks after X+2).

Sources: [Fedora 42 download](https://www.ubuntubuzz.com/2025/04/download-fedora-42-full-editions-workstation-server-iot-included.html), [endoflife.date — Fedora](https://endoflife.date/fedora), [Lansweeper — Fedora EOL](https://www.lansweeper.com/blog/eol/fedora-linux-end-of-life/)

### NVIDIA GPU Support
- **Fedora Server:** RPM Fusion provides NVIDIA drivers. Recent kernels good for Blackwell.
- **Fedora CoreOS:** **No official NVIDIA GPU support.** NVIDIA GPU Operator does not officially support FCOS. Community workarounds exist (bootc-nvidia images, third-party driver containers) but are fragile. Driver containers are kernel-specific, conflicting with CoreOS auto-update model.

Sources: [Fedora Discussion — GPU on FCOS](https://discussion.fedoraproject.org/t/can-you-run-nvidia-gpu-workloads-on-fcos/35090), [NVIDIA GPU Operator issue #696](https://github.com/NVIDIA/gpu-operator/issues/696), [coreos/fedora-bootc-nvidia](https://github.com/coreos/fedora-bootc-nvidia)

### Container Runtime Support
- **Fedora Server:** Docker (via Moby/Docker CE repo), Podman (default, Red Hat native). Full Podman + systemd integration.
- **Fedora CoreOS:** Podman is the native container runtime. No Docker daemon by default. Uses systemd + Podman quadlets for service management.

### Workload Management
- **Fedora Server:** Traditional systemd + package management (dnf). Similar to Ubuntu/Debian.
- **Fedora CoreOS:** Ignition for first-boot provisioning. Butane configs compiled to Ignition JSON. Immutable root filesystem. Auto-updates with rollback (rpm-ostree).

Sources: [FOSDEM — CoreOS homelab](https://archive.fosdem.org/2023/schedule/event/container_fedora_coreos/), [Fedora CoreOS install guide](https://fschoenberger.dev/homelab/02-fedora-core-os-installation/)

### Community & Support
- Fedora community is large and active. Red Hat-backed development.
- CoreOS community is smaller, more specialized.
- No commercial support (community project, upstream of RHEL).
- Good documentation for Fedora Server; CoreOS docs more sparse.

### Maintenance Burden (Solo Operator)
- **Fedora Server:** Moderate. 13-month lifecycle means **mandatory upgrades every ~year**. `dnf system-upgrade` works but is a task.
- **Fedora CoreOS:** Low once configured — auto-updates handle everything. But initial setup and GPU configuration are harder.
- Both are "bleeding edge" compared to Ubuntu LTS or Debian stable.

### Pros
- Cutting-edge packages and kernel versions
- Fedora CoreOS: immutable, auto-updating, container-native
- Podman + systemd quadlets is a modern, daemonless container approach
- Good testbed for RHEL-ecosystem knowledge
- CoreOS Ignition enables reproducible provisioning

### Cons
- **13-month support lifecycle is very short** — constant upgrade treadmill
- CoreOS has **no official NVIDIA GPU support** (dealbreaker for GPU workloads)
- CoreOS NVIDIA workarounds are fragile and kernel-version-dependent
- Not an LTS distribution — inappropriate for "set and forget" servers
- Smaller community than Ubuntu/Debian for homelab use cases

---

## 5. Proxmox VE

### Version & Release
- **Proxmox VE 8.4:** Released April 2025. Based on Debian 12.10 "Bookworm". Kernel 6.8 (default), 6.14 (opt-in).
- **Proxmox VE 9.0:** Released August 5, 2025. Based on Debian 13 "Trixie". Kernel 6.12 (default), newer opt-in.
- **Proxmox VE 9.1:** Latest. Adds OCI image support for LXC, QEMU 10.1.2, LXC 6.0.5, ZFS 2.3.4.

Sources: [Proxmox VE 8.4 release](https://www.proxmox.com/en/about/company-details/press-releases/proxmox-virtual-environment-8-4), [Proxmox VE 9.0 release](https://www.proxmox.com/en/about/company-details/press-releases/proxmox-virtual-environment-9-0), [4sysops — PVE 9.1](https://4sysops.com/archives/proxmox-ve-91-create-lxc-containers-from-oci-images-granular-nested-virt-cpu-control-and-more/), [Proxmox roadmap](https://pve.proxmox.com/wiki/Roadmap)

### NVIDIA GPU Support
- **GPU Passthrough (VFIO):** Works for VMs but RTX 5090 has documented stability issues:
  - Host CPU soft lockups after VM shutdown (D3cold/D0 reset issues)
  - Multiple GPU passthrough fails with SeaBIOS (use OVMF/UEFI instead)
  - Workaround: initialize GPU with NVIDIA driver on host, unbind, then start VM
- **LXC GPU access:** No VFIO needed — LXC uses host driver directly. Must install NVIDIA driver on Proxmox host.
- **vGPU:** Not supported on consumer GeForce cards (RTX 5090 included). Professional cards only.
- **PVE 9.1:** OCI containers as LXC can access host GPU.

Sources: [Proxmox Forum — RTX 5090 passthrough tutorial](https://forum.proxmox.com/threads/2025-proxmox-pcie-gpu-passthrough-with-nvidia.169543/), [Proxmox Forum — passthrough crashes](https://forum.proxmox.com/threads/passthrough-rtx-6000-5090-cpu-soft-bug-lockup-d3cold-to-d0-after-guest-shutdown.168424/), [Level1Techs — RTX 50 reset bug](https://forum.level1techs.com/t/do-your-rtx-5090-or-general-rtx-50-series-has-reset-bug-in-vm-passthrough/228549), [Virtualization Howto — LXC GPU](https://www.virtualizationhowto.com/2025/05/how-to-enable-gpu-passthrough-to-lxc-containers-in-proxmox/)

### Container Runtime Support
- **LXC:** Native. First-class citizen in Proxmox.
- **Docker:** Run inside VMs or LXC containers (not directly on Proxmox host, though technically possible).
- **OCI images (PVE 9.1):** LXC containers can now be created from OCI/Docker images. Application containers in technology preview.
- **VMs:** Full KVM virtualization. Can run any OS inside.

### Workload Management
- Web UI for VM/container management.
- CLI tools (`qm`, `pct`, `pvesh`).
- Clustering across multiple nodes with shared storage.
- Built-in backup, snapshot, migration tools.
- HA (High Availability) features available but add complexity.

### Community & Support
- Large, active community. Extensive forum.
- Commercial support available (subscription model for enterprise repos).
- Free tier is fully functional (community repo).
- Proxmox-specific knowledge, but Debian knowledge transfers directly.

### Maintenance Burden (Solo Operator)
- **Moderate.** Web UI simplifies many tasks. But it's another layer to understand and maintain.
- Upgrades between major versions (8 -> 9) are documented but non-trivial.
- "Once you split compute away from routing and storage, a lot of things stop being crises." ([DiyMediaServer](https://diymediaserver.com/post/media-server-compute-2025/))
- Avoid Ceph and HA for solo homelab — adds complexity with limited benefit.
- Subscription nag on free tier (cosmetic but annoying).

Sources: [Victor Nava — Proxmox homelab](https://victornava.dev/2025/08/12/proxmox-for-the-home-lab/), [Dustin Rue — Proxmox thoughts](https://dustinrue.com/2024/04/thoughts-on-proxmox-and-home-lab-use/)

### Pros
- Web UI for VM/container management
- Snapshot, backup, migration built-in
- LXC containers can share host GPU (no VFIO overhead)
- PVE 9.1 OCI image support bridges Docker and LXC worlds
- Clustering across multiple nodes
- Based on Debian (familiar, stable)
- Free and open source

### Cons
- **RTX 5090 VM passthrough has documented stability bugs** (reset issues, host lockups)
- Additional layer of abstraction (hypervisor) adds complexity
- Memory overhead for Proxmox host itself
- Subscription nag on free tier
- Not needed if you're only running containers (bare metal Docker is simpler)
- GPU passthrough to VMs adds latency vs bare metal
- vGPU not available on consumer GPUs

---

## 6. Talos Linux

### Version & Release
- **Current:** Talos Linux 1.12.3 (1.12.0 released December 22, 2025).
- **Components:** Linux 6.18.8, containerd 2.2.1, etcd 3.6.7, Kubernetes 1.35.0.
- **Certified Kubernetes distribution.**

Sources: [Talos Linux releases](https://github.com/siderolabs/talos/releases), [Sidero Labs blog — Q4 2025](https://www.siderolabs.com/blog/talos-omni-q4-2025-updates/), [InfoQ — Talos Linux](https://www.infoq.com/news/2025/10/talos-linux-kubernetes/)

### NVIDIA GPU Support
- GPU support via system extensions (signed, validated per release).
- Three components: NVIDIA GPU Drivers (LTS + Production branches), Fabric Manager, Container Toolkit.
- Extensions: `nvidia-container-toolkit-production` and `nonfree-kmod-nvidia-production`.
- **Gotcha:** Standard NVIDIA GPU Operator installation doesn't work because Talos has no shell, read-only filesystem, and only allows signed kernel modules. Must use Talos-specific extensions.

Sources: [Sidero — AI workloads](https://www.siderolabs.com/blog/ai-workloads-on-talos-linux/), [Sidero docs — NVIDIA GPU](https://docs.siderolabs.com/talos/v1.9/configure-your-talos-cluster/hardware-and-drivers/nvidia-gpu-proprietary), [DeepWiki — NVIDIA GPU Support](https://deepwiki.com/siderolabs/extensions/3.1-nvidia-gpu-support)

### Container Runtime Support
- **containerd:** Only container runtime. This is a Kubernetes OS — everything runs as pods.
- **No Docker.** No Podman. No standalone container runtime.
- All workloads are Kubernetes workloads (pods, deployments, services, etc.).

### Workload Management
- **Kubernetes only.** All services run as K8s resources.
- Managed via `talosctl` API (no SSH, no shell).
- Configuration via YAML machine configs applied via API.
- Immutable, read-only root filesystem.
- Automatic updates with rollback.

### Can It Run Without Kubernetes?
- **Officially: No.** "Talos will always stay a single-purpose Kubernetes distribution."
- **Technically:** You can disable kubelet registration and use `.machine.pods` for static pods, but this is unsupported and defeats the purpose.

Source: [GitHub Discussion #10008](https://github.com/siderolabs/talos/discussions/10008)

### Community & Support
- Growing community, especially in K8s/cloud-native space.
- Sidero Labs provides commercial support (Talos Omni).
- Smaller community than general-purpose distros.
- Documentation is good for K8s-focused use cases.

### Maintenance Burden (Solo Operator)
- **If you want Kubernetes:** Low maintenance. Immutable, auto-updating, API-driven.
- **If you don't want Kubernetes:** Talos is the wrong choice. Period.
- Must learn Kubernetes ecosystem (kubectl, Helm, operators, etc.) — significant investment.
- No SSH means debugging is different (talosctl logs, talosctl dmesg, etc.).

### Pros
- Most secure option (immutable, no SSH, no shell, signed modules only)
- API-driven — fully automatable
- Auto-updating with rollback
- Purpose-built for Kubernetes — nothing extraneous
- NVIDIA GPU support via signed extensions

### Cons
- **Kubernetes is mandatory** — no alternative workload management
- No SSH, no shell — steep adjustment for traditional sysadmins
- GPU driver installation via extensions only (not standard NVIDIA path)
- Overkill if you don't need/want Kubernetes
- Smallest community of all candidates
- You had a bad experience with it previously (Kaizen project — different context, but worth noting)

---

## Community Consensus: What Self-Hosters Actually Use (2025 Survey)

The 2025 Self-Host survey (selfh.st) collected 4,081 responses:

- **81% run Linux** as their primary homelab OS.
- **Docker is dominant:** Nearly 9 out of 10 respondents use Docker for containers.
- **Most popular platforms:** Proxmox (virtualization), Ubuntu Server (general purpose), Debian (stability-focused), TrueNAS SCALE (storage + containers).
- **NixOS, Fedora CoreOS, Talos:** Niche but growing followings in technically advanced communities.

Sources: [Linuxiac — Self-hosters survey](https://linuxiac.com/self-hosters-confirm-it-again-linux-dominates-the-homelab-os-space), [Hostbor — Best home server OS 2025](https://hostbor.com/home-server-os/), [Elest.io — 2026 homelab stack](https://blog.elest.io/the-2026-homelab-stack-what-self-hosters-are-actually-running-this-year/)

### "Best Linux Distro for Homelab" Consensus (2025 Articles)
- Ubuntu Server consistently recommended for beginners and general use.
- Debian recommended for stability-focused, resource-efficient deployments.
- Proxmox recommended when you need VMs + containers with a management UI.
- NixOS called "the best homelab OS you haven't tried yet" — but with heavy caveats about learning curve.
- Fedora CoreOS mentioned for container-native setups but noted as niche.

Sources: [Matt Adam — Best distros 2025](https://mattadam.com/2025/04/29/top-linux-distros-for-home-lab-environments-what-should-you-use/), [LinuxShout — Best distros 2025](https://linux.how2shout.com/best-linux-distros-for-your-home-lab-in-2025/), [Virtualization Howto — Lightweight distros](https://www.virtualizationhowto.com/2025/10/best-lightweight-linux-distros-for-home-server/)

---

## Comparison Matrix

| Factor | Ubuntu 24.04 LTS | Debian 13 | NixOS 25.11 | Fedora 42 / CoreOS | Proxmox VE 9 | Talos 1.12 |
|--------|------------------|-----------|-------------|---------------------|--------------|------------|
| **Kernel** | 6.17 (HWE) | 6.12 LTS | Varies by nixpkgs | Latest (6.x) | 6.12 + opt-in newer | 6.18.8 |
| **Support life** | 5yr (10yr Pro) | 5yr (3+2 LTS) | 7 months | ~13 months | Follows Debian | Rolling |
| **NVIDIA Blackwell** | PPA required, works | Backports, works | Declarative, works | Server: RPM Fusion. CoreOS: **broken** | LXC: works. VM passthrough: **buggy** | Extensions, works |
| **Docker** | Yes | Yes | Yes | Yes (Server) / No (CoreOS) | Inside VMs/LXC | No |
| **Podman** | Yes | Yes (5.4) | Yes | Yes (native) | Inside VMs/LXC | No |
| **containerd** | Yes | Yes | Yes | Yes | Yes | **Only runtime** |
| **Workload model** | Traditional + containers | Traditional + containers | Declarative + containers | Traditional (Server) / Immutable (CoreOS) | VMs + LXC + containers | Kubernetes only |
| **Learning curve** | Low | Low-Medium | **Very High** | Medium (Server) / High (CoreOS) | Medium | High (K8s required) |
| **Solo maintenance** | Low | Very Low | Low (after learning) | Moderate (upgrade treadmill) | Moderate | Low (if K8s-committed) |
| **Community size** | Very Large | Very Large | Large, growing | Large (Fedora) / Small (CoreOS) | Large | Small-Medium |
| **Multi-node mgmt** | Manual or Ansible | Manual or Ansible | **Excellent** (single config repo) | Ignition (CoreOS) / Manual (Server) | **Built-in** clustering | **Built-in** (K8s) |
| **Rollback** | No (manual snapshots) | No (manual snapshots) | **Atomic** (built-in) | rpm-ostree (CoreOS) / No (Server) | VM snapshots | **Atomic** (built-in) |
| **GPU in containers** | NVIDIA Container Toolkit | NVIDIA Container Toolkit | NVIDIA Container Toolkit | **Not officially supported** (CoreOS) | LXC shares host driver | Via K8s device plugin |

---

## Raw Notes: Proxmox vs Bare Metal Discussion

Key arguments from community discussions:

**For Proxmox:**
- Snapshot/backup/restore is invaluable when experimenting
- Can run more logical nodes than physical machines
- LXC containers are near-bare-metal performance with GPU access
- Web UI simplifies management
- Clustering for multi-node

**For Bare Metal:**
- No hypervisor overhead
- Simpler architecture (fewer layers to debug)
- Direct hardware access without passthrough complexity
- Better if you're only running containers anyway
- GPU passthrough issues disappear (no passthrough needed)

**Hybrid approach mentioned by many:** Proxmox on one node for VMs/experimentation, bare metal on GPU-heavy compute nodes.

Sources: [Yo Motherboard — Bare metal vs Proxmox](https://yomotherboard.com/question/bare-metal-vs-proxmox-whats-the-best-setup-for-a-homelab/), [SimpleHomelab — Best server OS](https://www.simplehomelab.com/udms-03-best-home-server-os/), [Medium — Proxmox VMs or bare metal](https://medium.com/@PlanB./proxmox-vms-or-bare-metal-best-practices-for-building-a-high-availability-kubernetes-cluster-a993439bb17c)
