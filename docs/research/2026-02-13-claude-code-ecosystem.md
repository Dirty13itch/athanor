# Claude Code Ecosystem Research for Athanor

## What This Document Covers

Everything available to supercharge Claude Code on Shaun's Windows 11 DEV machine for building and managing Athanor. MCP servers, skills, orchestrators, companion tools, dashboards, and extensions — evaluated against Athanor's principles (one-person maintainable, practical over pure, open scope).

---

## 1. MCP Servers — Recommended for Athanor

### Tier 1: Install Immediately (Essential)

| MCP Server | What It Does | Why We Need It |
|-----------|-------------|---------------|
| **GitHub MCP** | Full GitHub API — repos, PRs, issues, commits, CI/CD | Athanor lives in a repo. Claude Code needs to manage it directly. |
| **Sequential Thinking** | Structured multi-step reasoning | Complex architecture decisions, research synthesis |
| **Context7** | Live library/framework documentation | Always up-to-date docs for whatever stack we choose |
| **Brave Search** | Web search from within Claude Code | Research without leaving the session |
| **Playwright** | Browser automation via accessibility snapshots | Web scraping, testing dashboards, automated browsing |
| **Filesystem** | Advanced file operations with permission controls | Project-wide file management beyond basic bash |
| **Memory MCP** | Knowledge graph-based persistent memory | Claude Code remembering context across sessions |

### Tier 2: Install When Needed (Infrastructure)

| MCP Server | What It Does | When To Add |
|-----------|-------------|-------------|
| **Homelab MCP** (bjeans) | Docker/Podman, Ollama, UniFi, Ansible inventory monitoring | When Athanor infrastructure is running — directly supports UniFi + Docker on Unraid |
| **Unraid MCP** (jmagar) | Unraid-specific container management across hosts | When we start managing Unraid containers via Claude Code |
| **Kubernetes MCP** | Full k8s management — pods, deployments, services, logs | Only if we choose Kubernetes (not assumed) |
| **Docker MCP** | Container lifecycle, logs, inspection | When we deploy containerized services |
| **PostgreSQL MCP** | Natural language database queries | When we have databases to manage |
| **SQLite MCP** | Local SQLite management | For local config/state databases |
| **Home Assistant MCP** | HA entity control, automation management | When we integrate Athanor with Home Assistant |
| **Grafana MCP** | Query dashboards and metrics | When observability stack is running |

### Tier 3: Nice To Have (Productivity)

| MCP Server | What It Does | Notes |
|-----------|-------------|-------|
| **Fetch MCP** | Web content fetching and conversion | Complement to Brave Search for full page reads |
| **Git MCP** | Advanced git operations beyond bash | Useful for complex branching/merging workflows |
| **Google Drive MCP** | Access Google Drive files | If Shaun uses GDrive for business docs |

---

## 2. Desktop Commander MCP

**This deserves its own section.** Desktop Commander (by wonderwhy-er) is one of the most powerful MCP servers available and directly relevant to Athanor:

- Full terminal control with persistent sessions (SSH into nodes!)
- Interactive process management (keep SSH sessions alive, interact with running services)
- File system search and diff-based editing
- Execute code in memory (Python, Node.js) without saving files
- PDF reading and creation
- Excel file support
- Remote MCP support (use from any AI client)

**Install:** `npx -y @wonderwhy-er/desktop-commander`

This effectively turns Claude Desktop into a system administration tool. For Athanor, it means Claude Code could SSH into Unraid, manage Docker containers, inspect logs, all through persistent terminal sessions.

**Key difference from Claude Code's native bash:** Desktop Commander maintains persistent shell sessions. Claude Code's bash tool creates a new shell for each command. For infrastructure work (SSH tunnels, monitoring, interactive processes), Desktop Commander is significantly more capable.

---

## 3. Multi-Agent Orchestration

Claude Code now has **native Agent Teams** (experimental, as of v2.1.19+). This is relevant for Athanor because complex tasks (like auditing all nodes simultaneously, or building multiple project components in parallel) benefit from multi-agent coordination.

### Native Agent Teams
- Built into Claude Code, enable via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- Lead agent coordinates, spawns teammates, synthesizes results
- Each teammate is a full independent Claude Code session
- Teammates can message each other directly
- Delegate mode restricts lead to coordination only
- Best for: parallel research, multi-component builds, debugging with competing hypotheses

### Third-Party Orchestrators (if native isn't enough)

| Tool | What It Does | Complexity |
|------|-------------|------------|
| **Claude Squad** | Terminal app managing multiple CC agents in separate workspaces | Moderate — tmux-based |
| **Oh My Claude Code (OMC)** | 32 agents, 40 skills, zero config — "oh-my-zsh for Claude Code" | Low — plug and play |
| **Gas Town** | Mayor/agent hierarchy, agent spawning via CLI | High — solo dev focused |
| **Multiclaude** | Multi-agent with auto-merge CI, supervisor model | High — team focused |
| **Claude Flow (Ruflo)** | Full enterprise orchestration, 60+ agents, swarm topologies | Overkill for now |

**Recommendation:** Start with native Agent Teams. It's built-in, maintained by Anthropic, and avoids third-party dependency. Only look at external orchestrators if native teams hit real limitations.

---

## 4. Skills & Slash Command Collections

