# Athanor — System Overview

*The one-page explanation of what this is, how it works, and why it exists.*

---

## What Is Athanor?

Athanor is a personal AI system built on 4 physical machines in your home. It combines:
- **Local AI models** that run on your GPUs (free, unlimited, private)
- **Cloud AI subscriptions** (Claude, ChatGPT, Gemini, etc.) for when you need the best
- **9 autonomous agents** that monitor, create, and maintain things without you
- **A creative pipeline** that generates images, video, and voice

The name comes from alchemy — an athanor is a self-feeding furnace. You set the conditions, and it does the slow continuous work of transformation.

## The Five Machines

```
FOUNDRY (.244) — The Brain
  56-core EPYC, 219GB RAM, 5 GPUs (88GB VRAM)
  Runs: Main AI models, 9 autonomous agents, GPU orchestrator
  
WORKSHOP (.225) — The Studio  
  24-core Threadripper, 125GB RAM, 2 GPUs (48GB VRAM)
  Runs: Creative model, ComfyUI image gen, Dashboard, EoBQ app
  
DEV (.189) — Mission Control
  12-core Ryzen 9, 60GB RAM, 1 GPU (16GB VRAM)
  Runs: All coding tools, embedding/search, Local-System services
  You SSH here from DESK. This is where you work.

VAULT (.203) — The Vault
  16-core Ryzen 9, 123GB RAM, 200TB storage
  Runs: ALL databases, routing, monitoring, media, 47 Docker containers
  If this goes down, everything stops.
  
DESK (.50) — Your Desk
  16-core i7, 64GB RAM, RTX 3060 12GB
  Windows workstation. SSH terminal to DEV. Browser for dashboards.
```

## How You Use It

1. Sit at DESK (Windows)
2. Open terminal → SSH to DEV → tmux session "ATHANOR"
3. Claude Code launches automatically
4. Tell it what you want
5. It figures out the best way to do it

Claude Code is your primary interface. It knows about every tool, every model, every agent in the system. When you describe a task, it either does it itself or delegates to the right tool.

## The Two Modes

**When you're working:** Claude Code (powered by Opus 4.6, the best AI model available) listens to you and orchestrates everything. It costs $200/mo flat — no per-use charges.

**When you're sleeping:** 9 autonomous agents run on FOUNDRY using local AI models (Qwen3.5, free). They check GPU health, generate images, manage media, index documents, and alert your phone if something breaks.

## What It Costs

| Category | Monthly |
|----------|---------|
| 10 AI subscriptions | $544 |
| Electricity (~800W avg) | ~$60 |
| Cloud API tokens | $0 (all flat-rate) |
| **Total** | **~$604/mo** |

The hardware was a one-time investment (~$15K). Equivalent cloud compute would cost $5,000-10,000/month.

## The Core Principle

**Everything possible runs locally.** Cloud subscriptions are for the human operator's interactive sessions. Background agents, monitoring, creative generation — all local, all free, all private. No data leaves the cluster unless you explicitly use a cloud tool.
