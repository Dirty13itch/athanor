# Web-Based Development Environments for AI-Orchestrated Projects

**Date**: 2026-02-25
**Status**: Research complete
**Purpose**: Evaluate whether development can move from terminal-only (Claude Code in WSL2/tmux) to a web interface, potentially embedded in the Athanor dashboard. Research covers browser IDEs, AI-native development platforms, web terminal emulators, and the "orchestrator's workbench" concept.

---

## Context

Athanor's current development workflow: Claude Code CLI running in WSL2 tmux sessions on DEV (.215/.167), accessed via phone or local terminal. Shaun is an orchestrator, not a coder -- AI agents write code, Shaun reviews and steers. The question is whether a web-based interface could improve this workflow, enable mobile access, or be embedded into the Athanor dashboard (Next.js, DEV via athanor.local (runtime fallback dev.athanor.local:3001)).

Existing relevant docs:
- `docs/research/2026-02-13-claude-code-ecosystem.md` -- MCP servers, tools, orchestrators
- `docs/design/hybrid-development.md` -- Cloud/local AI coding architecture
- `docs/research/2026-02-25-cloud-coding-api-cascade.md` -- Multi-provider API cascade

---

## 1. code-server / VS Code in Browser

### Current State

code-server (by Coder) runs VS Code on a remote server, accessible through any browser. It is the most mature self-hosted browser IDE, widely deployed in homelabs and enterprises.

**Docker deployment** is straightforward:
```yaml
services:
  code-server:
    image: linuxserver/code-server
    ports:
      - "8443:8443"
    volumes:
      - ./config:/config
      - ./projects:/projects
    environment:
      - PASSWORD=your-password
```

Two maintained Docker images: `codercom/code-server` (official) and `linuxserver/code-server` (community, better config).

### Key Limitation: Extension Marketplace

code-server uses the **Open VSX Registry**, not the Microsoft Visual Studio Marketplace. This means:
- **No GitHub Copilot** extension (proprietary, MS Marketplace only)
- **No Claude Code VS Code extension** (MS Marketplace)
- **No Cursor/Windsurf-style AI features** (those are standalone forks)
- Many popular extensions ARE available (language support, themes, git tools)

This is the fundamental deal-breaker for AI-assisted development. The most valuable extensions for an AI-orchestrated workflow are unavailable.

### What It Is Good For

- Traditional code editing in a browser
- File browsing and management
- Terminal access (built-in xterm.js terminal)
- Git operations
- Syntax highlighting and IntelliSense for supported languages

### Evaluation

| Criterion | Rating |
|-----------|--------|
| Self-hostable | Yes -- Docker, any Linux host |
| LAN/local network | Yes |
| Mobile experience | Functional but cramped -- VS Code is desktop-first |
| Embed in Next.js dashboard | No -- standalone app, would need iframe |
| Real-time collaboration | Limited (no Live Share in Open VSX) |
| Resource requirements | Low (~512 MB RAM, minimal CPU) |
| Maturity | High -- 79K+ GitHub stars, active development |

### Verdict

**Not recommended for Athanor.** The missing AI extensions make it irrelevant for an AI-orchestrated workflow. It solves the wrong problem -- Shaun doesn't need a code editor in a browser, he needs an AI command interface in a browser.

### Sources
- https://github.com/coder/code-server
- https://hub.docker.com/r/linuxserver/code-server
- https://docs.linuxserver.io/images/docker-code-server/
- https://www.xda-developers.com/i-self-hosted-this-vs-code-fork/

---

## 2. Cursor / Windsurf / AI-Native IDEs

### Cursor

Cursor is a standalone VS Code fork by Anysphere, Inc. with AI as a core architectural component. Over 1M daily active developers, $1B+ ARR, $29.3B valuation.

- **No web/browser version.** Desktop only (Mac, Windows, Linux).
- **No self-hosting.** AI features require Cursor's cloud infrastructure.
- **Visual Editor** (Cursor 2.0+): drag-and-drop UI editing within the desktop app, not a web feature.
- Cursor is building a web browser as part of agent research, but no self-hostable browser IDE exists.

### Windsurf (Codeium)

"First agentic IDE" by Codeium. Cascading AI that flows with developer intent.

- **No web/browser version.** Desktop IDE + plugins for VS Code/JetBrains/Neovim.
- **No self-hosting.** Enterprise tier may offer private deployment, but not self-hosted browser access.
- AI features (Cascade, Flows) are cloud-dependent.

### Google Antigravity

Agent-first development platform launched November 2025. Built on a VS Code fork.

