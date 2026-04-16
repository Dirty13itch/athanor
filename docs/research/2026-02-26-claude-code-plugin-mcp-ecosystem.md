# Claude Code Plugin and MCP Ecosystem: February 2026 Landscape

## Context

Comprehensive survey of the Claude Code extension ecosystem as of February 2026. Covers plugins, MCP servers, custom agents, skills, hooks, and community tooling. Goal: identify what is essential, what is trending, and what is specifically relevant to Athanor's architecture (homelab, multi-GPU inference, self-hosted everything).

This supplements the earlier ecosystem research from `2026-02-13-claude-code-ecosystem.md` and the power-user features doc from `2026-02-26-claude-code-power-user-features.md`. The landscape has changed significantly -- the plugin system launched in late 2025 and has exploded since.

---

## 1. Ecosystem Scale and Structure

### Numbers (Feb 2026)

| Metric | Count | Source |
|--------|-------|--------|
| Total plugins across all marketplaces | 9,000+ | aitoolanalysis.com |
| Official Anthropic plugin directory stars | 8,400 | github.com/anthropics/claude-plugins-official |
| Awesome-claude-code stars (hesreallyhim) | 2,600+ | github.com/hesreallyhim/awesome-claude-code |
| `@modelcontextprotocol/sdk` npm downloads | 20M+ | npmjs.com |
| Repositories indexed in quemsah adoption tracker | 6,073 | github.com/quemsah/awesome-claude-plugins |

### Marketplace Structure

Plugins are distributed through **marketplaces** -- git repositories with a standard structure. The key ones:

| Marketplace | Type | How to Access |
|-------------|------|---------------|
| `anthropics/claude-plugins-official` | Official, Anthropic-managed | `/plugin > Discover` or `/plugin install name@claude-plugin-directory` |
| `ClaudePluginHub` | Community | `/plugin marketplace add` |
| `Claude-Plugins.dev` | Community | Web + CLI |
| `ccplugins/awesome-claude-code-plugins` | Curated list (132 plugins in 13 categories) | github.com/ccplugins/awesome-claude-code-plugins |
| `buildwithclaude.com` | Community (400+ extensions) | Web |

Sources:
- https://github.com/anthropics/claude-plugins-official
- https://github.com/ccplugins/awesome-claude-code-plugins
- https://www.buildwithclaude.com/
- https://aitoolanalysis.com/claude-code-plugins/

### Plugin Anatomy

A plugin is a directory containing:

```
my-plugin/
  .claude-plugin/plugin.json    # Metadata (REQUIRED -- only file that goes here)
  commands/                     # Slash commands
  agents/                       # Subagent definitions
  skills/                       # SKILL.md files
  hooks/hooks.json              # Hook definitions
  .mcp.json                     # MCP server definitions
  .lsp.json                     # LSP server configurations
```

**Common mistake:** putting commands/, agents/, etc. inside `.claude-plugin/`. They must be at the plugin root level.

Installation: `/plugin install <name>@<marketplace>` or `/plugin > Discover`.

Development: Use `--plugin-dir` flag to test without installation.

Sources:
- https://code.claude.com/docs/en/plugins
- https://github.com/anthropics/claude-code/blob/main/plugins/README.md

---

## 2. Most-Installed / Most-Recommended Plugins

### By Install Count (from official + community sources)

| Plugin | Installs | What It Does |
|--------|----------|-------------|
| **Frontend Design** | ~96K | Stronger design judgment for UI generation -- typography, spacing, color |
| **Context7** | ~71K | Injects real-time, version-specific library documentation |
| **Ralph Loop** | ~57K | Autonomous multi-hour coding sessions with sequential task completion |
| **Code Review** | ~50K | Multiple specialized review agents in parallel across PR diffs |
| **Playwright** | ~28K | Browser automation via natural language |
| **Security Guidance** | ~25K | Scans edits for vulnerabilities (injection, XSS) before save |

Sources:
- https://www.firecrawl.dev/blog/best-claude-code-plugins
- https://composio.dev/blog/top-claude-code-plugins

### Consensus "Top 10" (Aggregated Across 5+ Lists)

Every recommendation list I found includes these. Sorted by how many lists they appear on:

