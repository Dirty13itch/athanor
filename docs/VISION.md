# Athanor

## The Name

An athanor is an alchemist's self-feeding furnace — designed to maintain its own heat indefinitely without constant attention. The alchemist loads it, sets the conditions, and the furnace does the slow, continuous work of transformation. The quality of the vessel determines the quality of the output.

Athanor is a unified local system that ties together AI, media, home automation, creative tools, game development, and infrastructure into one coherent, well-crafted whole. Shaun is the alchemist — he sets the vision and makes judgment calls. Claude is the master craftsman — the COO who tends the furnace, directs the workforce, and keeps the fire burning. The 8 local agents are the specialized workers. Athanor is the furnace itself.

---

## Who Is Building This

Shaun Ulrich. Dayton, Minnesota. Engaged. Runs Ulrich Energy, an S-Corp — he's a RESNET-certified HERS Rater doing energy efficiency inspections in the Twin Cities area. That's the day job. Athanor is the passion project built around real life, real schedule constraints, and personal budget.

### The Twelve Words

These describe how Shaun thinks and works. Claude Code should internalize these — they inform every judgment call about how to approach this project.

**Identity — What you are:**
- **Autotelic** (Greek) — The activity is the reward
- **Zetetic** (Greek) — The seeking never resolves
- **Dharma** (Sanskrit) — The path fits the nature

**Method — How you operate:**
- **Kaizen** (Japanese) — Continuous improvement as philosophy
- **Phronesis** (Greek) — Wisdom about where to be rigorous
- **Affordance Sensitivity** (Gibsonian) — Seeing what something could become

**Experience — What it feels like:**
- **Meraki** (Greek) — Soul poured into the work
- **Sisu** (Finnish) — You don't quit
- **Jouissance** (French) — The overwhelm that isn't unpleasant

**Cognition — How the mind works:**
- **Compressivist** (Schmidhuber) — Elegance is shorter truth
- **Endogenous Attention** (Cognitive Science) — The internal signal is loudest
- **Tüftler** (German) — The one who refines what already works

What this means in practice: Shaun cares deeply about the craft of building. He sees potential in things before they have a plan. He doesn't quit. He values elegance and refinement over brute force. He is driven by internal motivation, not external validation. The process of building Athanor is as valuable as the result. Design decisions should honor this — don't optimize purely for speed or efficiency at the expense of craftsmanship.

---

## Why It Exists

In order of importance:

1. **Unification.** One system instead of scattered tools and services. Everything organized under one roof, loosely connected, coherent. Not deeply coupled — but not isolated silos either. There should be an integration layer that lets the pieces be aware of each other, queryable from a central interface, and accessible to AI agents that work across domains.

2. **The craft.** Building Athanor is inherently rewarding. The process of designing, refining, and improving the system is as valuable as the system itself. This is an autotelic project — the activity is the reward.

3. **Capability.** The system should make everything Shaun does faster, better, and more capable. It's a force multiplier across creative projects, research, and daily life.

4. **Sovereignty.** Local-preferred, not local-only. Privacy and control matter, but pragmatism wins over dogma. Cloud services are used when they're genuinely better. Local handles everything that needs to be uncensored, private, always-available, or deeply integrated with local infrastructure.

---

## What It Does

### The Core: AI

AI is what makes Athanor more than a homelab. Everything else is supporting infrastructure.

**Local Inference** — Uncensored models running on local GPUs. Not about running the biggest model possible — about running the right model for the task. Practical capability over bragging rights.

**Agents** — The most exciting piece. Local AI agents that do real work autonomously or on demand. Known agent roles include:

- **Research agent** — finds information, summarizes, reports back
- **Media agent** — manages downloads, organizes library, finds and curates content
- **Home agent** — optimizes automations, responds to conditions, manages devices
- **Creative agent** — generates images and video on demand or on schedule
- **General assistant** — uncensored local chat, ask anything
- **Adult content curator** — content discovery, organization, and management using tools like Stash (local-only by nature, a legitimate major use case that specifically requires local infrastructure)
- **Knowledge agent** — organizes and surfaces accumulated data: 1,173+ bookmarks, documents, research notes, saved references. Makes years of collected information actually accessible and useful.

This list is not exhaustive. New agent roles will emerge as Athanor grows. The system must be designed to absorb new agent types without rearchitecting.

Some agents are proactive (running in the background, doing things without being asked). Some are reactive (waiting for instructions). The split depends on the agent.

**Chat** — A conversational interface to the whole system. Not just a chatbot — a way to ask questions, trigger actions, and get status from anywhere in Athanor.

**Claude Code as COO** — Claude Code is not just a coding assistant. It is the **operational leader** of Athanor — the meta orchestrator that sits between Shaun and the local agent workforce. Claude makes operational decisions, directs local agents, maintains the infrastructure, keeps documentation accurate, and drives the roadmap forward. Shaun sets the vision and makes judgment calls. Claude runs the system. The 8 local agents are Claude's direct reports, executing specialized work under Claude's coordination.