- **Agent Manager**: Mission Control dashboard for spawning, monitoring, and interacting with multiple autonomous agents across workspaces.
- **Browser Control**: Agents can autonomously plan, code, test via browser using Gemini 2.5 Computer Use.
- **Free during public preview** for individual developers with personal Gmail accounts.
- **NOT self-hostable.** Runs on Google infrastructure. Requires Google account.
- Uses Gemini 3 Pro (not configurable to other models during preview).

### Evaluation Summary

| IDE | Web Version | Self-Hostable | Custom Models |
|-----|-------------|---------------|---------------|
| Cursor | No | No | No (Cursor cloud) |
| Windsurf | No | No | No (Codeium cloud) |
| Google Antigravity | Cloud-hosted | No | No (Gemini only) |

### Verdict

**None of these are viable for Athanor.** All are desktop-only or cloud-hosted, none are self-hostable, none support custom model endpoints. The Antigravity Agent Manager concept is worth studying as a UI pattern for the orchestrator's workbench, but the platform itself is a non-starter.

### Sources
- https://cursor.com/
- https://thenewstack.io/cursor-2-0-ide-is-now-supercharged-with-ai-and-im-impressed/
- https://windsurf.com/
- https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/
- https://www.baytechconsulting.com/blog/google-antigravity-ai-ide-2026

---

## 3. Claude Code in a Browser

This is the most directly relevant section. Multiple approaches exist, from Anthropic's official solutions to community-built wrappers.

### 3a. Claude Code on the Web (Official, Anthropic-hosted)

Launched November 2025 at claude.ai/code. Research preview for Pro/Max/Team/Enterprise users.

**How it works:**
1. Connect GitHub account, install Claude GitHub app
2. Submit coding task via browser
3. Repository cloned to Anthropic-managed VM
4. Claude executes task in isolated environment
5. Review changes via diff view, iterate with comments
6. Create PR when satisfied

**Key features:**
- Parallel task execution across multiple sessions
- Diff view for reviewing changes before PR creation
- Session handoff: send tasks from terminal to web with `&` prefix, pull web sessions to terminal with `/teleport`
- Available on iOS and Android Claude apps
- Supports SessionStart hooks for custom environment setup

**Limitations:**
- GitHub-only (no GitLab, no local repos)
- Runs on Anthropic infrastructure, not your machines
- Cannot access local filesystem, MCP servers, or project configuration
- Shares rate limits with all Claude usage
- Not self-hostable

**Verdict:** Useful for kicking off background tasks on public repos, but fundamentally wrong for Athanor. We need local filesystem access, local MCP servers, and local model inference.

### 3b. Remote Control (Official, runs locally)

Released February 25, 2026. Research preview for Pro/Max subscribers.

**How it works:**
1. Run `claude remote-control` (or `/rc` in existing session) in terminal
2. Generates session URL and QR code
3. Open URL on phone/tablet/browser via claude.ai/code
4. Session runs LOCALLY on your machine -- web/mobile is just a window into it

**Key features:**
- Full local environment: filesystem, MCP servers, tools, project config all available
- Conversation syncs across all connected devices (terminal + browser + phone)
- Auto-reconnect on network drop or laptop sleep
- No inbound ports opened -- outbound HTTPS only, through Anthropic API
- One remote session per Claude Code instance

**Limitations:**
- Requires Pro/Max subscription (API keys not supported)
- Terminal must stay open (the local process must keep running)
- 10-minute timeout on extended network outage
- One remote session at a time per instance
- Traffic routes through Anthropic's API (privacy consideration)
- Not self-hosted infrastructure -- depends on claude.ai being available

**Verdict:** This is the zero-effort winner for immediate mobile access to Claude Code. Run `claude remote-control` on DEV, access from phone via claude.ai app. The dependency on Anthropic's API is the only concern -- if claude.ai is down, remote access is down.

### 3c. claude-code-web (Community, npm)

Open-source web wrapper for Claude Code CLI. MIT license.

**Architecture:**
```
Browser (xterm.js) <--WebSocket--> Express Server <--node-pty--> Claude Code CLI
```

**Key features:**
- xterm.js terminal with full ANSI color and rich output support
- Multi-session management with named sessions and custom working directories
- Session persistence (last 1000 lines buffered, survives browser disconnect)
- VS Code-style split view for side-by-side terminals
- Authentication enabled by default (auto-generated tokens)
- HTTPS support with SSL certificates
- Rate limiting (100 req/min per IP)

**Installation:**
```bash
npx claude-code-web                    # Quick start
npx claude-code-web --port 8080       # Custom port
```

**Requirements:** Node.js >= 16, Claude Code CLI installed.

**Verdict:** Solid, minimal, works today. Good for quick remote access to Claude Code. Not as feature-rich as Claudeman but simpler to deploy.

### 3d. Claudeman (Community, tmux-based)