1. **Context7** -- Live documentation injection. Appears on every single list. Solves the hallucination problem for library APIs.
2. **Playwright** -- Browser automation. Universal recommendation for web developers.
3. **Code Review** -- Parallel multi-agent diff review with confidence scoring. Fast first-pass before human review.
4. **Ralph Loop / Continuous Claude** -- Autonomous iterative development. Multiple implementations exist (ralph-claude-code, continuous-claude, Continuous-Claude-v3).
5. **Security Guidance** -- PreToolUse hook that blocks dangerous code patterns. Acts as automated safety net.
6. **Figma MCP** -- Reads real Figma design files (frames, components, layout) for design-to-code.
7. **Linear** -- Connects to Linear issue tracker. Pull tickets, update status, manage issues.
8. **Chrome DevTools MCP** -- Full debugging access to Chrome DevTools (network, console, performance).
9. **Firecrawl** -- Web scraping that handles JS rendering, anti-bot, proxy rotation.
10. **LSP Plugins** (TypeScript/Rust) -- Real type checking via Language Server Protocol.

Sources:
- https://www.firecrawl.dev/blog/best-claude-code-plugins
- https://composio.dev/blog/top-claude-code-plugins
- https://github.com/hesreallyhim/awesome-claude-code
- https://github.com/ccplugins/awesome-claude-code-plugins

---

## 3. Plugin Deep Dives: Power-User Favorites

### The Deep Trilogy (Pierce Lamb)

Three plugins that form an idea-to-implementation pipeline:

| Plugin | Command | What It Does |
|--------|---------|-------------|
| **Deep Project** | `/deep-project` | Decomposes vague ideas into components |
| **Deep Plan** | `/deep-plan` | Transforms components into implementation plans via research, interviews, multi-LLM review |
| **Deep Implement** | `/deep-implement` | Implements code from /deep-plan sections with TDD and code review |

Workflow: Research --> Interview (5-10 questions) --> External LLM Review --> TDD Plan --> Section Splitting --> Implementation.

Source: https://pierce-lamb.medium.com/the-deep-trilogy-claude-code-plugins-for-writing-good-software-fast-33b76f2a022d

### SuperClaude Framework

A meta-programming configuration framework with 30 commands across 4 categories:

- **Development:** `/sc:build`, `/sc:code`, `/sc:debug`
- **Analysis:** `/sc:analyze`, `/sc:optimize`, `/sc:refactor`, `/sc:review`, `/sc:audit`
- **Operations:** `/sc:deploy`, `/sc:test`, `/sc:monitor`, `/sc:backup`, `/sc:scale`, `/sc:migrate`
- **Research:** `/sc:research` (enhanced with Tavily MCP)

Optional MCP servers for enhanced performance: Serena (2-3x faster code understanding), Sequential Thinking (30-50% fewer tokens), Tavily (web search), Context7 (docs).

Currently in BETA. Heavy -- may conflict with existing configurations.

Source: https://github.com/SuperClaude-Org/SuperClaude_Framework

### TDD-Guard

Hook-based plugin that enforces Test-Driven Development by intercepting file modifications:

- Blocks implementation without failing tests
- Blocks over-implementation beyond test requirements
- Blocks adding multiple tests simultaneously
- Supports: JS/TS (Jest, Vitest, Storybook), Python (pytest), PHP (PHPUnit), Go, Rust

Install via `/hooks` command. Available on Homebrew (`brew install tdd-guard`). 1,700 stars.

Source: https://github.com/nizos/tdd-guard

### Superpowers (obra)

Structured lifecycle skills for the full SDLC: brainstorming, TDD, debugging, code review, collaboration. 20+ battle-tested skills.

Source: https://github.com/obra/superpowers

### Claude-Mem

Persistent long-term memory across sessions:

- Captures observations (tool usage, file changes, decisions)
- Compresses via AI summarization using Claude Agent SDK
- Stores in local SQLite database
- Progressive disclosure strategy (saves ~2,250 tokens/session vs manual context)
- Web interface at localhost:37777
- Beta: "Endless Mode" (biomimetic memory architecture for extended sessions)

Install: `/plugin marketplace add thedotmack/claude-mem` then `/plugin install claude-mem`.

Source: https://github.com/thedotmack/claude-mem

### Trail of Bits Security Skills

12+ security-focused skills for code auditing from the actual security research firm:

- **Audit Context Building**: Line-by-line analysis with First Principles, 5 Whys, 5 Hows
- **Specification-to-Code Compliance**: Evidence-based alignment analysis (blockchain focus)
- **Fix Review**: Deep context review for complex fixes
- **Culture Index**: Organization security culture assessment

Source: https://github.com/trailofbits/skills

### Compound Engineering Plugin (EveryInc)

Multi-step task composition where each cycle compounds: plans inform future plans, reviews catch more issues, patterns get documented.

Philosophy: "Each unit of engineering work should make subsequent units easier, not harder."

Source: https://github.com/EveryInc/compound-engineering-plugin

### Context Engineering Kit (NeoLab)

Advanced context engineering techniques with minimal token footprint:
- Structured reasoning templates (Zero-shot CoT, Tree of Thoughts, Problem Decomposition, Self-Critique)
- Multi-agent orchestration for context management
- Context isolation to prevent context rot

**Warning:** Core FPF specification is ~600k tokens. Loads into a Sonnet subagent to avoid blowing main context.

Source: https://github.com/NeoLabHQ/context-engineering-kit

---

## 4. MCP Servers: Beyond the Basics

### Essential MCP Servers (Consensus)

These appear on every "must-have" list:

| MCP Server | Package | Purpose |
|-----------|---------|---------|
| Sequential Thinking | `@modelcontextprotocol/server-sequential-thinking` | Structured multi-step reasoning |
| Context7 | `@upstash/context7-mcp` | Live library documentation |
| Playwright | `@anthropic/mcp-server-playwright` | Browser automation |
| Filesystem | `@modelcontextprotocol/server-filesystem` | Advanced file operations |
| GitHub | `@modelcontextprotocol/server-github` | GitHub API access |

Sources:
- https://apidog.com/blog/top-10-mcp-servers-for-claude-code/
- https://mcpcat.io/guides/best-mcp-servers-for-claude-code/

### Infrastructure / Homelab MCP Servers

Directly relevant to Athanor:

| MCP Server | What It Does | Relevance |
|-----------|-------------|-----------|
| **Grafana MCP** (`mcp-grafana`) | Search dashboards, run PromQL/LogQL, manage OnCall, query Tempo | Already configured. Official Grafana Labs project. |
| **Neo4j MCP** (`mcp-neo4j`) | Knowledge graph operations via MCP | We have Neo4j with 3,095 nodes. Could replace manual scripts. |
| **mem0-mcp-selfhosted** | Persistent memory backed by Qdrant + Neo4j + Ollama | Uses our exact stack. 11 MCP tools for memory management. |
| **Octopus MCP** | Rust-based knowledge base with Qdrant + Neo4j + Redis | Another option using our exact infrastructure. |
| **Docker MCP** | Container lifecycle, logs, inspection | Could manage our 15+ containers across 3 nodes. |
| **PostgreSQL MCP** | Natural language database queries | If we add PostgreSQL. |

Sources:
- https://github.com/grafana/mcp-grafana
- https://github.com/elvismdev/mem0-mcp-selfhosted
- https://github.com/neo4j-contrib/mcp-neo4j

### mem0-mcp-selfhosted: Athanor-Relevant Deep Dive

This project runs against the exact same stack we already have:

- **Qdrant** for vector storage (we have it at Node 1:6333)
- **Neo4j** for knowledge graph (we have it at VAULT)
- **Ollama** for local embeddings (we could use our vLLM instead)
- **Claude Code** as the main LLM

11 MCP tools exposed: memory CRUD, search, entity extraction, graph traversal.

**Key question for Athanor:** Do we need this, or does our existing `mcp__athanor-agents__*` bridge already cover memory? Our agent framework already has Qdrant integration with 7 collections and Neo4j graph. Adding mem0-mcp would be a parallel memory system unless we integrate them. Likely **not worth adding** -- we have better custom infrastructure already.

Source: https://github.com/elvismdev/mem0-mcp-selfhosted

---

## 5. LSP Plugins (Code Intelligence)

LSP support was added in Claude Code v2.0.74 (December 2025). This is the highest-impact "silent" improvement.

### What It Gives Claude

- **Go-to-definition** in 50ms vs 45s text search
- **Find references** across entire codebase
- **Real-time diagnostics** after every file edit
- **Type error detection** before commit

