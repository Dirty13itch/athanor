# Athanor

## The Name

An athanor is an alchemist's self-feeding furnace — designed to maintain its own heat indefinitely without constant attention. The alchemist loads it, sets the conditions, and the furnace does the slow, continuous work of transformation. The quality of the vessel determines the quality of the output.

Athanor is a unified local system that ties together AI, media, home automation, creative tools, game development, and infrastructure into one coherent, well-crafted whole. It is an instrument, not a mind. Shaun is the alchemist. Athanor is the furnace.

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

**Cloud AI Stays in the Mix** — Claude Code, Kimi Code, and other cloud coding/AI tools remain part of Shaun's workflow. Athanor does not replace them — it complements them. Cloud tools handle what they're best at (coding assistance, large-context reasoning). Local AI handles what cloud can't (uncensored inference, private data, always-on agents, deep local integration). Claude Code may even be used to manage and build Athanor itself. This is not a contradiction — it's pragmatism.

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

**Networking** — UniFi stack already in place. 1GbE currently, 10GbE switch available for future upgrade.

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

## How Shaun Interacts With Athanor

### The Dashboard (Primary)
Athanor's face is a unified command center — a single web UI opened in a browser that shows the state of everything at a glance:

- System health (nodes, GPUs, temps, storage)
- AI status (loaded models, active agents, recent tasks)
- Media (now playing, recent additions, library stats)
- Home (lights, climate, presence, automations)
- Chat panel (talk to the AI without leaving the dashboard)
- Quick actions (trigger agents, run tasks, search)

Additional panels and capabilities will be added as new services come online. The dashboard grows with the system.

**Design language:** Dark, minimal, clean. Inspired by the Twelve Words artifact — Cormorant Garamond, subtle warmth, no clutter. This is a crafted interface, not a generic admin panel. It deserves deep research, careful design, and ongoing refinement. The dashboard is never finished.

### Terminal
Claude Code and other CLI tools for development, system management, and building Athanor itself.

### Mobile (Future)
Phone access when away from home. Not a priority now, but the architecture should not prevent it.

### Voice (Future)
Voice interaction is on the radar. Not a priority now, but worth keeping in mind during architecture decisions.

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

- **Not a "second mind" or artificial intelligence.** It's a tool. A powerful, well-crafted tool.
- **Not an enterprise system.** It doesn't need five nines of uptime, HA failover, or distributed consensus. If a node goes down, Shaun fixes it.
- **Not locked to any technology.** No OS, no orchestration platform, no inference engine, no framework is assumed. Everything is evaluated fresh.
- **Not a finished product.** Athanor is always being built, always being refined. That's the point. The day it's "done" is the day it's dead.
- **Not a closed scope.** The use cases listed in this document are what's known today. Tomorrow there will be more. The system must be ready for that.
- **Not replacing cloud AI tools.** Claude Code, Kimi Code, and other cloud services remain in the workflow. Athanor complements them with capabilities they can't provide.

---

## Current State

### Hardware (to be audited)
- **Node 1** — Silverstone RM52 Upper, running Talos Linux (unhealthy cluster). IPs: 192.168.1.244, 192.168.1.245. Has IPMI via ASRock Q270 Pro BTC+. JetKVM on 192.168.1.165.
- **Node 2** — Silverstone RM52 Middle, running Talos Linux (unhealthy cluster). IP: 192.168.1.10 (both ports).
- **VAULT** — Unraid server, running, accessible. IP: 192.168.1.139. JetKVM on 192.168.1.80.
- **DEV** — Windows 11 desktop (Shaun's daily driver, where he sits and works). IP: 192.168.1.181. Runs Claude Code and Claude Desktop. Not a server node.
- **Loose hardware** — additional components not currently installed in any node. To be inventoried by Shaun.

CPUs, GPUs, RAM, drives, and NICs per node are **unknown until audited**. Do not assume anything from prior projects. The audit is the first real task.

### Network
- UniFi Dream Machine Pro (router/gateway)
- USW Pro 24 PoE (main switch, all servers connected here at 1GbE)
- USW Pro XG 10 PoE (10GbE switch, available but no server connections yet)
- USW Flex (garage)
- Multiple U6 APs (Flex Room, Master Bedroom, Den, Dining Room, Basement, Living Room)
- Lutron lighting controller (192.168.1.158)
- USP PDU Pro (rack power management)
- 3 electrical circuits powering the rack

### Software
- Node 1 and Node 2: Talos Linux (unhealthy Kubernetes cluster from previous project)
- VAULT: Unraid (running, media services operational)
- DEV: Windows 11 with Claude Code, Claude Desktop

**Important:** The Talos Linux installation and Kubernetes cluster are remnants of a previous project (Kaizen). They carry no weight in Athanor decisions. Every technology choice is evaluated fresh. Talos and Kubernetes may or may not be the right answer — that's what the research phase determines.

---

## What Comes Next

1. **Hardware audit** — Claude Code gets access to every reachable node and documents exactly what's installed. Shaun inventories loose hardware. This produces the complete bill of materials.
2. **Research phase** — Evaluate current state of the art for each major component against Athanor's principles. Not just "what's popular" but "what's right for a one-person-maintainable, AI-first, open-scope system."
3. **Architecture decisions** — Made one at a time, in dependency order, each documented with rationale. No decision is made until the research supports it.
4. **Build** — Incremental. Get something running, use it, refine it. Layer by layer. The athanor heats up slowly.

The name tells you how: slow fire, self-feeding, continuous transformation.