The most impressive community solution. A "Claude Code Control Plane" with a mobile-first web UI.

**Architecture:**
```
Browser (xterm.js + React/Ink) <--SSE--> Fastify Server <--tmux--> Claude Code CLI
```

**Key features:**
- **Zero-lag input**: Mosh-inspired local echo system. Keystrokes render at 0ms via DOM overlay inside xterm.js. Server echo arrives 200-300ms later and seamlessly replaces overlay. Typing feels instant regardless of network latency.
- **Live agent visualization**: Monitors Task tool invocations, shows background agents as draggable floating windows with animated connection lines to parent session. Status badges (active/idle/completed).
- **Respawn controller**: Detects idle sessions, sends continue prompts, cycles `/clear` -> `/init` for fresh context. Can run unattended 24+ hours with circuit breaker to prevent thrashing.
- **Multi-session dashboard**: Up to 20 parallel sessions at 60fps. Per-session token/cost tracking. Auto-compact at 110k tokens, auto-clear at 140k.
- **Anti-flicker pipeline**: 6-layer architecture: PTY -> 16ms server batch -> DEC 2026 wrap -> SSE -> client rAF -> xterm.js.
- **Mobile-first**: 44px touch targets, swipe navigation, keyboard accessory bar with quick actions, safe area support for iPhone notches.
- **tmux persistence**: Sessions survive server restarts and network drops.

**Tech stack:** Fastify 5.x, TypeScript 5.5, Node.js 18+, xterm.js, tmux. 1435+ tests.

**Installation:**
```bash
curl -fsSL https://raw.githubusercontent.com/Ark0N/claudeman/master/install.sh | bash
claudeman web            # http://localhost:3000
claudeman web --https    # HTTPS for remote access
```

**Built-in presets:** solo-work, subagent-workflow, team-lead, overnight-autonomous.

**Published sub-package:** `xterm-zerolag-input` on npm -- standalone zero-lag input overlay for xterm.js.

**Verdict:** This is the best community solution by a wide margin. The zero-lag input, agent visualization, respawn controller, and mobile-first design directly address the orchestrator workflow. The overnight autonomous mode with circuit breaker is exactly what Athanor needs for unattended builds.

### 3e. CloudCLI / claude-code-ui (Community)

Web UI for managing Claude Code, Cursor CLI, and Codex sessions.

**Tech stack:** React 18 + Vite frontend, Node.js + Express backend, CodeMirror editor, Tailwind CSS.

**Features:** Interactive chat interface, file explorer with syntax highlighting, git integration, session management. Discovers existing CLI sessions and groups them into projects.

**Verdict:** More of a project management overlay than a terminal interface. Less relevant than Claudeman for the orchestrator use case.

### 3f. Other Remote Access Solutions

- **247-claude-code-remote**: Mobile-first web terminal with Cloudflare Tunnel. Session persistence via tmux.
- **remotelab**: Access any AI CLI tool from any browser via HTTPS. Requires a domain managed by Cloudflare ($1-12/year).
- **Claude-Code-Remote**: Control via email, Discord, or Telegram. Start tasks locally, get notifications on completion, send new commands by replying.

### Comparison Matrix

| Solution | Self-Hosted | Local FS | Mobile | Multi-Session | Auth | Effort |
|----------|-------------|----------|--------|---------------|------|--------|
| Claude Code Web (official) | No | No | Yes | Yes | Anthropic | Zero |
| Remote Control (official) | Hybrid | Yes | Yes | No (1/instance) | Anthropic | Zero |
| claude-code-web | Yes | Yes | Yes | Yes | Token | Low |
| **Claudeman** | **Yes** | **Yes** | **Yes** | **Yes (20)** | **Configurable** | **Low** |
| CloudCLI | Yes | Yes | Yes | Yes | Local | Low |
| 247-remote | Yes | Yes | Yes | Yes | Cloudflare | Medium |

### Sources
- https://code.claude.com/docs/en/claude-code-on-the-web
- https://code.claude.com/docs/en/remote-control
- https://github.com/vultuk/claude-code-web
- https://www.npmjs.com/package/claude-code-web
- https://github.com/Ark0N/Claudeman
- https://github.com/siteboon/claudecodeui
- https://github.com/QuivrHQ/247-claude-code-remote
- https://github.com/trmquang93/remotelab
- https://github.com/JessyTsui/Claude-Code-Remote

---

## 4. AI Software Engineering Platforms (OpenHands, SWE-agent, Devin)

### OpenHands (formerly OpenDevin)

The most relevant platform in this category. Open-source (MIT), self-hostable, with a web UI.