### Available Languages

TypeScript, Python, Go, Rust, Java, C/C++, C#, PHP, Kotlin, Ruby, HTML/CSS, Bash/Shell, Clojure, Dart/Flutter, Elixir, Gleam, Lua, Nix, OCaml, Swift, Terraform, YAML, Zig.

### Key Implementations

| Plugin | Source | Notes |
|--------|--------|-------|
| Official TypeScript LSP | `anthropics/claude-plugins-official` | Requires `typescript-language-server` binary |
| Official Python LSP | `anthropics/claude-plugins-official` | Uses `pylsp` |
| boostvolt/claude-code-lsps | Community | 22+ languages in one marketplace |
| Piebald-AI/claude-code-lsps | Community | Alternative marketplace |

### Performance Claim

"With LSP enabled, Claude Code navigates codebases in 50ms instead of 45 seconds using traditional text search."

**Caveat:** This claim needs verification. The 50ms is for definition lookup; full-project analysis still takes time. But the diagnostic feedback loop (edit -> instant type errors) is genuinely transformative for TypeScript and Rust work.

### Athanor Relevance

We work primarily in:
- **TypeScript** (Command Center, EoBQ) -- **high value**
- **Python** (agents, scripts) -- **high value**
- **YAML** (Ansible) -- moderate value
- **Rust** -- not currently, but would be valuable if we start

Sources:
- https://github.com/boostvolt/claude-code-lsps
- https://github.com/Piebald-AI/claude-code-lsps
- https://dev.to/rajeshroyal/lsp-ide-level-code-intelligence-for-claude-4kp5

---

## 6. Custom Agents: Interesting Configurations

### Community Patterns

From analyzing multiple repositories of shared agent configurations:

| Agent Pattern | Description | Source |
|--------------|-------------|--------|
| **Read-Only Reviewer** | Haiku model, `tools: ["Read", "Grep", "Glob"]` only. Fast, cheap code review. | claude-world.com |
| **Deploy Reviewer** | Reviews infrastructure changes with `permissionMode: plan`. Cannot execute. | iannuttall/claude-agents |
| **QA Tester** | "Meticulous QA professional" persona. Thinks about edge cases, error states. | code.claude.com/docs |
| **Git Expert** | Specialized for complex rebasing, merging, history analysis. | ccplugins list |
| **Doc Writer** | Updates documentation after code changes. `memory: project` for accumulated style knowledge. | hesreallyhim/awesome-claude-code |
| **Security Auditor** | Sonnet model for capability. Scans for OWASP Top 10, dependency vulnerabilities. | trailofbits/skills |

### Key Agent Configuration Fields (New/Underused)

| Field | Value | Effect |
|-------|-------|--------|
| `isolation: worktree` | Runs in temporary git worktree. Auto-cleaned if no changes. | Safe for risky refactoring. |
| `memory: user` | Persistent memory at `~/.claude/agent-memory/<name>/`. Accumulates knowledge. | Agent gets smarter over sessions. |
| `background: true` | Always runs as background task. | Non-blocking for async work. |
| `skills: [list]` | Skills preloaded at startup. | Agent has domain knowledge immediately. |
| `mcpServers: [list]` | Specific MCP servers available. | Limit scope per agent. |
| `hooks` | Lifecycle hooks scoped to agent. | Agent-specific automation. |

Source: https://code.claude.com/docs/en/sub-agents

---

## 7. Skills: Reusable Community Collections

### Where to Find Skills

| Source | Scale | Quality |
|--------|-------|---------|
| `anthropics/skills` | Official Anthropic collection | Curated, highest quality |
| `travisvn/awesome-claude-skills` | Community curated list | Variable, inspect before use |
| `skillsmp.com` | Agent Skills Marketplace (Claude, Codex, ChatGPT) | Cross-platform |
| `skillshare` (runkids) | CLI tool syncing skills across Claude Code, OpenClaw, OpenCode, Codex | Tool, not a source |

### Notable Skill Collections