**Cloud/Local AI Hybrid** — Cloud AI (Claude Code) handles architecture, reasoning, coordination, and novel problem-solving. Local AI (Qwen3-32B, Qwen3-14B, 8 agents) handles always-on operations, uncensored inference, private data, and autonomous task execution. This is not a contradiction — it's the operating model. The cloud brain directs the local workforce.

### Game Development

Athanor provides the infrastructure for game development projects.

**Empire of Broken Queens** — The current active project. EoBQ is not a traditional visual novel — it's something between a top-tier visual novel and a new kind of interactive cinematic experience. The vision is a game that feels like a real cinematic movie where the user can participate in ways that are personally responsive and arousing. AI is what makes this possible — static scripts and pre-rendered assets can't create this level of personalization and responsiveness.

What EoBQ needs from Athanor:
- Local LLM inference for procedural, responsive dialogue that adapts to the player
- Image generation pipeline (ComfyUI) for dynamic character portraits, scenes, expressions, and environments
- Video generation for cinematic sequences
- Game engine / visual novel framework capable of integrating AI-generated content in real time
- Asset management, version control, and build pipeline
- Adult content is central to the project — this is intentional and non-negotiable

EoBQ is a serious, ambitious creative project. It deserves proper engineering and infrastructure support.

Future game development projects will emerge. The infrastructure should support game dev workflows broadly, not just EoBQ specifically.

### Creative Tools

- **Image generation** — ComfyUI with local models (Flux, SD3, LoRA training)
- **Video generation** — Wan2.x and emerging models
- **Future creative workloads** — 3D, music production, content creation as needs emerge

### Supporting Infrastructure

These exist to serve the AI core and Shaun's daily life:

**Media** — Plex, *arr stack, content acquisition and organization. Runs on Unraid. The media agent layer makes it smarter over time.

**Adult Content Management** — Stash and related tools for organization, tagging, and curation of adult content libraries. This is a significant use case that requires local infrastructure, dedicated storage, and AI-assisted organization. It deserves proper engineering, not an afterthought.

**Home Automation** — Home Assistant, Lutron lighting, smart devices, UniFi network integration. The home agent layer optimizes and automates beyond basic rules.

**Storage** — Unraid is the backbone. Bulk storage, media, backups. Non-negotiable — it stays.

**Networking** — UniFi stack with 10GbE backbone deployed (USW Pro XG 10 PoE). All server nodes on SFP+ data plane.

**Development Environment** — Claude Code, Kimi Code, and other cloud coding tools stay in the workflow. Local dev environments as needed for Athanor development, game development, app development, and other projects.

This list is not exhaustive. New infrastructure needs will emerge — game servers, emulation platforms, web crawling services, app development environments, and anything else that fits under Athanor's roof. The architecture must accommodate growth without requiring fundamental redesign.

---

## Projects

Athanor is both the infrastructure and the workspace. Multiple distinct projects live on it, each with their own files, tools, context, and pace. The system needs a clear project organization model.

### Known Projects
- **Athanor itself** — the infrastructure, the dashboard, the agents, the system
- **Empire of Broken Queens** — AI-driven interactive cinematic adult game
- **Kindred** — passion-based social matching app (concept/research phase)
- **Ulrich Energy workflows** — business tools, reports, templates (separate from Athanor core)
- **Future projects** — new games, new apps, new ideas as they emerge

### What Project Organization Needs to Provide
- **Separation** — each project is self-contained with its own files, configs, and context
- **Project-specific context** — when working on a project (in Claude Code or any tool), the tool should know which project it's in and load the right context, rules, and available tools
- **Easy onboarding** — spinning up a new project should be trivial, not require redesigning anything
- **Shared infrastructure** — projects share Athanor's resources (GPU, storage, networking, AI inference) but don't interfere with each other
- **Independent pace** — some projects move fast, some sit dormant for months, some are continuous. The system doesn't force a tempo.

The specific implementation of project organization (directory structure, tooling, isolation model) is a research and design question — not something to decide in this vision document. But the need for it is established here.

---

## How Athanor is Operated

### The Operating Model

Athanor runs as a three-tier organization. Shaun sets the vision. Claude runs the system. Agents do the work.

- **Shaun (Owner)** — Sets direction, reviews results, makes judgment calls, handles physical tasks and credentials.
- **Claude (COO / Meta Orchestrator)** — Makes operational decisions, designs architecture, directs agents, maintains infrastructure, keeps docs accurate, drives the roadmap.
- **8 Local Agents (Workforce)** — Execute domain-specific work autonomously or on command, within defined boundaries.