**Architecture:**
- Python SDK (75.8%) + React SPA frontend (22.1% TypeScript)
- Sandboxed Docker execution environment for each task
- Model-agnostic: works with Anthropic, OpenAI, Google, local models (Ollama, LM Studio)
- 473+ contributors, 6091 commits, actively developed

**Web UI:** React single-page application at localhost:3000. Conversational interface where you describe tasks, AI agent plans and executes in sandboxed Docker, shows reasoning and code changes. You can steer mid-run.

**Self-hosting:**
```bash
# Option A: uv (recommended)
uv tool install openhands --python 3.12
openhands serve

# Option B: Docker
docker run -d -p 3000:3000 foundationmodels/openhands:latest
```

**System requirements:** Minimum 4 GB RAM, modern processor. GPU optional (16 GB VRAM recommended for local models). Tested with OpenHands 1.4 + Docker 27.x as of February 2026.

**Performance:** 77.6% SWE-bench Verified. Competitive with commercial alternatives.

**Local model support:** Can use Qwen3-32B via vLLM/Ollama/LM Studio OpenAI-compatible API. Requires models tuned for instruction-following and agent behavior.

**Evaluation:**

| Criterion | Rating |
|-----------|--------|
| Self-hostable | Yes -- Docker or uv |
| LAN/local network | Yes |
| Mobile experience | Responsive web app |
| Embed in Next.js | No -- standalone app (iframe possible) |
| Real-time observation | Yes -- live reasoning + code changes |
| Resource requirements | Low (4 GB RAM) + Docker |
| Maturity | High -- 77.6% SWE-bench, 473 contributors |

**Verdict:** Worth deploying as a second AI coding interface alongside Claude Code. Particularly useful for tasks where you want to point at a GitHub issue and say "fix this" without the overhead of managing a Claude Code session. The Docker sandbox is good for safety. However, it is a separate tool, not embeddable into the Athanor dashboard.

### SWE-agent (Princeton/Stanford)

Research-focused tool optimized for resolving GitHub issues. Innovative Agent-Computer Interface design. Less suitable as a general development environment.

- Not a general-purpose AI coding tool
- Minimal web UI (research interface)
- Optimized for benchmark tasks, not interactive development
- Open-source but academic focus

**Verdict:** Not relevant for Athanor. The UI patterns are not transferable to an orchestrator workflow.

### Devin (Cognition AI)

The original "AI software engineer." Impressive UI with planning, coding, browsing, and deployment.

- **Proprietary.** Not self-hostable. Not open-source.
- Cloud-hosted with per-task pricing.
- Slick UI is the gold standard for AI coding interfaces.

**Verdict:** Not viable (proprietary, cloud-only). The UI design is worth studying as inspiration for the orchestrator's workbench concept.

### Sources
- https://github.com/OpenHands/OpenHands
- https://openhands.dev/
- https://docs.openhands.dev/openhands/usage/run-openhands/local-setup
- https://arxiv.org/abs/2407.16741
- https://localaimaster.com/blog/openhands-vs-swe-agent

---

## 5. Web Terminal Emulators

For embedding a terminal in a web page that can handle Claude Code's rich output (ANSI colors, Ink framework spinners, tool call displays).

### xterm.js

The industry standard. Used by VS Code, code-server, Claudeman, claude-code-web, and virtually every web terminal.

- TypeScript library, actively maintained
- Full ANSI escape code support (colors, cursor positioning, text formatting)
- Works with tmux, vim, and curses-based applications
- GPU-accelerated WebGL renderer for smooth 60fps output
- Unicode/CJK/emoji support
- Mouse event support
- Addon system (fit, search, web-links, webgl, serialize)

**React integration:** `react-xtermjs` by Qovery provides modern React hooks-based wrapper. Older wrappers (`xterm-for-react`, `xterm-react`) exist but are less maintained.

**Next.js consideration:** xterm.js requires browser APIs (DOM, canvas). Must use dynamic import with `ssr: false` in Next.js to avoid server-side rendering issues.

```typescript
// Next.js dynamic import pattern
const XTerm = dynamic(() => import('react-xtermjs'), { ssr: false });
```

### ttyd

C-based, minimal, fast. Single binary that exposes any CLI command as a web terminal.

```bash
ttyd -p 8080 bash                    # Basic shell
ttyd -p 8080 tmux new -A -s main    # Attach to tmux session
ttyd -p 8080 claude                  # Direct Claude Code access
```

- Built on libwebsockets (C) and xterm.js
- Very low resource usage (~5 MB RAM)
- SSL/TLS support built-in
- Basic authentication
- Read-only mode option
- No session management (single command per instance)

### Wetty

Node.js-based. SSH connection from browser to remote host.

- Uses xterm.js on frontend
- Connects via SSH (can target remote machines)
- Supports custom SSH commands
- Docker image available