| Collection | Skills | Focus |
|-----------|--------|-------|
| **Superpowers** (obra) | 20+ | Full SDLC: TDD, debugging, brainstorm, review |
| **Fullstack Dev Skills** | 65 specialized + 9 workflow commands | Full-stack development |
| **cc-devops-skills** | DevOps validations, generators, shell scripts | IaC, cloud platforms |
| **Trail of Bits Security** | 12+ | Vulnerability detection, audit workflows |
| **Context Engineering Kit** | Reasoning templates | CoT, Tree of Thoughts, Self-Critique |
| **RIPER Workflow** | 5-phase | Research, Innovate, Plan, Execute, Review |

### Skillshare: Cross-Tool Sync

If you use multiple AI CLI tools (we use Claude Code, Gemini CLI, Kimi CLI, OpenCode, Aider), `skillshare` by runkids syncs skills across all of them from a single source:

- Single source of truth in `~/.config/skillshare/config.yaml`
- Symlinks to each tool's skill directory
- Built-in security audit (scans for prompt injection, data exfiltration)
- Web UI at localhost:19420
- Privacy-first: no central registry, no telemetry

Source: https://github.com/runkids/skillshare

### Key Skill Features (Often Overlooked)

- **`context: fork`**: Run skill in isolated subagent context. Preserves main conversation.
- **`disable-model-invocation: true`**: Only user can invoke. Critical for dangerous operations.
- **Dynamic context injection**: `` !`command` `` syntax runs shell commands before skill content is sent.
- **`once: true`**: Run only once per session.
- **Supporting files**: Skills can include templates, examples, scripts alongside SKILL.md.

---

## 8. Hooks: Automation Patterns

### Most-Adopted Hook Patterns

| Pattern | Event | What It Does |
|--------|-------|-------------|
| **Auto-format** | PostToolUse (Edit/Write) | Run Prettier/Black/gofmt after every file edit |
| **Path protection** | PreToolUse (Edit/Write) | Block writes to protected files/directories |
| **Auto-lint** | PostToolUse (Edit/Write) | Run eslint/ruff/clippy after edits |
| **Desktop notifications** | Notification | Alert on permission requests, idle |
| **TDD enforcement** | PreToolUse (Write/Edit) | Block implementation without failing tests (tdd-guard) |
| **Context injection** | UserPromptSubmit | Inject dynamic state (git branch, running containers, GPU status) |
| **State preservation** | PreCompact | Save session state before context compaction |
| **Auto-commit** | Stop | Commit changes when Claude finishes |
| **LLM quality gate** | Stop | Use `prompt` type hook to verify task completeness |
| **GitButler integration** | PreToolUse + PostToolUse + Stop | `but claude pre-tool`, `but claude post-tool`, `but claude stop` |
| **Session init** | SessionStart | Inject dynamic reminders ("Use Bun, not npm. Current sprint: X") |

### Hook Handler Types (Often Missed)

Most people only use `command` type hooks. Two other types exist:

| Type | Description | Use Case |
|------|-------------|----------|
| `command` | Shell command, receives JSON on stdin | Most hooks |
| `prompt` | Single-turn LLM evaluation, returns yes/no | Quality gates, policy checks |
| `agent` | Subagent with tools (Read, Grep, Glob) | Complex analysis before decision |

**`prompt` and `agent` hooks are underused.** A Stop-event `prompt` hook that asks "Did Claude complete all requested tasks?" before ending would be valuable.

Sources:
- https://code.claude.com/docs/en/hooks-guide
- https://blog.gitbutler.com/automate-your-ai-workflows-with-claude-code-hooks/
- https://github.com/disler/claude-code-hooks-mastery

---

## 9. Orchestrators and Autonomous Patterns

### The Ralph Loop Ecosystem

"Ralph Wiggum" is the dominant pattern for autonomous Claude Code sessions. Multiple implementations:

| Tool | Stars | Approach |
|------|-------|----------|
| **Continuous-Claude-v3** (parcadei) | 2,200+ | Hooks maintain state via ledgers and handoffs. MCP execution without context pollution. |
| **continuous-claude** (AnandChowdhary) | - | Ralph loop with PRs: autonomous loop creating PRs, waiting for checks, merging. Relay race model. |
| **ralph-claude-code** (frankbria) | - | Intelligent exit detection and safety guardrails. |
| **awesome-ralph** | - | Curated list of Ralph technique resources. |
| **ralph-wiggum-bdd** | - | BDD-focused standalone Bash script. |

### Multi-Agent Orchestrators