### Pre-Built Skill Collections

| Collection | What It Includes | Source |
|-----------|-----------------|--------|
| **Claude Command Suite** | 119+ slash commands for code review, security, architecture | github.com/qdhenry/Claude-Command-Suite |
| **obra/superpowers** | 20+ battle-tested skills: TDD, debugging, collaboration | github.com/obra/superpowers |
| **cc-devops-skills** | Detailed DevOps skills for IaC, cloud platforms, deployment | github.com/akin-ozer/cc-devops-skills |
| **agent-toolkit** | 237+ curated skills for AI coding agents | github.com search |
| **claude-starter** | 40 auto-activating skills across 8 domains | Production-ready template |

### Individual Skills Worth Having

| Skill | What It Does |
|-------|-------------|
| **systematic-debugging** | Structured debugging methodology before proposing fixes |
| **test-driven-development** | TDD workflow for any feature or bugfix |
| **software-architecture** | Clean Architecture, SOLID, comprehensive design patterns |
| **webapp-testing** | Playwright-based testing for web applications |
| **blader** | Autonomous skill extraction — Claude Code gets smarter as it works |
| **file-organizer** | Intelligent file/folder organization |
| **mcp-builder** | Guide for creating custom MCP servers (we'll need this) |

---

## 5. Usage Monitoring & Dashboards

| Tool | What It Does | Platform |
|------|-------------|----------|
| **ccflare** | Beautiful web UI dashboard for Claude Code usage, costs, tokens | Web |
| **CC Usage (ccusage)** | CLI tool for analyzing logs with cost/token dashboard | Terminal |
| **Claude Code Usage Monitor** | Real-time terminal monitoring for token usage | Terminal |

**Recommendation:** Install ccflare for the web dashboard. You're going to be running a lot of Claude Code on this project — knowing your usage patterns and costs matters.

---

## 6. IDE Integrations

| Tool | What It Does |
|------|-------------|
| **Claude Code Chat (VS Code)** | Chat interface for Claude Code inside VS Code with inline suggestions |
| **Claude MCP Browser Extension** | Enable MCP in claude.ai web interface |

Since Shaun runs Claude Code from terminal / Claude Desktop, these are optional. But the browser extension could be useful for adding MCP capabilities to the claude.ai chat interface.

---

## 7. Key Resources & References

| Resource | URL |
|----------|-----|
| awesome-claude-code (main list) | github.com/hesreallyhim/awesome-claude-code |
| awesome-claude-skills | github.com/ComposioHQ/awesome-claude-skills |
| awesome-mcp-servers | github.com/punkpeye/awesome-mcp-servers |
| Official Claude Code Docs | code.claude.com/docs |
| MCP Protocol Spec | modelcontextprotocol.io |
| MCP Tool Search (lazy loading) | Reduces context usage by 95% — enable for many MCPs |
| Homelab MCP (UniFi + Docker) | github.com/bjeans/homelab-mcp |
| Unraid MCP | github.com/jmagar/unraid |
| Desktop Commander | github.com/wonderwhy-er/DesktopCommanderMCP |

---

## 8. Recommended Installation Plan

### Phase 0: Right Now (Before Hardware Audit)

```
# User-scoped MCPs (available in all projects)
claude mcp add github -s user -- npx -y @modelcontextprotocol/server-github
claude mcp add brave-search -s user -- npx -y @modelcontextprotocol/server-brave-search
claude mcp add memory -s user -- npx -y @modelcontextprotocol/server-memory
claude mcp add desktop-commander -s user -- npx -y @wonderwhy-er/desktop-commander

# Environment variables needed:
# GITHUB_PERSONAL_ACCESS_TOKEN (for GitHub MCP)
# BRAVE_API_KEY (for Brave Search — free tier available)
```

### Project-scoped MCPs (in .mcp.json)
```json
{
  "mcpServers": {
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    },
    "playwright": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-playwright"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:\\Users\\Shaun"]
    }
  }
}
```

### Phase 1: After Hardware Audit
- Add Homelab MCP (for UniFi + Docker monitoring)
- Add Unraid MCP (for Unraid container management)
- Possibly Kubernetes MCP (depends on architecture decisions)

### Phase 2: After Services Are Running
- PostgreSQL / SQLite MCP (when databases exist)
- Grafana MCP (when monitoring is live)
- Home Assistant MCP (when HA integration begins)
- Custom MCPs we build ourselves

### Enable Agent Teams
```
# In settings.json or environment
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

### Install Usage Monitor
```
npm install -g ccusage
# Or set up ccflare for web dashboard
```

---

## 9. Important Notes

### MCP Tool Search
Claude Code now supports **MCP Tool Search** which enables lazy loading. This means you can install many MCP servers without bloating context — tools only load when relevant to the current task. This is a game changer for having 10+ MCPs installed simultaneously.

### Windows-Specific Considerations
- All `npx`-based MCPs work on Windows with Node.js installed
- Desktop Commander works on Windows
- SSH from Claude Code requires OpenSSH client (built into Windows 10/11)
- Some Python-based MCPs may need `python` or `py` command adjustment

### Security
- MCP servers can execute arbitrary code. Only install from trusted sources.
- GitHub PAT should have minimal required scopes
- Desktop Commander has command blacklisting for safety
- Filesystem MCP requires explicit directory permissions