### GoTTY

Go-based. Similar to ttyd but less actively maintained.

- Single binary
- WebSocket-based
- Read/write modes
- Less feature-rich than ttyd

### Comparison

| Tool | Language | RAM | Features | Maintenance |
|------|----------|-----|----------|-------------|
| **xterm.js** (library) | TypeScript | N/A (library) | Complete terminal emulation | Active (VS Code team) |
| **ttyd** | C | ~5 MB | Minimal, fast | Active |
| **Wetty** | Node.js | ~50 MB | SSH bridge | Moderate |
| **GoTTY** | Go | ~10 MB | Basic | Low |

### Can They Handle Claude Code's Rich Output?

Yes. Claude Code uses the Ink framework (React for CLIs) which renders via ANSI escape codes. All xterm.js-based solutions handle this correctly:
- Colored text and syntax highlighting
- Spinner animations
- Progress bars
- Tool call displays with borders/boxes
- Interactive prompts
- Real-time streaming

Tested indirectly via Claudeman and claude-code-web, both of which report full compatibility with Claude Code's Ink-based UI.

### Embedding in Next.js Dashboard

The most viable approach for the Athanor dashboard:

```
Dashboard (Next.js, DEV via athanor.local (runtime fallback dev.athanor.local:3001))
  |-- Terminal Page
  |     |-- react-xtermjs component
  |     |-- WebSocket connection to backend
  |
  Backend (Node.js on DEV or Node 1)
    |-- node-pty spawning Claude Code process
    |-- WebSocket server relaying PTY I/O
```

This is exactly what claude-code-web already implements. The architecture could be adapted as a dashboard page.

### Sources
- https://xtermjs.org/
- https://github.com/xtermjs/xterm.js
- https://tsl0922.github.io/ttyd/
- https://www.qovery.com/blog/react-xtermjs-a-react-library-to-build-terminals
- https://github.com/Qovery/react-xtermjs
- https://sabujkundu.com/best-open-source-web-terminals-for-embedding-in-your-browser/

---

## 6. Jupyter-Like Paradigms

### JupyterLab + AI Agents

Several projects bring AI agents into JupyterLab:

- **jupyter-ai-agents** (Datalayer): MCP tools for JupyterLab, chat interface for notebook interaction. Uses Pydantic AI for agent orchestration.
- **Notebook Intelligence (NBI)**: AI coding assistant and extensible framework for JupyterLab. Handles orchestration between LLMs and tools.
- **Runcell**: AI agent that writes Python, executes cells, debugs, and explains results in real-time. Leading the "Notebook Wars of 2025."
- **jupyter-ai** (official Jupyter): Generative AI extension, brings LLM chat and magic commands to notebooks.

### Evaluation for Orchestrator Workflow

| Criterion | Jupyter Paradigm |
|-----------|-----------------|
| Self-hostable | Yes (JupyterHub, Docker) |
| LAN/local network | Yes |
| Mobile experience | Poor -- notebook UI is desktop-centric |
| Embed in Next.js | No (standalone Tornado server) |
| Orchestrator fit | Low -- cell-based execution model is wrong paradigm |

### Why Notebooks Are Wrong for This

The notebook paradigm is designed for **exploratory data science** -- write code in cells, see output, iterate. An orchestrator's workflow is fundamentally different:

1. **Task dispatch, not cell execution**: The orchestrator describes what needs to be done, not how to do it step-by-step.
2. **Conversation, not cells**: AI coding is conversational ("fix the auth bug") not procedural ("run this cell").
3. **Multi-file changes**: Software development spans entire codebases. Notebooks are single-file.
4. **Review, not run**: The orchestrator reviews AI output, not code execution results.

### Verdict

**Not recommended for Athanor.** Notebooks solve the wrong problem. The cell-based paradigm forces the orchestrator into a programmer's workflow when the whole point is to operate at a higher level. Conversational AI interfaces (Claude Code, OpenHands) are fundamentally better for this use case.

### Sources
- https://github.com/datalayer/jupyter-ai-agents
- https://blog.jupyter.org/building-ai-agents-for-jupyterlab-using-notebook-intelligence-0515d4c41a61
- https://www.runcell.dev/
- https://github.com/jupyterlab/jupyter-ai

---

## 7. The Orchestrator's Workbench Concept

### What Would It Be?

Not an IDE. Not a notebook. A **mission control for AI-driven development**. The orchestrator:
- Assigns tasks to AI agents
- Monitors progress in real-time
- Reviews output (diffs, test results, reasoning)
- Approves or steers
- Manages multiple parallel workstreams

### Does Anything Like This Exist?