| Tool | Approach | Complexity |
|------|----------|------------|
| **Claude Squad** | Terminal app, multiple agents in separate workspaces | Moderate (tmux) |
| **Claude Swarm** | Launch Claude connected to swarm of agents | High |
| **Auto-Claude** | Full SDLC with kanban-style UI | High |
| **Claude Task Master** | Task management for AI-driven dev | Moderate |
| **TSK** | Rust CLI delegating tasks to Docker-sandboxed agents | High |
| **Happy Coder** | Spawn and control multiple Claude instances from phone/desktop | Moderate |

### Recommendation for Athanor

We already have a sophisticated multi-agent architecture (9 local agents on Node 1:9000, LangGraph, Work Planner). The Ralph loop and external orchestrators would **conflict** with our existing system. Our architecture is more mature than most of these tools. Skip.

---

## 10. Usage Monitoring and Tooling

### Usage Dashboards

| Tool | Type | Features |
|------|------|----------|
| **ccflare** | Web UI | Comprehensive metrics, cost dashboard |
| **better-ccflare** | Web UI | Enhanced fork with performance improvements |
| **CC Usage** (`ccusage`) | CLI | Cost analysis, usage patterns |
| **Claudex** | Web | Conversation history browser with full-text search |
| **viberank** | Web | Community leaderboard |

### Status Lines

| Tool | Language | Features |
|------|----------|----------|
| **CCometixLine** | Rust | Git integration, TUI configuration |
| **ccstatusline** | Node.js | Customizable, model info, git branch, token usage |
| **claude-code-statusline** | - | 4-line, themes, cost tracking |
| **claude-powerline** | - | Vim-style powerline, real-time usage |
| **claudia-statusline** | Rust | Persistent stats, progress bars |

### Config Management

| Tool | What |
|------|------|
| **ClaudeCTX** | Switch entire Claude Code configuration with single command |
| **claude-rules-doctor** | CLI detecting dead/unused `.claude/rules/` files |
| **Rulesync** | Auto-generate configs for multiple AI agents |

---

## 11. Context Window Economics

### The Critical Constraint

**Everything competes for a 200k token context window:**
- System prompt
- Tool definitions (MCP servers)
- Memory files (CLAUDE.md, MEMORY.md, rules)
- Skills descriptions
- Conversation history
- File contents

### Key Numbers

| Factor | Impact |
|--------|--------|
| File loading overhead | ~1.7x raw token count (70% overhead from line number formatting) |
| Performance degradation at 1M context | 17-point MRCR drop (93% to 76%) on Opus 4.6 |
| Average developer cost/day | $6 (90th percentile: $12) |
| Recommended MCP server limit | Under 10 enabled, under 80 total active tools |
| MCP Tool Search savings | Up to 95% context reduction via lazy loading |

### Guidelines

1. **Under 10 MCP servers.** Tool Search helps, but each server still has baseline overhead.
2. **CLI tools over MCP servers when possible.** `gh`, `docker`, `ansible` via Bash consume no persistent context.
3. **Path-scoped rules.** Only load when relevant.
4. **Skills over CLAUDE.md.** Skills load on demand; CLAUDE.md loads always.
5. **`context: fork` on research skills.** Preserve main context window.

Sources:
- https://code.claude.com/docs/en/costs
- https://github.com/anthropics/claude-code/issues/20223
- https://deepwiki.com/affaan-m/everything-claude-code/12.2-context-window-optimization

---

## 12. Athanor-Specific Analysis

### What We Already Have vs. Ecosystem

| Ecosystem Component | Athanor Status | Gap |
|---------------------|---------------|-----|
| MCP servers (5 configured) | sequential-thinking, context7, filesystem, grafana, athanor-agents | Triple Context7 duplication (wastes context) |
| Hooks (7 across 6 events) | PreToolUse, PostToolUse, UserPromptSubmit, Notification, Stop, PreCompact, SessionStart | Missing: SessionEnd, PostToolUseFailure, `prompt`/`agent` type hooks |
| Rules (9 path-scoped) | agents, ansible, dashboard, docker, docs, eoq, knowledge, scripts, vllm | Good coverage. Some could use `paths:` frontmatter. |
| Skills (12) | architecture-decision, athanor-conventions, deploy-agent, deploy-docker-service, gpu-placement, local-coding, network-diagnostics, node-ssh, state-update, troubleshoot, vllm-deploy, comfyui-deploy | Missing: `context: fork` on research skills, `disable-model-invocation` on deploy skills |
| Custom agents (4) | coder, doc-writer, infra-auditor, researcher | Missing: `memory:` field, `isolation: worktree`, `background: true` |
| Plugins (0 installed) | None | Untapped. LSP plugins for TypeScript/Python would be highest impact. |

