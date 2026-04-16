# Persistent Development Environment: Integration, Interaction Layers, and Self-Modification

**Date:** 2026-02-26
**Status:** Research complete
**Purpose:** Define how Shaun interacts with Athanor permanently -- the layered interaction architecture that serves both mobile and desktop equally, integrates development capabilities into the Command Center, and explores whether the system can safely develop itself.
**Depends on:** `2026-02-25-web-development-environments.md` (tool landscape), `command-center.md` (design), ADR-019 (Command Center), ADR-017 (Meta-Orchestrator)

---

## Context

Athanor's current development workflow runs through Claude Code CLI in WSL2 tmux sessions on DEV. Shaun is an orchestrator, not a coder -- AI writes code, Shaun reviews and steers. The Command Center is a Next.js PWA at DEV via athanor.local (runtime fallback dev.athanor.local:3001) with 17 pages, 5 lens modes, SSE streaming, a command palette, and bottom nav on mobile. Claudeman (multi-session Claude Code web UI) is at DEV:3000. Eight AI agents on Node 1:9000 do autonomous work.

The existing research (`2026-02-25-web-development-environments.md`) comprehensively covers the tool landscape: code-server, Cursor/Windsurf, Claude Code web/remote-control, Claudeman, claude-code-web, OpenHands, xterm.js, ttyd, Jupyter, and the orchestrator's workbench concept. That research is not repeated here. This document addresses the questions that research left open:

1. How should development capabilities integrate with the monitoring dashboard?
2. What makes development productive on mobile vs desktop?
3. How do interaction layers map to mobile vs desktop?
4. Can the system safely develop itself?
5. What is the recommended layered interaction architecture?

---

## 1. Integration Patterns: Development Environment + Dashboard

### 1.1 The Fundamental Question: Embedded vs Linked

Three architectural patterns exist for combining a development environment with a monitoring dashboard:

**A. Embedded (iframe)** -- The dev environment runs inside the dashboard as an iframe or embedded component.

**B. Micro-frontend** -- Multiple apps share a shell, rendered as one. Each maintains its own build pipeline.

**C. Linked (separate apps, deep links)** -- Dashboard and dev tools are separate apps. Dashboard links to dev tools contextually.

### 1.2 Iframe Embedding: Analysis

Iframes are the simplest embedding mechanism but carry significant issues:

**Security risks:**
- Cross-Site Scripting (XSS) if the embedded content is compromised (Qrvey, 2026: https://qrvey.com/blog/iframe-security/)
- Clickjacking via transparent overlays (WorkOS: https://workos.com/blog/security-risks-of-iframes)
- Session hijacking through embedded malicious content targeting auth tokens
- Cross-origin restrictions limit communication between iframe and parent

**Mobile behavior:**
- Iframes are not naturally responsive -- require wrapper CSS with aspect-ratio hacks
- Touch scrolling within iframes is unreliable on iOS (momentum scrolling conflicts)
- Performance penalty: a Stack Overflow report documented forms loading in 2 seconds directly vs 45 seconds through an iframe in an iOS web view
- Keyboard behavior is inconsistent -- virtual keyboard focus management breaks frequently
- No URL routing -- the iframe's URL is invisible to the browser, breaking navigation, bookmarks, and back button

**Performance:**
- Each iframe is a separate browsing context with its own DOM, JS heap, and rendering pipeline
- A terminal emulator (xterm.js) inside an iframe inside a Next.js app adds two layers of overhead to every keystroke
- Embeddable.com identified 8 reasons not to embed dashboards with iframes, including performance degradation, broken navigation, and inconsistent user experience (https://embeddable.com/blog/iframes-for-embedding)

**Verdict: Do not use iframes for terminal embedding.** The mobile experience will be poor, the performance overhead is unnecessary, and the security model adds complexity without benefit. On a trusted LAN this is less critical, but the UX problems remain.

Source: https://caisy.io/blog/nextjs-iframe-implementation, https://www.feroot.com/blog/how-to-secure-iframe-compliance-2025/

### 1.3 Micro-Frontend Architecture: Analysis

Next.js supports micro-frontends through two mechanisms:

**Multi-Zones** (official): Multiple Next.js apps deployed under a single domain using rewrites. Each zone handles a subset of routes. A gateway app rewrites `/terminal/*` to Terminal App, `/dashboard/*` to Dashboard App. Each zone deploys independently.

Source: https://nextjs.org/docs/app/guides/multi-zones

**Module Federation** (Webpack 5): Dynamically load code from different builds at runtime. A shell app imports components from remote builds. Next.js 14+ with Module Federation 2.0 enables shared UI code across independent deployments.

Source: https://medium.com/@livenapps/building-micro-frontends-with-next-js-and-module-federation-0e322230d751

**Evaluation for Athanor:**

| Criterion | Multi-Zones | Module Federation |
|-----------|-------------|-------------------|
| Complexity | Low -- just rewrites | High -- Webpack config, shared deps |
| Independent deploy | Yes | Yes |
| Shared state | Via cookies/headers | Via shared modules |
| Mobile UX | Seamless (same domain) | Seamless (same page) |
| One-person maintainable | Yes | Borderline -- debugging is hard |
| Necessary for Athanor | No | No |

**Verdict: Micro-frontends are over-engineered for Athanor.** The dashboard is a single Next.js app maintained by one person (Claude, technically, but directed by one person). There is no team boundary problem to solve. Adding a `/terminal` page directly to the existing dashboard is simpler and achieves the same result as a micro-frontend zone -- with zero additional infrastructure.

### 1.4 Linked Apps with Deep Linking: Analysis

This is the pattern used by platforms like Vercel, Railway, and Coolify -- monitoring dashboards that link to development tools contextually.

**Vercel's approach:** The dashboard shows deployments, monitoring, and analytics. When you need to see code, it links to GitHub. When you need logs, it shows them inline. When you need a terminal, it provides a CLI. The dashboard is the hub; development tools are spokes.

Source: https://vercel.com/docs/dashboard-features, https://medium.com/design-bootcamp/vercels-new-dashboard-ux-what-it-teaches-us-about-developer-centric-design-93117215fe31

**Coolify's approach:** Open-source, self-hosted PaaS with a web dashboard for deploying apps, databases, and services. Monitoring and deployment in one UI. Git integration for auto-deploy. Built-in Grafana for monitoring.

Source: https://coolify.io/docs/get-started/introduction

**How this maps to Athanor:**

```
Command Center (DEV via athanor.local (runtime fallback dev.athanor.local:3001)) -- THE HUB
  |
  |-- Layers 0-4: Native pages in the dashboard
  |     |-- Home (ambient), GPUs, Services, Agents (monitoring)
  |     |-- Chat, Tasks, Goals, Feedback (directing)
  |     |-- /terminal page (xterm.js, native in dashboard)
  |
  |-- Layer 5: Linked external apps
        |-- Claudeman (DEV:3000) -- multi-session Claude Code
        |-- OpenHands (Node 1:3000) -- sandboxed AI coding
        |-- Open WebUI (Node 2:3000) -- direct model chat
```

Deep links enable contextual navigation:
- Click agent task in Command Center --> link to Claudeman session working on it
- Click service error in Command Center --> link to relevant log view
- Push notification "Task complete" --> deep link to diff view in Command Center

**Verdict: Linked apps with deep linking is the correct pattern.** It respects each tool's strengths, avoids the complexity of embedding, and keeps the Command Center focused on orchestration rather than becoming a monolithic super-app.

### 1.5 Real-World Integration Precedents

| Platform | Pattern | What Works | What Breaks |
|----------|---------|------------|-------------|
| **Vercel** | Hub dashboard + linked GitHub/CLI | Clean separation, contextual links | Cannot edit code in dashboard |
| **Railway** | Single dashboard, deploy + monitor | Fast iteration, everything visible | Limited for complex workflows |
| **Coolify** | Self-hosted PaaS, web dashboard | One URL for ops, git auto-deploy | Not designed for AI dev workflows |
| **GitHub** | Code + Issues + Actions + Copilot | Deep integration across concerns | Sprawling, bloated on mobile |
| **Grafana** | Monitoring hub, links to data sources | Extensible, plugin ecosystem | Steep learning curve |

The pattern that works best for a single operator is **Railway's approach**: everything critical in one dashboard, with depth available on demand. Not GitHub's "everything in one app" approach (too complex) and not the distributed model where every tool is separate (too many URLs to manage).

### 1.6 Risk Assessment: Dev Environment in Dashboard

| Risk | Severity | Mitigation |
|------|----------|------------|
| Terminal page crash takes down dashboard | Medium | xterm.js is a client-side component; crash is isolated to the page, not the app |
| node-pty backend crash affects Node 2 | Low | Run terminal backend on DEV, not Node 2 -- crash does not affect dashboard server |
| Security exposure via web terminal | Medium | LAN-only access, token auth, no internet-facing exposure |
| Performance drag from terminal on mobile | Low | Terminal page loaded on demand (Next.js code splitting), not part of other pages |
| Complexity creep | Medium | Terminal is ONE page. Chat is the primary interface. Terminal is the escape hatch. |

**Overall assessment:** Adding a terminal page to the dashboard is low risk. The key is restraint -- it is a fallback, not the primary interface. The primary interface is chat + task dispatch + feedback.

---

## 2. Mobile-First Development Interaction

### 2.1 What Actions Make Sense on Mobile vs Desktop

This is the critical insight: mobile and desktop are not degraded versions of each other. They are different tools for different actions.

**Mobile-appropriate actions (Layers 0-3):**

| Action | Why Mobile Works | Implementation |
|--------|-----------------|----------------|
| Glance at system status | 2-second check, phone already in hand | Home page, System Pulse strip |
| Read agent activity | Scrolling a feed is natural on phone | Activity/Stream page |
| Approve/reject agent proposals | Binary decision, one tap | Push notification action buttons, inline buttons |
| Give thumbs up/down feedback | Binary, one tap | Feedback icons on every agent output |
| Set priorities ("focus on media tonight") | Short text input or voice | Chat page, command palette |
| Triage notifications | Swipe to dismiss/act | Notification tray |
| Monitor task progress | Check status, no input needed | Tasks page |
| Voice commands | Phone has microphone, hands-free | Voice input in chat |

**Desktop-appropriate actions (Layers 4-5):**

| Action | Why Desktop Required | Implementation |
|--------|---------------------|----------------|
| Review code diffs | Needs wide screen, syntax highlighting | Diff viewer page (or Claudeman) |
| Architecture decisions | Complex context, multiple documents | Claude Code session via Claudeman |
| Complex debugging | Terminal interaction, log analysis | Claudeman or terminal page |
| Agent configuration | Form-heavy, many fields | Settings pages |
| Workflow design | Visual, drag-and-drop possible | Desktop-only creative tools |
| Multi-file review | Side-by-side comparison | Desktop layout with panels |

**Both equally (Layer 1-3):**

| Action | Mobile | Desktop |
|--------|--------|---------|
| Chat with agents | Quick messages, voice | Longer context, paste code |
| Submit tasks | Simple description | Detailed specification |
| View GPU status | Card layout | Chart layout |
| Manage goals | Read, adjust priority | Create, edit in detail |

### 2.2 Mobile Code Review Patterns

GitHub Mobile launched enhanced code review in April 2024, allowing developers to review pull requests, comment on specific lines, approve or request changes, and have Copilot analyze PRs -- all from a phone.

Source: https://github.blog/changelog/2024-04-09-introducing-enhanced-code-review-on-github-mobile/

Key patterns from GitHub Mobile and similar tools:
- **Unified diff view** (not side-by-side) -- side-by-side does not work on narrow screens
- **Collapsible file sections** -- tap to expand a file's changes
- **Inline comments** -- tap a line to add a comment
- **Binary approval** -- "Approve" or "Request changes" as prominent buttons
- **Summary first** -- show what changed (files, lines added/removed) before the diff
- **Swipe between files** -- horizontal navigation through changed files

For Athanor, the diff reviewer does not need to be as complex as GitHub's. The primary flow is:
1. Agent completes task
2. Push notification: "Coding agent finished: Update GPU dashboard layout (4 files changed)"
3. Tap notification --> opens diff summary in Command Center
4. Scroll through changes (unified diff, syntax highlighted)
5. Tap "Approve" or "Reject with feedback"

This is feasible on mobile because the review is AI-generated work, not human-authored code that needs line-by-line scrutiny.

### 2.3 Mobile Task Management Patterns

The most effective mobile task management apps share these patterns:

- **Card-based views** over table/list views (Linear, Todoist)
- **Swipe gestures** for quick actions: swipe right to complete, left to snooze/archive (SAP Business ByDesign uses "swipe to accept or reject")
- **Quick-add** from anywhere: floating action button or pull-down gesture
- **Status pills** with color coding: green=done, amber=in-progress, red=blocked
- **Tap to expand** for details, not separate page navigation
- **Sorting by priority/recency** as default, not alphabetical

Source: https://www.clappia.com/blog/task-management-system, https://zapier.com/blog/best-todo-list-apps/

For Athanor's task management on mobile:
- Card per task: agent name, task description, status pill, timestamp
- Tap to expand: show step log, agent reasoning, output preview
- Swipe right to approve/complete, swipe left to reject with feedback
- Quick-add: "Ask [agent] to [task]" via chat or command palette

### 2.4 Voice as Input

Voice is the most underutilized mobile input for orchestration. Athanor already has STT/TTS via Home Assistant Wyoming integration (whisper + Piper + ok_nabu wake word).

**Current state of voice AI (2026):**
- Voice agents trained to recognize emotions and adjust delivery (ElevenLabs: https://elevenlabs.io/blog/voice-agents-and-conversational-ai-new-developer-trends-2025)
- React Native speech recognition with wake word, STT, and voice commands (Picovoice: https://picovoice.ai/blog/react-native-speech-recognition/)
- Global voice market reached $2.73B in 2024, projected $14.2B by 2032

**Voice use cases for Athanor:**
- "Creative agent, generate 5 character portraits for EoBQ chapter 3" (task dispatch)
- "What happened overnight?" (status query, returns daily digest)
- "Approve the media agent's request" (binary approval)
- "Focus on creative work tonight" (lens/priority change)
- "How are the GPUs doing?" (status query, returns generative UI card)

**Implementation path:**
The dashboard's chat page should accept voice input via the Web Speech API (browser-native, no server-side dependency). This is separate from the HA voice pipeline -- the HA pipeline is for ambient/hands-free use ("Hey Nabu, ask Athanor..."), while browser voice input is for intentional mobile use.

```
Mobile flow:
  Tap microphone icon in chat --> Web Speech API --> text --> POST to agent --> streaming response
```

This is low effort (Web Speech API is built into Chrome/Safari) and high value for mobile orchestration.

### 2.5 Push Notification Quick Actions

PWA push notifications on Android support action buttons. On iOS, actions are more limited but improving.

Source: https://www.magicbell.com/blog/using-push-notifications-in-pwas, https://almanac.httparchive.org/en/2025/pwa

**Notification patterns for Athanor:**

| Event | Notification | Actions |
|-------|-------------|---------|
| Agent task complete | "Media agent added 3 shows to Sonarr" | [View] [Undo] |
| Agent needs approval | "Creative agent wants to regenerate scene 4" | [Approve] [Reject] |
| System alert | "GPU 2 temperature: 89C" | [View] [Silence] |
| Daily digest | "Overnight: 12 tasks completed, 1 issue" | [View Digest] |
| Build complete | "Coding agent finished: dashboard update (4 files)" | [Review Diff] [Approve] |

**iOS limitation:** No rich media or silent push for PWAs on iOS as of 2025. Action buttons work on Android Chrome. On iOS, the notification opens the app to the relevant page -- no inline action buttons.

Source: https://www.magicbell.com/blog/best-practices-for-ios-pwa-push-notifications

**Mitigation for iOS:** When notification is tapped, deep-link to the specific approval/review page with prominent action buttons at the top. The flow becomes: tap notification --> see context + approve/reject buttons --> one more tap to act. Two taps total instead of one, but functional.

### 2.6 Gesture-Based Interaction

| Gesture | Action | Where |
|---------|--------|-------|
| Pull-to-refresh | Reload current view data | All pages |
| Swipe right on task card | Approve / complete | Tasks page, Stream |
| Swipe left on task card | Reject / dismiss | Tasks page, Stream |
| Long-press agent portrait | Open quick-action menu | CrewBar (agent portrait bar) |
| Swipe between tabs | Navigate bottom nav tabs | Bottom navigation |
| Pinch-to-zoom on diff | Zoom into code changes | Diff reviewer |
| Double-tap metric | Expand to full chart | GPU page, Monitoring page |

**Caution:** Swipe gestures can conflict with system gestures (iOS back swipe, Android nav gesture). Implement with horizontal thresholds (>30% of card width to trigger) and visual feedback (card slides, reveals action color underneath).

---

## 3. Interaction Layers / Modes

### 3.1 The Six Layers

The interaction model is structured as six layers of increasing depth and engagement. Each layer requires more attention, more screen space, and more input complexity.

```
Layer 0: AMBIENT     "Everything okay?"        Glance, 2 seconds
Layer 1: MONITOR     "What happened?"           Scan, 30 seconds
Layer 2: FEEDBACK    "That was good/bad"        React, 5 seconds
Layer 3: DIRECT      "Do this next"             Instruct, 1-2 minutes
Layer 4: CREATE      "Build this workflow"       Design, 10-30 minutes
Layer 5: DEVELOP     "Change the system"         Engineer, 1+ hours
```

### 3.2 Layer Definitions

**Layer 0: Ambient**
- What: System status at a glance. Is everything healthy?
- Interface: Home screen PWA icon badge (if supported), System Pulse strip, ambient background color (warm=busy, cool=idle, red-tint=error)
- Mobile: Check phone, see PWA icon, see green/amber/red status. Done.
- Desktop: Dashboard home page with ambient CSS, agent constellation
- Input: None required. This is passive.
- Precedent: Apple Watch complications, smart home widget, car dashboard gauges

**Layer 1: Monitor**
- What: What happened since last check? What is in progress? Any issues?
- Interface: Activity Stream, GPU status cards, Agent status grid, Service health
- Mobile: Scroll the Stream page. Cards show summaries. Tap to expand.
- Desktop: Same content, wider layout, charts instead of sparklines
- Input: Navigation only (scroll, tap to expand)
- Precedent: Twitter/X feed, GitHub notification inbox, Grafana dashboards

**Layer 2: Feedback**
- What: React to agent outputs. Thumbs up/down. Priority adjustment. "More/less of this."
- Interface: Inline feedback icons on every agent output. Priority sliders on goals. Quick-reaction buttons.
- Mobile: Thumbs up/down icons on each card. Swipe gestures. Star ratings.
- Desktop: Same, plus text feedback fields
- Input: One-tap binary feedback. Occasionally short text.
- Precedent: Netflix thumbs up/down, Spotify like/dislike, Instagram double-tap to heart

**Layer 3: Direct**
- What: Give new instructions. Set goals. Queue tasks. Chat with agents.
- Interface: Chat page, Task dispatch form, Goals page, Command palette
- Mobile: Type or speak instructions in chat. Use command palette for common actions.
- Desktop: Same, plus longer-form goal editing, multi-agent task coordination
- Input: Natural language (text or voice). Selection from menus. Form fields.
- Precedent: Slack commands, Siri/Alexa commands, Linear issue creation

**Layer 4: Create**
- What: Design workflows. Configure agent behavior. Write prompts. Set up automations.
- Interface: Agent configuration pages, Workflow editor, Prompt templates, Automation rules
- Mobile: Partially usable for simple config (toggle switches, dropdown selections). Complex creation requires desktop.
- Desktop: Form-heavy pages, possibly visual editors for workflows, prompt template management
- Input: Structured forms, possibly drag-and-drop, code/prompt editing
- Precedent: IFTTT/Shortcuts (mobile-friendly creation), Home Assistant automations (desktop-first)

**Layer 5: Develop**
- What: Full development environment. Code review. Architecture decisions. System modifications.
- Interface: Claudeman (DEV:3000), Terminal page in dashboard, Diff reviewer, Claude Code CLI
- Mobile: Review-only (read diffs, approve/reject). No code writing on phone.
- Desktop: Full Claudeman with multi-session management, terminal access, diff viewer
- Input: Terminal commands, code review annotations, architecture discussion
- Precedent: GitHub mobile (review only) vs GitHub desktop (full development)

### 3.3 Layer-to-Platform Suitability Matrix

| Layer | Mobile Suitability | Desktop Suitability | Primary Interface |
|-------|-------------------|--------------------|--------------------|
| 0: Ambient | Excellent (phone glance) | Good (background tab) | Home page + PWA badge |
| 1: Monitor | Excellent (scroll feed) | Excellent (charts) | Stream page |
| 2: Feedback | Excellent (tap/swipe) | Good (click) | Inline on all agent outputs |
| 3: Direct | Good (voice/text) | Excellent (keyboard) | Chat page + Command palette |
| 4: Create | Partial (simple configs) | Excellent (forms) | Settings/Config pages |
| 5: Develop | Limited (review only) | Required (full dev) | Claudeman + Terminal page |

### 3.4 Navigation Between Layers

Layers are not separate modes that require explicit switching. They are depths of engagement that the user moves through naturally.

**Entry points:**
- Notification tap --> Layer 2 (feedback on the specific item)
- Open app casually --> Layer 0/1 (home page, scan activity)
- Command palette (Cmd+K) --> Layer 3 (direct instruction)
- Chat page --> Layer 3 (conversational directing)
- Link from agent task --> Layer 5 (review code change)
- Settings pages --> Layer 4 (configure agents)

**Progressive disclosure drives transitions:**
- Layer 0 (home) --> tap agent portrait --> Layer 1 (agent detail) --> tap task --> Layer 2 (feedback buttons) --> tap "View changes" --> Layer 5 (diff review)
- Each tap goes one layer deeper. Back button goes one layer shallower.

**The Lens system enables lateral movement within layers:**
- System lens at Layer 1 shows infrastructure monitoring
- Media lens at Layer 1 shows media activity
- Creative lens at Layer 1 shows generation history
- Lens changes the DOMAIN, not the DEPTH

Source: Progressive disclosure patterns from https://agentic-design.ai/patterns/ui-ux-patterns/progressive-disclosure-patterns, https://primer.style/design/ui-patterns/progressive-disclosure/, https://uxplanet.org/mission-control-software-ux-design-patterns-benchmarking-e8a2d802c1f3

### 3.5 Mapping to Existing Dashboard Pages

| Page | Layer(s) | Mobile | Notes |
|------|----------|--------|-------|
| Home (/) | 0, 1 | Primary | Furnace surface, agent constellation, Smart Stack |
| GPUs (/gpu) | 1 | Good | Card layout mobile, chart layout desktop |
| Monitoring (/monitoring) | 1 | Good | Per-node cards |
| Services (/services) | 1 | Good | Health grid |
| Agents (/agents) | 1 | Good | Agent roster |
| Activity (/activity) | 1, 2 | Excellent | Stream with inline feedback |
| Chat (/chat) | 3 | Excellent | Voice input on mobile |
| Tasks (/tasks) | 1, 2, 3 | Good | Task cards with swipe actions |
| Goals (/goals) | 3 | Good | Priority adjustment, simple goal setting |
| Workspace (/workspace) | 1 | Desktop | GWT internals, mostly diagnostic |
| Conversations (/conversations) | 1 | Good | Historical agent conversations |
| Gallery (/gallery) | 1, 2 | Excellent | Image feed with feedback |
| Media (/media) | 1, 3 | Good | Library + request actions |
| Home Automation (/home) | 1, 3 | Excellent | Device control, like HA mobile |
| Notifications (/notifications) | 2 | Excellent | Triage + act |
| Preferences (/preferences) | 4 | Partial | Simple prefs mobile, complex desktop |
| Terminal (/terminal) | 5 | Limited | Desktop primary, mobile escape hatch |
| **NEW: Diff Review** (/review) | 5 | Partial | Unified diff, approve/reject mobile-friendly |

### 3.6 Research Precedents: Multi-Layer Interaction Systems

**SpaceX Mission Control:** Uses subsystem isolation (each subsystem on its own page) with a persistent status strip across all views. Operators navigate between overview (Layer 1) and subsystem detail (Layer 4-5) using side navigation. The key insight: "minimalism as safety" -- if a detail is not essential, it does not belong.

Source: `2026-02-25-command-center-ui-design.md`

**Waymo Fleet Response:** Exception-based intervention (Layer 0-1 passive, Layer 3 only when the vehicle asks for help). Rich context at intervention time -- the operator sees camera feeds, 3D model, rewind capability. The system retains authority after human input.

Source: `2026-02-25-human-in-the-loop-patterns.md`

**Trading platforms:** Layered defense: pre-trade controls (Layer 0 automated), real-time monitoring (Layer 1), kill switches (Layer 3), circuit breakers (Layer 0 automated). Alerts within 5 seconds. The rubber-stamp problem: humans fail when the system operates faster than they can process.

Source: `2026-02-25-human-in-the-loop-patterns.md`

**Smart home dashboards (Home Assistant):** Prominent controls at the forefront (Layer 3 accessible from Layer 1). Tap to toggle, long-press for details (Layer 1 --> Layer 4 transition). State-dependent styling (Layer 0 ambient signals).

Source: `2026-02-25-command-center-ui-design.md`

**Calm technology (Weiser & Brown, 1995):** "Informs but doesn't demand focus." Information moves between periphery and center of attention based on relevance. This is exactly the Layer 0 --> Layer 1 transition.

Source: `2026-02-25-novel-interface-patterns.md`

---

## 4. The "System Developing Itself" Pattern

### 4.1 What This Means for Athanor

Athanor's development environment (Claude Code, Claudeman, agents) is part of Athanor. Claude Code modifies dashboard code, Ansible playbooks, agent configurations, and documentation -- all of which are part of the running system. The question is whether this creates dangerous feedback loops and what safeguards are needed.

### 4.2 Historical Precedents

**Smalltalk (1972-present):**
Smalltalk is the canonical self-modifying development environment. The entire IDE -- editor, debugger, inspector, class browser -- is written in Smalltalk and runs inside the same image as the code being developed. You modify the development tools using the development tools.

Benefits: Immediate feedback. No compile cycle. Debugging the debugger is possible. "All development information is saved which facilitates debugging."

Risks: "Modifying an instance creates a custom version tightly coupled to that specific configuration" (Martin Fowler, "Internal Reprogrammability": https://martinfowler.com/bliki/InternalReprogrammability.html). Instance fragmentation -- your Smalltalk image diverges from every other image. Upgrades become migration projects.

**Emacs (1976-present):**
Emacs is configured and extended in Emacs Lisp, evaluated in the running editor. Your configuration IS a program. `M-x eval-buffer` modifies the running environment immediately.

Benefits: Infinite customization. The tool becomes exactly what you need. Community packages extend capabilities enormously.

Risks: Configuration complexity grows unbounded. "Emacs bankruptcy" -- the config becomes so complex that the user starts over. No separation between safe and unsafe modifications. A bad `.el` file can render Emacs unusable.

**Jupyter Notebooks (2014-present):**
A computing environment that documents itself. Code cells, output cells, markdown cells -- the notebook is both the program and its documentation.

Benefits: Executable documentation. Reproducible workflows. Self-documenting exploration.

Risks: Hidden state (cells executed out of order). Non-reproducibility ("it works on my machine"). Version control is terrible for notebooks. The tool encourages sloppy practices by making them easy.

Source: https://en.wikipedia.org/wiki/Smalltalk, https://martinfowler.com/bliki/InternalReprogrammability.html, https://www.researchgate.net/publication/200040544_Constructing_a_Metacircular_Virtual_Machine_in_an_Exploratory_Programming_Environment

### 4.3 Risk Analysis for Athanor

| Risk | Severity | Likelihood | Description |
|------|----------|------------|-------------|
| Breaking change to dashboard | Medium | Medium | Claude Code edits dashboard code, deploys, dashboard crashes |
| Breaking change to agent server | High | Medium | Claude Code edits agent code, deploys, agents stop working |
| Breaking change to Ansible | High | Low | Ansible playbook change misconfigures a node |
| Feedback loop | Low | Low | Agent modifies its own config, creating unstable oscillation |
| State corruption | Medium | Low | Modification to Qdrant schema or Redis data format breaks agents |
| Security escalation | Low | Very Low | On a trusted LAN with no internet exposure, attack surface is minimal |

### 4.4 GitOps as the Safety Net

Git is the single most important safeguard for a self-modifying system. Every change goes through git, which provides:

**Audit trail:** Every modification is a commit with author, timestamp, and diff. `git log` is the complete history of what changed and when.

**Rollback:** `git revert` undoes any change. `git checkout <commit> -- <file>` restores any file to any previous state. This is the "undo button" for the entire system.

**Review gate:** Changes can require review before deployment. For Athanor, this means Claude Code commits changes, and either (a) Shaun reviews the diff before deployment, or (b) the system auto-deploys but can be rolled back instantly.

**Branch isolation:** Experimental changes can be made on branches without affecting the running system. Merge only after testing.

Source: https://codefresh.io/learn/gitops/, https://developer.hashicorp.com/well-architected-framework/define-and-automate-processes/process-automation/gitops, https://opengitops.dev/blog/sec-gitops/

**GitOps risks specific to self-modifying systems:**
- "If the GitOps process is compromised, it can open backdoors in infrastructure" (Microtica: https://www.microtica.com/blog/security-misconfigurations-with-gitops)
- Unencrypted git files that disclose API credentials
- Supply chain issues with third-party dependencies
- For Athanor, the mitigation is: LAN-only deployment, no public git exposure, credentials in environment variables not git

### 4.5 Staged Rollout Within the Same System

For a one-person homelab, full staging environments are overkill. But lightweight staging is valuable:

**Level 1: Branch + manual deploy (current):**
Claude Code commits to a branch. Shaun reviews the diff. Claude deploys manually via `ansible-playbook` or `docker compose up -d --build`. This is the current model and it works.

**Level 2: Auto-deploy on merge to main:**
A webhook on git push triggers Ansible convergence on affected nodes. Changes to `projects/dashboard/` trigger dashboard rebuild on Node 2. Changes to `projects/agents/` trigger agent server rebuild on Node 1. This removes the manual deployment step.

**Level 3: Canary/progressive rollout:**
For the dashboard specifically, Next.js supports multi-zone deployment. A new version could be deployed alongside the old version, with a percentage of requests routed to the new version. But this is enterprise-grade complexity for a one-person system.

**Recommended: Level 1 now, Level 2 when Ansible automation is mature.** Level 3 is unnecessary.

### 4.6 Snapshot and Rollback

If the system breaks itself, recovery must be fast and reliable.

| Component | Snapshot Mechanism | Recovery Time | Recovery Method |
|-----------|-------------------|---------------|-----------------|
| Dashboard code | Git | Seconds | `git revert` + rebuild |
| Agent server code | Git | Seconds | `git revert` + rebuild |
| Ansible configs | Git | Seconds | `git revert` + re-converge |
| Qdrant data | Nightly backup (03:00) | Minutes | Restore from snapshot |
| Redis data | AOF persistence | Seconds | Auto-recovery on restart |
| Neo4j data | Nightly backup (03:15) | Minutes | Restore from export |
| Docker images | Docker image cache | Seconds | Roll back to previous image tag |
| System state | Prometheus metrics | N/A | Metrics preserved regardless |

**The worst case:** Claude Code deploys a breaking change to all three targets (dashboard, agents, Ansible) simultaneously, and the system is down. Recovery: `git revert --no-commit HEAD~3 && git commit -m "revert"` + re-deploy. Total downtime: 5-10 minutes. This is acceptable for a homelab.

### 4.7 Practical Assessment: Elegant or Dangerous?

**For a one-person homelab, self-modification is elegant with proper safeguards.**

The safeguards that make it work:
1. **Git as the immutable audit trail** -- every change is reversible
2. **Ansible as the convergence engine** -- the desired state is always declared, never improvised
3. **Docker as the isolation layer** -- a broken build does not affect the host
4. **Separate nodes** -- dashboard (Node 2) and agents (Node 1) are on different machines. Breaking one does not break the other.
5. **Claude as the operator** -- Claude Code is more careful than a human about testing changes before deployment (runs tests, checks syntax, validates configs)
6. **Shaun as the safety valve** -- Shaun reviews significant changes. The escalation protocol exists.

What would make it dangerous:
1. Auto-deploying to all nodes simultaneously without testing -- mitigate by deploying to one node at a time
2. Agents modifying their own core behavior without human review -- mitigate by keeping agent config changes at Level C (propose-and-wait)
3. No backups -- mitigate with existing nightly backup schedule
4. No monitoring of the modification process itself -- mitigate with commit hooks, deployment logs, and Prometheus alerts on service health

**The Emacs lesson applies:** The system will accumulate complexity over time. Documentation discipline (CLAUDE.md, MEMORY.md, ADRs, SYSTEM-SPEC.md) is the counterweight. As long as documentation stays accurate, the system remains one-person-maintainable.

---

## 5. Recommended Architecture

### 5.1 The Layered Interaction Architecture

```
+------------------------------------------------------------------+
|                    LAYER 0: AMBIENT                               |
|  PWA badge | Home page warmth | Agent constellation glow         |
|  "Is everything okay?" -- 2 second glance                        |
+------------------------------------------------------------------+
|                    LAYER 1: MONITOR                               |
|  Stream page | GPU cards | Service health | Agent status          |
|  "What happened?" -- 30 second scan                               |
+------------------------------------------------------------------+
|                    LAYER 2: FEEDBACK                              |
|  Inline thumbs up/down | Swipe approve/reject | Priority adjust  |
|  "That was good/bad" -- 5 seconds per item                       |
+------------------------------------------------------------------+
|                    LAYER 3: DIRECT                                |
|  Chat (text + voice) | Task dispatch | Goals | Command palette   |
|  "Do this next" -- 1-2 minutes                                    |
+------------------------------------------------------------------+
|                    LAYER 4: CREATE                                |
|  Agent config | Workflow editor | Prompt templates | Automations  |
|  "Build this workflow" -- 10-30 minutes                           |
+------------------------------------------------------------------+
|                    LAYER 5: DEVELOP                               |
|  Claudeman | Terminal page | Diff reviewer | Claude Code CLI      |
|  "Change the system" -- 1+ hours                                  |
+------------------------------------------------------------------+

        Mobile-native              Desktop-native
        <----------->              <----------->
        Layers 0-3                 Layers 0-5
```

### 5.2 Architecture Diagram

```
Phone / Desktop Browser
  |
  +-- Command Center PWA (DEV via athanor.local (runtime fallback dev.athanor.local:3001), Next.js 16)
  |     |
  |     +-- LAYER 0-1: Ambient + Monitor
  |     |     |-- Home (Furnace surface, agent constellation, Smart Stack)
  |     |     |-- Stream (unified activity with inline feedback)
  |     |     |-- GPUs, Monitoring, Services, Agents (domain views)
  |     |     |-- System Pulse strip (persistent, all pages)
  |     |     |-- CrewBar agent portraits (persistent, all pages)
  |     |
  |     +-- LAYER 2: Feedback
  |     |     |-- Inline feedback on all agent outputs (thumbs up/down)
  |     |     |-- Swipe actions on task cards (approve/reject)
  |     |     |-- Push notification action buttons (Android)
  |     |     |-- Deep-link to approval pages (iOS fallback)
  |     |
  |     +-- LAYER 3: Direct
  |     |     |-- Chat page (text + voice input via Web Speech API)
  |     |     |-- Task dispatch (POST to /v1/tasks)
  |     |     |-- Goals page (set/adjust/steer)
  |     |     |-- Command palette (Cmd+K / swipe-down)
  |     |
  |     +-- LAYER 4: Create (desktop-primary)
  |     |     |-- Preferences page (agent tuning)
  |     |     |-- Future: Workflow editor, prompt templates
  |     |
  |     +-- LAYER 5: Develop (desktop-only, linked apps)
  |           |-- /terminal page (xterm.js, escape hatch)
  |           |-- /review page (diff viewer, approve/reject)
  |           |-- Link to Claudeman (DEV:3000)
  |           |-- Link to OpenHands (Node 1:3000, when deployed)
  |
  +-- Claudeman (DEV:3000) -- LAYER 5
  |     |-- Multi-session Claude Code management
  |     |-- Live agent visualization
  |     |-- Overnight autonomous operation
  |     |-- Zero-lag mobile input
  |
  +-- Agent Server (Node 1:9000) -- BACKEND
  |     |-- 8 agents, task engine, GWT workspace
  |     |-- /v1/chat, /v1/tasks, /v1/goals, /v1/feedback
  |     |-- Redis pub/sub -> SSE -> dashboard
  |
  +-- Claude Code CLI (DEV) -- LAYER 5
        |-- COO operations, architecture, builds
        |-- MCP bridge to agent server
```

### 5.3 What to Build Next

Based on this research, the recommended build order -- sorted by impact per effort:

| Priority | Item | Effort | Layer | Impact |
|----------|------|--------|-------|--------|
| 1 | **Voice input in chat** | 1 day | 3 | Web Speech API, microphone button, massive mobile improvement |
| 2 | **Inline feedback on agent outputs** | 1 day | 2 | Thumbs up/down on every card in Stream/Activity |
| 3 | **Swipe actions on task cards** | 2 days | 2 | Swipe approve/reject on Tasks page |
| 4 | **Diff review page** | 3 days | 5 | Unified diff viewer with approve/reject, mobile-friendly |
| 5 | **Terminal page** | 2 days | 5 | xterm.js + WebSocket to DEV, escape hatch |
| 6 | **Deep links from notifications** | 1 day | 2 | Push notification taps open the relevant page with context |
| 7 | **Voice output for status** | 2 days | 0-1 | TTS for status responses in chat ("GPUs are at 15%") |
| 8 | **Workflow/prompt templates** | 5 days | 4 | Save and reuse common agent instructions |

### 5.4 What NOT to Build

| Item | Why Not |
|------|---------|
| Full IDE in dashboard | Shaun does not write code. AI does. An IDE is the wrong tool. |
| code-server deployment | Missing AI extensions make it irrelevant (confirmed in prior research) |
| Micro-frontend architecture | One-person team, one app. No team boundary problem to solve. |
| Native mobile app | PWA covers all needs. Capacitor only if iOS push is unreliable. |
| Auto-deploy pipeline (Level 2) | Current manual deploy works. Automate only when deploy frequency justifies it. |
| Separate staging environment | Overkill for homelab. Git revert is the staging/rollback mechanism. |

---

## 6. Existing Athanor Assets to Leverage

### 6.1 What Is Already Built

The Command Center (DEV via athanor.local (runtime fallback dev.athanor.local:3001)) already implements significant portions of the interaction architecture:

| Asset | Status | Maps to Layer |
|-------|--------|---------------|
| PWA with manifest, service worker | Deployed | 0 |
| System Pulse strip (SSE-driven) | Deployed | 0, 1 |
| Agent portrait bar (CrewBar) | Deployed | 0, 1 |
| Bottom nav (mobile) / Sidebar (desktop) | Deployed | Navigation |
| Command palette (Cmd+K) | Deployed | 3 |
| 5 Lens modes (URL param switching) | Deployed | Lateral navigation |
| GPUs page with cards | Deployed | 1 |
| Services health page | Deployed | 1 |
| Agents page | Deployed | 1 |
| Activity/Stream page | Deployed | 1 |
| Chat page (text input) | Deployed | 3 |
| Tasks page | Deployed | 1, 3 |
| Goals page | Deployed | 3 |
| Notifications page | Deployed | 2 |
| Push notifications (VAPID) | Deployed | 2 |
| SSE streaming (/api/stream) | Deployed | Real-time foundation |
| Gallery page | Deployed | 1 |
| Media page | Deployed | 1, 3 |
| Home automation page | Deployed | 1, 3 |
| Monitoring page | Deployed | 1 |
| Conversations page | Deployed | 1 |
| Workspace page | Deployed | 1 (diagnostic) |
| Preferences page | Deployed | 4 |
| Claudeman (DEV:3000) | Deployed | 5 |
| Voice pipeline (HA Wyoming) | Deployed | 3 (ambient only) |

### 6.2 Gaps to Fill

| Gap | Current State | Target State | Effort |
|-----|---------------|--------------|--------|
| Voice input in chat (browser) | Not implemented | Web Speech API microphone button | 1 day |
| Inline feedback (thumbs up/down) | Not on most pages | On every agent output card | 1 day |
| Swipe gestures on task cards | Not implemented | Swipe left/right for actions | 2 days |
| Diff review page | Not implemented | Unified diff with approve/reject | 3 days |
| Terminal page (xterm.js) | Not implemented | Embedded terminal, WebSocket to DEV | 2 days |
| Deep links from push notifications | Basic (opens app) | Opens specific page with context | 1 day |
| Push notification action buttons | Basic | Approve/Reject buttons (Android) | 1 day |

### 6.3 Dashboard Technical Stack (confirmed)

From the layout.tsx and dashboard rules:
- Next.js 16 + React 19 + Tailwind CSS v4 + shadcn/ui + oklch colors
- Fonts: Inter (data), Cormorant Garamond (headings), Geist Mono (metrics)
- SSE at `/api/stream` (5s interval) -- custom events, NOT Vercel AI SDK
- Agent proxy at `/api/agents/proxy` -- forwards to Node 1:9000
- LensProvider wraps layout inside Suspense
- Bottom nav on mobile (<768px), sidebar on desktop (>=768px)
- PWA manifest with amber theme color (#c8963c)
- Dark-first design with `--furnace-glow` ambient warmth

---

## 7. Risk Assessment Summary

### 7.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| xterm.js SSR issues in Next.js | Medium | Low | Dynamic import with `ssr: false` (standard pattern) |
| WebSocket terminal on mobile | Medium | Medium | Test thoroughly on iOS Safari and Android Chrome |
| Web Speech API browser support | Low | Low | Chrome and Safari both support it; graceful fallback to text |
| Swipe gesture conflicts with OS | Medium | Low | Threshold-based detection, visual feedback |
| Self-modification breaking the system | Medium | Medium | Git rollback, separate nodes, nightly backups |
| Push notification iOS limitations | Certain | Low | Deep-link to approval page as fallback |

### 7.2 Design Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Feature creep in Command Center | High | High | Strict layer discipline -- each feature maps to exactly one layer |
| Mobile UX degradation from desktop features | Medium | High | Test every feature on phone first, desktop second |
| Information overload at Layer 1 | Medium | Medium | Smart Stack widget surfacing, lens filtering |
| Feedback fatigue (too many thumbs up/down) | Medium | Medium | Batch feedback, smart defaults, fatigue detection |
| Terminal becoming primary interface | Low | High | Design it as escape hatch, not promoted path |

---

## 8. Open Questions

1. **Terminal backend location:** Should the node-pty WebSocket server run on DEV (where Claude Code lives) or Node 1 (more resources)? Recommendation: DEV, because that is where Claude Code processes run. Cross-node terminal adds latency and SSH complexity.

2. **Web Speech API vs dedicated STT:** Browser-native Web Speech API is zero-dependency but requires internet (sends audio to Google/Apple for processing). For a sovereignty-focused system, should we use the local Whisper model via the agent server instead? Recommendation: Start with Web Speech API (zero effort), migrate to local Whisper if privacy becomes a concern.

3. **Diff viewer library:** Several options exist -- `react-diff-viewer-continued`, Monaco editor diff view, or custom rendering with `diff2html`. Monaco is heavy (~2MB) but feature-complete. `react-diff-viewer-continued` is lightweight (~50KB) and sufficient for review purposes. Recommendation: `react-diff-viewer-continued` for the initial implementation.

4. **Layer 4 scope:** How much agent configuration should be exposed in the dashboard? Currently, agent behavior is defined in code (`agent-contracts.md`, system prompts, tool configs). Exposing all of this in the UI is a multi-week project. Recommendation: Start with goal setting and priority adjustment only. Deeper config stays in code, managed by Claude Code.

5. **Claudeman integration depth:** Should Command Center deep-link to specific Claudeman sessions? This requires Claudeman to expose a URL scheme for sessions (e.g., `DEV:3000/session/abc123`). Need to verify Claudeman's URL routing before implementing.

---

## Sources Index

### Integration Patterns
| Source | URL |
|--------|-----|
| Next.js Multi-Zones docs | https://nextjs.org/docs/app/guides/multi-zones |
| Module Federation + Next.js | https://medium.com/@livenapps/building-micro-frontends-with-next-js-and-module-federation-0e322230d751 |
| Iframe security risks (Qrvey, 2026) | https://qrvey.com/blog/iframe-security/ |
| Iframe security (WorkOS) | https://workos.com/blog/security-risks-of-iframes |
| Iframe compliance (Feroot, 2025) | https://www.feroot.com/blog/how-to-secure-iframe-compliance-2025/ |
| 8 reasons not to iframe embed | https://embeddable.com/blog/iframes-for-embedding |
| Next.js iframe guide (Caisy) | https://caisy.io/blog/nextjs-iframe-implementation |
| Vercel dashboard features | https://vercel.com/docs/dashboard-features |
| Vercel dashboard UX analysis | https://medium.com/design-bootcamp/vercels-new-dashboard-ux-what-it-teaches-us-about-developer-centric-design-93117215fe31 |
| Coolify docs | https://coolify.io/docs/get-started/introduction |

### Mobile Development Interaction
| Source | URL |
|--------|-----|
| GitHub Mobile code review | https://github.blog/changelog/2024-04-09-introducing-enhanced-code-review-on-github-mobile/ |
| GitHub Mobile | https://github.com/mobile |
| PWA push notifications guide | https://www.magicbell.com/blog/using-push-notifications-in-pwas |
| iOS PWA push best practices | https://www.magicbell.com/blog/best-practices-for-ios-pwa-push-notifications |
| Web Almanac 2025 PWA | https://almanac.httparchive.org/en/2025/pwa |
| Next.js PWA guide | https://nextjs.org/docs/app/guides/progressive-web-apps |
| Task management patterns | https://www.clappia.com/blog/task-management-system |
| Best to-do apps 2026 | https://zapier.com/blog/best-todo-list-apps/ |
| Mobile design trends 2026 | https://uxpilot.ai/blogs/mobile-app-design-trends |

### Voice Input
| Source | URL |
|--------|-----|
| Voice assistant integration | https://www.ptolemay.com/post/ai-powered-voice-assistant-integration-in-apps-elevating-usability-and-accessibility |
| React Native speech recognition | https://picovoice.ai/blog/react-native-speech-recognition/ |
| Voice agents 2026 trends | https://elevenlabs.io/blog/voice-agents-and-conversational-ai-new-developer-trends-2025 |
| AI voice agents guide | https://www.assemblyai.com/blog/ai-voice-agents |

### Interaction Layers & Progressive Disclosure
| Source | URL |
|--------|-----|
| Progressive disclosure for agentic AI | https://agentic-design.ai/patterns/ui-ux-patterns/progressive-disclosure-patterns |
| Agentic UI/UX patterns | https://agentic-design.ai/patterns/ui-ux-patterns |
| Primer progressive disclosure | https://primer.style/design/ui-patterns/progressive-disclosure/ |
| Mission control UX patterns | https://uxplanet.org/mission-control-software-ux-design-patterns-benchmarking-e8a2d802c1f3 |
| Mission control case study | https://medium.com/grace-kwan/case-study-mission-control-d410e562ec0e |
| Progressive disclosure (IDF) | https://www.interaction-design.org/literature/topics/progressive-disclosure |
| GitLab progressive disclosure | https://design.gitlab.com/patterns/progressive-disclosure/ |

### Self-Modifying Systems
| Source | URL |
|--------|-----|
| Internal Reprogrammability (Fowler) | https://martinfowler.com/bliki/InternalReprogrammability.html |
| Smalltalk (Wikipedia) | https://en.wikipedia.org/wiki/Smalltalk |
| Metacircular VM (ResearchGate) | https://www.researchgate.net/publication/200040544_Constructing_a_Metacircular_Virtual_Machine_in_an_Exploratory_Programming_Environment |
| GitOps principles (Codefresh) | https://codefresh.io/learn/gitops/ |
| GitOps workflow (HashiCorp) | https://developer.hashicorp.com/well-architected-framework/define-and-automate-processes/process-automation/gitops |
| Security of GitOps (OpenGitOps) | https://opengitops.dev/blog/sec-gitops/ |
| GitOps security (Microtica) | https://www.microtica.com/blog/security-misconfigurations-with-gitops |
| Secure GitOps (OpsMx) | https://www.opsmx.com/blog/embracing-secure-gitops-a-paradigm-shift-for-modern-software-and-ai-delivery/ |
| Secure SDLC with GitOps (InfoQ) | https://www.infoq.com/articles/secure-software-development-gitops/ |

### Terminal Embedding
| Source | URL |
|--------|-----|
| xterm.js | https://xtermjs.org/ |
| xterm.js GitHub | https://github.com/xtermjs/xterm.js |
| xterm.js + node-pty + WebSocket guide | https://ashishpoudel.substack.com/p/web-terminal-with-xtermjs-node-pty |
| Scalable node-pty + Socket.io | https://medium.com/@deysouvik700/efficient-and-scalable-usage-of-node-js-pty-with-socket-io-for-multiple-users-402851075c4a |
| xterm.js flow control | https://xtermjs.org/docs/guides/flowcontrol/ |

### Existing Athanor Research (cross-references)
| Source | Path |
|--------|------|
| Web development environments | `docs/research/2026-02-25-web-development-environments.md` |
| Command center UI design | `docs/research/2026-02-25-command-center-ui-design.md` |
| Human-in-the-loop patterns | `docs/research/2026-02-25-human-in-the-loop-patterns.md` |
| Novel interface patterns | `docs/research/2026-02-25-novel-interface-patterns.md` |
| Mobile PWA architecture | `docs/research/2026-02-25-mobile-pwa-architecture.md` |
| Command Center design | `docs/design/command-center.md` |
| ADR-019 Command Center | `docs/decisions/ADR-019-command-center.md` |