**GitHub Agent HQ / Mission Control** (announced Universe 2025):
- Assign tasks to Copilot across repos
- Watch real-time session logs showing reasoning and decisions
- Steer mid-run (pause, refine, restart)
- Jump to resulting PRs
- Consistent interface across GitHub, VS Code, mobile, CLI
- Multi-agent: integrates Copilot + third-party agents (Anthropic, OpenAI, Google, Cognition, xAI)

Limitations: GitHub-hosted, not self-hostable, requires GitHub Copilot subscription, tightly coupled to GitHub ecosystem.

**Google Antigravity Agent Manager**:
- Dashboard for spawning, monitoring, and interacting with multiple agents
- Agents plan entire features, execute across files, test via browser control
- Asynchronous execution across different workspaces

Limitations: Google-hosted, not self-hostable, Gemini-only.

**Devin UI** (Cognition AI):
- Task assignment with natural language
- Agent shows planning, coding, browsing, debugging in real-time
- Terminal, editor, and browser panels visible simultaneously
- Deploy button for shipping results

Limitations: Proprietary, cloud-only, expensive.

### What Would Athanor's Orchestrator Workbench Need?

Based on the patterns from these platforms, a self-hosted workbench would need:

1. **Task Dispatch Panel**: Natural language task input -> routes to appropriate agent (Claude Code, local Qwen3, OpenHands). Shows estimated cost/time.

2. **Session Monitor**: Real-time view of active AI sessions. Shows:
   - Current reasoning/action (streaming)
   - Token usage and cost
   - Files modified
   - Tests run/passed/failed
   - Time elapsed

3. **Multi-Session Grid**: Like Claudeman's multi-session dashboard but integrated with the existing Athanor dashboard. See all active Claude Code sessions, agent tasks, and background jobs at a glance.

4. **Diff Reviewer**: When an agent completes a task, show the diff for review. Approve, reject, or send back with feedback. Like Claude Code on the web's diff view but for local sessions.

5. **Build Manifest Integration**: Show the BUILD-MANIFEST.md as a kanban or checklist. Click an item to dispatch it as a task.

6. **Agent Activity Feed**: Already partially built (Athanor dashboard Activity page). Extend with real-time streaming from agent task execution.

7. **Terminal Fallback**: Embedded xterm.js terminal for when you need to drop into a full Claude Code session.

### How Close Is Athanor Already?

The existing infrastructure covers significant ground:

| Component | Status | Gap |
|-----------|--------|-----|
| Agent task queue | Deployed (POST /v1/tasks) | No web dispatch UI |
| Agent monitoring | Deployed (Activity page) | Not real-time streaming |
| GPU monitoring | Deployed (GPU page) | Done |
| Service health | Deployed (26 checks) | Done |
| Terminal access | Not deployed | Need xterm.js + WebSocket |
| Diff review | Not deployed | Need git diff rendering |
| Build manifest view | Not deployed | Need manifest parser |
| Multi-session view | Not deployed | Need Claude Code session bridge |

### Build Path

The workbench can be built incrementally in the existing Next.js dashboard:

**Phase 1 -- Terminal Page** (days):
Add a dashboard page with xterm.js. WebSocket to a node-pty backend on DEV or Node 1. Immediate Claude Code access from the browser.

**Phase 2 -- Task Dispatch** (days):
Dashboard page to POST tasks to the agent server (already has API). Show task queue, status, results. Wire up the existing `/v1/tasks` endpoint.

**Phase 3 -- Live Activity Stream** (week):
SSE or WebSocket from agent server to dashboard. Show real-time agent reasoning and tool use as tasks execute. Extend the existing GWT workspace broadcast mechanism.

**Phase 4 -- Session Manager** (week):
Integration with Claudeman or claude-code-web for multi-session management. Show active Claude Code sessions with token usage and status.

**Phase 5 -- Diff Reviewer** (week):
Git diff rendering component. When a task produces commits, show the diff for review/approval before merge.

### Sources
- https://github.blog/ai-and-ml/github-copilot/how-to-orchestrate-agents-using-mission-control/
- https://visualstudiomagazine.com/articles/2025/10/28/github-introduces-agent-hq-to-orchestrate-any-agent-any-way-you-work.aspx
- https://www.baytechconsulting.com/blog/google-antigravity-ai-ide-2026
- https://humanwhocodes.com/blog/2026/01/coder-orchestrator-future-software-engineering/
- https://zackproser.com/blog/orchestrator-pattern

---

## Comparative Summary

### Full Comparison Matrix