### Recommended Additions (Priority Order)

#### 1. LSP Plugins for TypeScript + Python (HIGH -- Install Now)

Our PostToolUse typecheck hook is a manual approximation of what LSP does natively. With LSP:
- Claude gets instant type errors after every edit (no hook needed)
- Go-to-definition in 50ms vs grep/ripgrep
- Find references across entire codebase
- Works for both our TypeScript (dashboard, EoBQ) and Python (agents, scripts) codebases

Install from official marketplace or `boostvolt/claude-code-lsps`.

```bash
# From Claude Code:
/plugin marketplace add boostvolt/claude-code-lsps
/plugin install typescript-lsp
/plugin install python-lsp
```

Prerequisite: `typescript-language-server` and `pylsp` binaries must be available.

#### 2. Deduplicate Context7 (HIGH -- Fix Now)

We have three Context7 instances (`mcp__context7__*`, `mcp__plugin_context7_context7__*`, `mcp__claude_ai_Context7__*`). This triples the context overhead. Keep one, remove two.

#### 3. Code Review Plugin (MEDIUM)

Parallel multi-agent review with confidence scoring. Would complement our existing `coder` agent. 50K installs suggests it is battle-tested.

#### 4. TDD-Guard (MEDIUM)

Hook-based TDD enforcement. Supports our Python (pytest) and TypeScript (Jest/Vitest) codebases. Prevents implementation-before-test. More robust than a custom skill for this purpose.

Source: https://github.com/nizos/tdd-guard

#### 5. Subagent Memory Fields (MEDIUM -- Quick Win)

Add `memory: user` to our existing custom agents so they accumulate knowledge across sessions:

```yaml
# .claude/agents/infra-auditor.md
---
memory: user
---
```

#### 6. Skillshare for Cross-Tool Sync (LOW)

We use 7+ AI CLI tools (Claude Code, Gemini CLI, Kimi CLI, OpenCode, Aider, Codex CLI, CCR). `skillshare` would let us maintain one set of skills and sync across all. Low priority because Claude Code is our primary tool.

### What NOT to Add

| Tool | Why Skip |
|------|----------|
| **Ralph Loop / Continuous Claude** | We have our own autonomous loop (ADR-021, Work Planner, proactive task engine). These would conflict. |
| **SuperClaude** | Heavy framework (30 commands) that would conflict with our existing CLAUDE.md, skills, and conventions. We already have equivalent coverage. |
| **Claude-Mem** | We have our own memory system (Qdrant 7 collections + Neo4j graph + MEMORY.md). Claude-Mem is SQLite-based, less capable. |
| **mem0-mcp-selfhosted** | Uses our exact stack (Qdrant + Neo4j + Ollama) but would create a parallel memory system alongside our existing agent framework. |
| **Context Engineering Kit** | 600k token core specification. Way too heavy. Our CLAUDE.md + skills approach is more token-efficient. |
| **External orchestrators** (Claude Squad, Swarm, etc.) | Our 9-agent LangGraph architecture is more mature. |
| **Desktop Commander** | Listed in our permissions but native Bash tool + our SSH scripts cover the same ground. Adds context overhead for minimal gain. |
| **Figma MCP** | No Figma workflow. |
| **Linear** | No Linear. We use GitHub issues. |
| **Frontend Design** | 96K installs but not relevant -- we have our own UI conventions and design system for EoBQ/dashboard. |

---

## 13. Curated Resource Index

### Essential References