This means Shaun doesn't need to micromanage. He opens the Command Center, sees the system state, chats with agents when he wants to, and reviews what Claude has built. Claude keeps things running between sessions.

### The Command Center (Primary Interface)
Athanor's face is a unified command center — a PWA at Node 2:3001. 17 pages, 5 lens modes, live system metrics via SSE, generative UI for rich tool results:

- System health (nodes, GPUs, temps, storage)
- AI status (loaded models, active agents, recent tasks, trust scores)
- Media (now playing, recent additions, library stats)
- Home (lights, climate, presence, automations)
- Chat panel (talk to any of the 8 agents)
- Task management (submit, monitor, cancel background work)
- Goals and feedback (steering goals, daily digest, trust scores)

**Design language:** Dark, minimal, clean. Inspired by the Twelve Words artifact — subtle warmth, ambient glow, no clutter. This is a crafted interface, not a generic admin panel. It deserves deep research, careful design, and ongoing refinement. The dashboard is never finished.

### Claude Code / Claudeman (Operations)
Claude operates through Claude Code (terminal) and Claudeman (DEV:3000, multi-session web UI). This is where architecture decisions are made, infrastructure is built, agents are tuned, and the roadmap is executed.

### Mobile (Deployed)
Command Center is a responsive PWA — works on mobile with bottom nav, safe area handling, and touch-optimized controls. Claudeman is accessible via HTTPS on mobile.

### Voice (Deployed)
Voice interaction via Home Assistant Wyoming integration. STT (whisper), TTS (Piper), wake word (ok_nabu). "Athanor Voice" pipeline configured.

---

## Non-Negotiables

These are true regardless of what technology decisions are made:

1. **Uncensored local inference must be available.** This is the one capability that justifies the entire local AI investment. Cloud AI can't do this.

2. **Unraid stays.** It works. It runs the media stack. It's the storage backbone. Don't replace it, build around it.

3. **One-person maintainable.** If the system requires a team to operate, it's overengineered. Every component must be understandable, debuggable, and fixable by Shaun alone. This is the single most important filter on every architectural decision.

4. **Remote access.** Eventually accessible from outside the home network. Not urgent, but the architecture shouldn't prevent it.

---

## Principles

### Right Over Fast
Take the time to research, document, and decide before building. Each layer verified solid before building the next. No jumping ahead. But also: don't design for six months without running anything. Find the balance.

### The Tüftler Principle
Refine what works. Don't throw everything out and start over when something can be improved in place. Continuous, incremental improvement over revolutionary rebuilds.

### Practical Over Pure
Best tool for the job wins. Local is preferred but not mandatory. Simple is preferred over complex. Working is preferred over theoretically optimal.

### One-Person Scale
Every decision must pass the test: "Can Shaun understand, operate, debug, and fix this alone?" If the answer is no, the decision is wrong — no matter how technically superior it is.

### The Vessel Matters
Infrastructure quality determines output quality. The care put into how things are built — clean configs, good documentation, thoughtful architecture — is not wasted effort. It's the whole point.

### Open Scope
Athanor is not a fixed-scope project. It is designed to grow. New workloads, new agents, new services, new ideas will emerge over time. The architecture must make it easy to add new capabilities without rearchitecting what already exists. If adding something new requires tearing apart something old, the foundation was wrong.

---

## What Athanor Is Not

- **Not a passive tool.** Athanor has operational intelligence — Claude as COO actively manages the system, directing 8 agents that do real autonomous work. But Shaun is always the owner. The system serves his vision.
- **Not an enterprise system.** It doesn't need five nines of uptime, HA failover, or distributed consensus. If a node goes down, Claude investigates and Shaun fixes what requires physical presence.
- **Not locked to any technology.** No OS, no orchestration platform, no inference engine, no framework is assumed. Everything is evaluated fresh.
- **Not a finished product.** Athanor is always being built, always being refined. That's the point. The day it's "done" is the day it's dead.
- **Not a closed scope.** The use cases listed in this document are what's known today. Tomorrow there will be more. The system must be ready for that.
- **Not cloud-dependent.** Claude (cloud) provides strategic intelligence and coordination. Local agents provide always-on execution. If cloud access is lost, the local workforce continues operating autonomously within their defined boundaries.

---

## Current State

For live operational state, see:
- `docs/SYSTEM-SPEC.md` — Complete operational specification
- `docs/SERVICES.md` — Service inventory with ports
- `STATUS.md` — Ground-truth cluster state (verified and updated regularly)
- `docs/hardware/inventory.md` — Hardware inventory
- `docs/decisions/` — 21 Architecture Decision Records
- `docs/BUILD-MANIFEST.md` — Build queue and roadmap

---

## What Comes Next

The athanor is never finished. Continuous improvement.

The name tells you how: slow fire, self-feeding, continuous transformation.