| Solution | Self-Host | Local FS | Mobile | Dashboard Embed | Multi-Session | Local Models | Maturity | Effort |
|----------|-----------|----------|--------|-----------------|---------------|--------------|----------|--------|
| code-server | Yes | Yes | Poor | Iframe | No | N/A | High | Low |
| Cursor/Windsurf | No | Yes | No | No | No | No | High | N/A |
| Claude Code Web (official) | No | No | Yes | No | Yes | No | Medium | Zero |
| Remote Control (official) | Hybrid | Yes | Yes | No | No | Via MCP | Medium | Zero |
| **claude-code-web** | **Yes** | **Yes** | **Yes** | **Adaptable** | **Yes** | **Via Claude** | **Medium** | **Low** |
| **Claudeman** | **Yes** | **Yes** | **Yes** | **No (standalone)** | **Yes (20)** | **Via Claude** | **Medium** | **Low** |
| CloudCLI | Yes | Yes | Yes | No | Yes | Partial | Low | Low |
| **OpenHands** | **Yes** | **Sandboxed** | **Yes** | **No (standalone)** | **Yes** | **Yes (any API)** | **High** | **Medium** |
| ttyd | Yes | Yes | Basic | Iframe | No | N/A | High | Low |
| JupyterLab | Yes | Yes | Poor | No | No | Yes | High | Medium |
| GitHub Agent HQ | No | Via GitHub | Yes | No | Yes | Partial | Medium | N/A |
| Google Antigravity | No | No | No | No | Yes | No | Low | N/A |
| **Custom Workbench** | **Yes** | **Yes** | **Yes** | **Native** | **Yes** | **Yes** | **None** | **High** |

---

## Recommendation

### Layered Strategy (Immediate -> Long-term)

#### Layer 1: Remote Control (Today, Zero Effort)

Use Anthropic's Remote Control feature immediately.

```bash
# On DEV (WSL2)
claude remote-control
# Scan QR code with phone, or open URL in any browser
```

This gives mobile access to Claude Code with full local environment (MCP servers, filesystem, tools) via claude.ai. No infrastructure to deploy. Works now.

**Limitation:** Depends on Anthropic API availability. One session at a time. Traffic routes through Anthropic.

#### Layer 2: Claudeman (This Week, Low Effort)

Deploy Claudeman on DEV for a self-hosted, zero-dependency-on-Anthropic web interface.

```bash
# On DEV (WSL2)
curl -fsSL https://raw.githubusercontent.com/Ark0N/Claudeman/master/install.sh | bash
claudeman web --https
# Access at https://192.168.1.167:3000 from any device on LAN
```

This provides:
- Multi-session management (up to 20 parallel Claude Code sessions)
- Zero-lag mobile input
- Live agent visualization
- Overnight autonomous operation with respawn controller
- No dependency on Anthropic's infrastructure for the UI layer

Claudeman is LAN-accessible. Remote access via Tailscale was evaluated but cancelled (ADR-016 superseded 2026-02-26).

#### Layer 3: Dashboard Terminal Page (Next Build Session)

Add an xterm.js terminal page to the Athanor dashboard. This is the first step toward the orchestrator's workbench.

```
Athanor Dashboard (DEV via athanor.local (runtime fallback dev.athanor.local:3001))
  |-- New page: /terminal
  |     |-- react-xtermjs component (dynamic import, ssr: false)
  |     |-- WebSocket to terminal backend
  |
Terminal Backend (Node 1 or DEV)
  |-- node-pty spawning Claude Code or bash
  |-- WebSocket server
```

This embeds terminal access directly into the dashboard alongside GPU monitoring, agent activity, and service health. One URL for everything.

#### Layer 4: Task Dispatch + Live Monitoring (Tier 9)

Extend the dashboard with:
- Task dispatch form (POST to /v1/tasks on agent server)
- Real-time task execution streaming (SSE from agent server)
- Diff viewer for completed tasks
- Build manifest visualization

This builds the orchestrator's workbench incrementally using existing Athanor infrastructure.

#### Layer 5: OpenHands (Parallel Track)

Deploy OpenHands as a complementary AI coding interface.

```bash
# On Node 1 (has plenty of RAM)
uv tool install openhands --python 3.12
openhands serve
# Access at http://192.168.1.244:3000
```

Configure to use Qwen3-32B via vLLM (Node 1:8000) or Claude via LiteLLM (VAULT:4000). Useful for:
- GitHub issue resolution ("fix issue #42")
- Tasks that benefit from Docker sandbox isolation
- Tasks where you want a different AI interface than Claude Code

### What NOT to Do

1. **Do not deploy code-server.** The missing AI extensions make it pointless for this use case.
2. **Do not try to self-host Cursor/Windsurf.** They are not designed for it.
3. **Do not use Jupyter for software development orchestration.** Wrong paradigm.
4. **Do not build a full custom IDE.** The orchestrator does not need to edit code -- AI does.
5. **Do not depend solely on Anthropic-hosted solutions.** Remote Control is great but needs a self-hosted fallback.