| Resource | URL | What |
|----------|-----|------|
| Official Claude Code Docs | https://code.claude.com/docs/en | Canonical reference |
| Official Plugin Directory | https://github.com/anthropics/claude-plugins-official | Anthropic-curated plugins |
| Claude Code repo (plugins) | https://github.com/anthropics/claude-code/tree/main/plugins | Plugin system source |
| Awesome Claude Code (hesreallyhim) | https://github.com/hesreallyhim/awesome-claude-code | Best curated list (skills, hooks, agents, orchestrators, tools) |
| Awesome Claude Code Plugins (ccplugins) | https://github.com/ccplugins/awesome-claude-code-plugins | 132 plugins categorized |
| Awesome Claude Plugins (quemsah) | https://github.com/quemsah/awesome-claude-plugins | Adoption metrics for 6,073 repos |
| Awesome Claude Skills | https://github.com/travisvn/awesome-claude-skills | Skills curation |
| Anthropic Skills | https://github.com/anthropics/skills | Official skill collection |
| MCP Servers (official) | https://github.com/modelcontextprotocol/servers | Official MCP server implementations |
| MCP TypeScript SDK | https://github.com/modelcontextprotocol/typescript-sdk | Build custom MCP servers |
| Hooks Mastery | https://github.com/disler/claude-code-hooks-mastery | Comprehensive hook patterns |
| Claude Code LSPs | https://github.com/boostvolt/claude-code-lsps | 22+ language LSP plugins |
| Trail of Bits Skills | https://github.com/trailofbits/skills | Security audit skills |
| TDD-Guard | https://github.com/nizos/tdd-guard | TDD enforcement hook |
| Skillshare | https://github.com/runkids/skillshare | Cross-tool skill sync |
| Deep Trilogy | https://github.com/piercelamb/deep-plan | Research-plan-implement pipeline |

### Blog Posts Worth Reading

| Title | URL |
|-------|-----|
| The Deep Trilogy (Pierce Lamb) | https://pierce-lamb.medium.com/the-deep-trilogy-claude-code-plugins-for-writing-good-software-fast-33b76f2a022d |
| Claude Code Hooks (GitButler) | https://blog.gitbutler.com/automate-your-ai-workflows-with-claude-code-hooks/ |
| Plugin Starter Stack for Web Devs | https://blog.devgenius.io/the-claude-code-plugin-starter-stack-for-web-developers-f2d85b0335fa |
| 9,000+ Extensions Analysis | https://aitoolanalysis.com/claude-code-plugins/ |
| Configure Agent Team (Haberlah) | https://medium.com/@haberlah/configure-claude-code-to-power-your-agent-team-90c8d3bca392 |

---

## 14. Plugin Development Tips (For Building Our Own)

If we want to package Athanor's skills/hooks/agents as a plugin:

### Structure

```
athanor-plugin/
  .claude-plugin/
    plugin.json         # Only metadata goes here
  commands/
    build.md
    deploy.md
    health.md
    morning.md
    research.md
    status.md
  agents/
    coder.md
    doc-writer.md
    infra-auditor.md
    researcher.md
  skills/
    deploy-agent/SKILL.md
    gpu-placement/SKILL.md
    network-diagnostics/SKILL.md
    node-ssh/SKILL.md
    troubleshoot/SKILL.md
    vllm-deploy/SKILL.md
  hooks/
    hooks.json          # All hook definitions
  .mcp.json             # athanor-agents MCP server config
```

### plugin.json

```json
{
  "name": "athanor",
  "version": "1.0.0",
  "description": "Athanor sovereign AI cluster management plugin",
  "author": "Shaun",
  "homepage": "https://github.com/Dirty13itch/athanor"
}
```

### Testing

```bash
claude --plugin-dir ./athanor-plugin
```

### Distribution

Can self-host as a marketplace (just a GitHub repo with standard structure) or submit to Anthropic's official directory via https://clau.de/plugin-directory-submission.

Sources:
- https://code.claude.com/docs/en/plugins
- https://www.datacamp.com/tutorial/how-to-build-claude-code-plugins
- https://www.morphllm.com/claude-code-plugins

---

## Open Questions

1. **LSP overhead**: How much context do LSP tool definitions consume? Need to measure before and after.
2. **Plugin conflicts**: Can plugins override project-level hooks/skills? What happens with name collisions?
3. **Neo4j MCP**: Would the official Neo4j MCP server be useful alongside our existing agent framework's Neo4j integration, or is it redundant?
4. **Custom marketplace**: Is it worth creating a private Athanor marketplace for our plugins, or just keep them in `.claude/`?

---

Last updated: 2026-02-26