### Priority Order

| Priority | Action | Effort | Unblocks |
|----------|--------|--------|----------|
| 1 | Use Remote Control (`claude remote-control`) | Zero | Mobile access now |
| 2 | Deploy Claudeman on DEV | 30 min | Self-hosted web UI, multi-session, overnight autonomous |
| 3 | Add terminal page to dashboard | 1-2 days | Integrated development from one URL |
| 4 | Deploy OpenHands on Node 1 | 1 hour | Alternative AI coding interface |
| 5 | Build task dispatch + monitoring | 3-5 days | Orchestrator's workbench v1 |
| 6 | Build diff reviewer + manifest view | 3-5 days | Full orchestrator's workbench |

---

## Open Questions

1. **Claudeman stability**: It is a relatively new project. Need to test thoroughly before depending on it for overnight autonomous runs. The circuit breaker and respawn logic is promising but unverified in our environment.

2. **xterm.js + Next.js SSR**: Dynamic import with `ssr: false` is the standard approach but can cause layout shifts. The dashboard already uses client-side rendering for charts, so this should be manageable.

3. **Terminal backend location**: Should the node-pty backend run on DEV (where Claude Code runs) or Node 1? DEV is closer to the Claude Code process. Node 1 has more resources. If the backend runs on Node 1, it needs SSH access to DEV to spawn Claude Code there. Simplest: run backend on DEV, dashboard on Node 2 fetches via WebSocket across LAN.

4. **Security for web terminal**: Any web-accessible terminal is a high-value target. The dashboard currently has no authentication. Before exposing terminal access, need at minimum token-based auth. LAN-only access is acceptable for now (trusted network).

5. **Remote Control vs Claudeman**: Both solve mobile access. Remote Control is simpler (zero deploy) but single-session and Anthropic-dependent. Claudeman is more capable (multi-session, agent viz, autonomous) but requires deployment and maintenance. They can coexist -- Remote Control for quick phone checks, Claudeman for serious work sessions.

6. **OpenHands + local Qwen3**: OpenHands recommends using models with strong instruction-following. Qwen3-32B-AWQ is adequate but not optimized for agent behavior. Need to test whether it produces good results in OpenHands or whether cloud models are required for acceptable quality.

---

## Sources Index

| Source | URL | Date |
|--------|-----|------|
| Claude Code on the Web docs | https://code.claude.com/docs/en/claude-code-on-the-web | 2026-02-25 |
| Claude Code Remote Control docs | https://code.claude.com/docs/en/remote-control | 2026-02-25 |
| claude-code-web (npm) | https://github.com/vultuk/claude-code-web | 2026-02-25 |
| Claudeman | https://github.com/Ark0N/Claudeman | 2026-02-25 |
| CloudCLI / claude-code-ui | https://github.com/siteboon/claudecodeui | 2026-02-25 |
| 247-claude-code-remote | https://github.com/QuivrHQ/247-claude-code-remote | 2026-02-25 |
| remotelab | https://github.com/trmquang93/remotelab | 2026-02-25 |
| OpenHands | https://github.com/OpenHands/OpenHands | 2026-02-25 |
| OpenHands local setup | https://docs.openhands.dev/openhands/usage/run-openhands/local-setup | 2026-02-25 |
| code-server | https://github.com/coder/code-server | 2026-02-25 |
| xterm.js | https://xtermjs.org/ | 2026-02-25 |
| react-xtermjs | https://github.com/Qovery/react-xtermjs | 2026-02-25 |
| ttyd | https://tsl0922.github.io/ttyd/ | 2026-02-25 |
| Cursor | https://cursor.com/ | 2026-02-25 |
| Windsurf | https://windsurf.com/ | 2026-02-25 |
| Google Antigravity | https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/ | 2026-02-25 |
| GitHub Agent HQ | https://github.blog/news-insights/company-news/welcome-home-agents/ | 2026-02-25 |
| GitHub Mission Control guide | https://github.blog/ai-and-ml/github-copilot/how-to-orchestrate-agents-using-mission-control/ | 2026-02-25 |
| jupyter-ai-agents | https://github.com/datalayer/jupyter-ai-agents | 2026-02-25 |
| Orchestrator pattern | https://zackproser.com/blog/orchestrator-pattern | 2026-02-25 |
| Coder to Orchestrator essay | https://humanwhocodes.com/blog/2026/01/coder-orchestrator-future-software-engineering/ | 2026-02-25 |
| Agentic Coding Trends 2026 | https://resources.anthropic.com/hubfs/2026%20Agentic%20Coding%20Trends%20Report.pdf | 2026-02-25 |
