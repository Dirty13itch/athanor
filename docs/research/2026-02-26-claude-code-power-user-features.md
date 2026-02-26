# Claude Code Power User Features: Complete Reference

## Context

Comprehensive research into Claude Code's feature set, configuration options, and power-user patterns. Goal: identify every capability that exists, assess what Athanor currently uses vs. what we are missing, and provide actionable recommendations for each area.

Research date: 2026-02-26. Based on official docs (code.claude.com), Anthropic GitHub repos, community sources, and empirical observation of current Athanor config.

---

## 1. CLAUDE.md Optimization

### What It Is

CLAUDE.md is a special markdown file loaded into context at session start. It is the primary mechanism for giving Claude persistent instructions. Multiple locations are supported, forming a hierarchy.

### Memory Hierarchy (Priority Order)

| Location | Scope | Shared | Loaded |
|----------|-------|--------|--------|
| Managed policy (`/etc/claude-code/CLAUDE.md` on Linux) | Organization | Yes | Always |
| Project root (`./CLAUDE.md` or `./.claude/CLAUDE.md`) | Project | Via git | Always |
| `.claude/rules/*.md` | Project | Via git | Always (conditional with `paths:`) |
| User (`~/.claude/CLAUDE.md`) | All projects | No | Always |
| Local (`./CLAUDE.local.md`) | Project, personal | No (auto-gitignored) | Always |
| Auto memory (`~/.claude/projects/<project>/memory/`) | Per project | No | First 200 lines of MEMORY.md |
| Child directory CLAUDE.md | Subdirectory | Via git | On demand when Claude reads files there |

### Key Best Practices (From Official Docs + Community)

1. **Keep it under 500 lines.** If it grows beyond that, Claude starts ignoring rules. "Important rules get lost in the noise." Move reference material to skills.
2. **Only include what Claude cannot infer from code.** Bash commands, code style deviations from defaults, non-obvious workflow rules, architectural decisions. Do not document standard language conventions or self-evident practices.
3. **Use `@path` imports** to pull in other files: `@README.md`, `@docs/git-instructions.md`, `@~/.claude/my-preferences.md`. Max depth: 5 hops. First encounter per project triggers an approval dialog.
4. **Treat it like code.** Review when Claude misbehaves. Prune regularly. Test changes by observing behavior shifts.
5. **Use emphasis for critical rules.** "IMPORTANT" and "YOU MUST" improve adherence on rules that keep getting violated.
6. **If Claude keeps violating a rule despite it being in CLAUDE.md, the file is too long.** Convert the rule to a hook (deterministic enforcement) or move less important content to skills.
7. **Run `/init` to bootstrap.** Analyzes codebase to detect build systems, test frameworks, and patterns.

### Athanor Current State

Our CLAUDE.md is well-structured with hardware tables, hierarchy, gotchas, and blockers. **Potential issue:** it is approaching the length where effectiveness degrades. Consider:
- Moving the hardware table to a skill (loaded on demand)
- Moving the "Never Do" list to a hook-enforced pattern where possible
- Keeping only the most frequently violated rules in CLAUDE.md

### Source

- https://code.claude.com/docs/en/best-practices
- https://code.claude.com/docs/en/memory
- https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/

---

## 2. Hooks System

### What It Is

Hooks are user-defined shell commands, LLM prompts, or subagents that execute automatically at specific lifecycle points. Unlike CLAUDE.md instructions (advisory), hooks are **deterministic** -- they guarantee an action happens.

### All Hook Events (16 Total)

| Event | When | Matcher | Can Block? |
|-------|------|---------|------------|
| `SessionStart` | Session begins/resumes | `startup`, `resume`, `clear`, `compact` | No |
| `SessionEnd` | Session terminates | `clear`, `logout`, `prompt_input_exit`, `bypass_permissions_disabled`, `other` | No |
| `UserPromptSubmit` | User submits prompt | No matcher (always fires) | Yes |
| `PreToolUse` | Before tool call | Tool name (`Bash`, `Edit\|Write`, `mcp__.*`) | Yes |
| `PermissionRequest` | Permission dialog shown | Tool name | Yes |
| `PostToolUse` | After tool succeeds | Tool name | No (feedback only) |
| `PostToolUseFailure` | After tool fails | Tool name | No (feedback only) |
| `Notification` | Notification sent | `permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog` | No |
| `SubagentStart` | Subagent spawned | Agent type name | No |
| `SubagentStop` | Subagent finishes | Agent type name | Yes |
| `Stop` | Claude finishes responding | No matcher (always fires) | Yes |
| `TeammateIdle` | Agent team teammate idle | No matcher (always fires) | Yes |
| `TaskCompleted` | Task being marked complete | No matcher (always fires) | Yes |
| `ConfigChange` | Config file changes | `user_settings`, `project_settings`, `local_settings`, `policy_settings`, `skills` | Yes |
| `PreCompact` | Before context compaction | `manual`, `auto` | No |
| `WorktreeCreate` | Worktree being created | No matcher | Yes (non-zero fails creation) |
| `WorktreeRemove` | Worktree being removed | No matcher | No |

### Hook Handler Types

| Type | Description | Default Timeout |
|------|-------------|-----------------|
| `command` | Shell command, receives JSON on stdin | 600s |
| `prompt` | Single-turn LLM evaluation, returns yes/no JSON | 30s |
| `agent` | Subagent with tools (Read, Grep, Glob), returns decision | 60s |

### Key Features

- **Async hooks**: Set `"async": true` to run in background without blocking.
- **`$CLAUDE_PROJECT_DIR`**: Reference project root in hook commands.
- **`$CLAUDE_PLUGIN_ROOT`**: For plugin-bundled hooks.
- **`CLAUDE_ENV_FILE`**: SessionStart hooks can persist env vars for all subsequent Bash commands.
- **`once`**: Run only once per session (skills only).
- **`statusMessage`**: Custom spinner text while hook runs.
- **Hooks in skill/agent frontmatter**: Scoped to component lifecycle, auto-cleaned up.
- **Prompt/agent hooks**: Use an LLM to evaluate conditions instead of shell scripts.

### PreToolUse Decision Control (Richest)

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|deny|ask",
    "permissionDecisionReason": "string shown to user or Claude",
    "updatedInput": { "field": "modified value" },
    "additionalContext": "injected into Claude's context"
  }
}
```

Can modify tool input before execution. "allow" bypasses permissions, "deny" blocks, "ask" escalates to user.

### Athanor Current State

We have 5 hooks configured:
1. `PreToolUse` (Edit|Write) - path protection
2. `Notification` (permission_prompt, idle_prompt) - desktop notifications
3. `Stop` - auto-commit
4. `PreCompact` - state snapshot
5. `SessionStart` - health check + compact state re-injection

### Missing Opportunities

- **PostToolUse (Edit|Write)**: Auto-lint after file edits. Could run eslint/prettier/ruff automatically.
- **UserPromptSubmit**: Could inject dynamic context (e.g., current git branch, running containers, GPU status).
- **SessionEnd**: Could flush any state, update MEMORY.md, or trigger a summary.
- **Stop with LLM evaluation**: "prompt" type hook that asks an LLM to verify all tasks are complete before stopping.
- **PostToolUseFailure**: Log failures, send alerts, provide corrective context.
- **PermissionRequest**: Auto-approve known-safe operations programmatically instead of via allowlist.

### Source

- https://code.claude.com/docs/en/hooks
- https://github.com/disler/claude-code-hooks-mastery
- https://claude.com/blog/how-to-configure-hooks

---

## 3. Rules Directory (`.claude/rules/`)

### What It Is

Modular, topic-specific instruction files in `.claude/rules/`. All `.md` files are auto-loaded as project memory, same priority as `.claude/CLAUDE.md`. Supports path-scoping via YAML frontmatter.

### Path-Specific Rules

```markdown
---
paths:
  - "src/api/**/*.ts"
  - "lib/**/*.ts"
---

# API Development Rules
- All endpoints must include input validation
```

Rules without `paths:` are loaded unconditionally. Rules with `paths:` only load when Claude works with matching files.

### Glob Patterns

| Pattern | Matches |
|---------|---------|
| `**/*.ts` | All TypeScript files in any directory |
| `src/**/*` | All files under src/ |
| `*.md` | Markdown files in project root only |
| `src/**/*.{ts,tsx}` | Brace expansion for multiple extensions |
| `{src,lib}/**/*.ts` | Brace expansion for multiple directories |

### Features

- Recursive discovery of subdirectories
- Symlinks supported (shared rules across projects via `ln -s`)
- User-level rules at `~/.claude/rules/` (lower priority than project rules)
- All files are `.md` format

### Athanor Current State

We have 4 rules files: `agents.md`, `ansible.md`, `dashboard.md`, `vllm.md`. **None use path-scoping.**

### Recommendations

- Add `paths:` frontmatter to each rule so they only load when relevant:
  - `ansible.md` -> `paths: ["ansible/**/*"]`
  - `dashboard.md` -> `paths: ["projects/dashboard/**/*"]`
  - `agents.md` -> `paths: ["projects/agents/**/*", "scripts/mcp-athanor-agents.py"]`
  - `vllm.md` -> `paths: ["ansible/roles/vllm/**/*"]`
- This reduces noise in sessions that do not touch those domains.
- Consider adding rules for: `eoq.md` (EoBQ game), `infrastructure.md` (hardware/network), `docs.md` (doc conventions).

### Source

- https://code.claude.com/docs/en/memory#modular-rules-with-claude-rules
- https://claudefa.st/blog/guide/mechanics/rules-directory

---

## 4. Skills

### What It Is

Skills are markdown files (SKILL.md) that extend Claude's knowledge with reusable instructions, reference material, and invocable workflows. They are loaded on demand (descriptions at session start, full content when invoked), unlike CLAUDE.md which loads fully at session start.

### Skills vs Commands

**Commands (`/.claude/commands/`) and skills (`.claude/skills/`) are now unified.** Both create `/slash-commands`. Skills add: directory for supporting files, frontmatter for invocation control, and auto-loading when relevant. Existing commands keep working; if both share a name, the skill wins.

### SKILL.md Frontmatter Fields

| Field | Description |
|-------|-------------|
| `name` | Display name, becomes the `/command` |
| `description` | When to use (Claude matches against this) |
| `argument-hint` | Hint for autocomplete, e.g., `[issue-number]` |
| `disable-model-invocation` | `true` = only user can invoke (not Claude) |
| `user-invocable` | `false` = hidden from `/` menu, only Claude invokes |
| `allowed-tools` | Tools Claude can use without permission while skill is active |
| `model` | Override model while skill is active |
| `context` | `fork` = run in isolated subagent context |
| `agent` | Which subagent type when `context: fork` (`Explore`, `Plan`, custom) |
| `hooks` | Lifecycle hooks scoped to skill lifetime |

### String Substitutions

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All arguments passed |
| `$ARGUMENTS[N]` or `$N` | Specific argument by 0-based index |
| `${CLAUDE_SESSION_ID}` | Current session ID |

### Dynamic Context Injection

The `` !`command` `` syntax runs shell commands before skill content is sent. Output replaces the placeholder:

```markdown
## PR Context
- PR diff: !`gh pr diff`
- Changed files: !`gh pr diff --name-only`
```

### Supporting Files

Skills can include multiple files (templates, examples, scripts). Keep SKILL.md under 500 lines. Reference supporting files with relative links.

### Activation Optimization (Community Finding)

Properly optimized descriptions can improve activation from 20% to 50%. Adding examples improves it from 72% to 90%.

### Athanor Current State

We have 10 skills/commands. Some good patterns already. **Opportunities:**
- Add `disable-model-invocation: true` to destructive skills (deploy, vllm-deploy)
- Add `context: fork` to research-heavy skills to preserve main context
- Add `argument-hint` for better autocomplete UX
- Consider a `session-report` skill that summarizes what was done

### Source

- https://code.claude.com/docs/en/skills
- https://gist.github.com/mellanon/50816550ecb5f3b239aa77eef7b8ed8d

---

## 5. Memory / Auto Memory

### What It Is

Claude Code has two memory systems:
1. **CLAUDE.md files**: You write instructions for Claude
2. **Auto memory**: Claude writes notes for itself in `~/.claude/projects/<project>/memory/`

### Auto Memory Details

- Stores: project patterns, debugging insights, architecture notes, preferences
- Location: `~/.claude/projects/<project>/memory/MEMORY.md` + topic files
- Only first 200 lines of MEMORY.md are loaded at session start
- Topic files (e.g., `debugging.md`, `api-conventions.md`) are NOT loaded at startup -- read on demand
- Claude reads and writes memory during sessions
- Toggle with `/memory` command or `autoMemoryEnabled` in settings.json
- Override all settings with `CLAUDE_CODE_DISABLE_AUTO_MEMORY` env var (0=force on, 1=force off)

### Best Practices

- Direct Claude: "remember that we use pnpm" or "save to memory that API tests need Redis"
- Structure as bullet points under markdown headings
- Review periodically as project evolves
- Keep MEMORY.md concise; move details to topic files

### Subagent Persistent Memory (New Feature)

Subagents can have their own persistent memory with the `memory` field:
- `user`: `~/.claude/agent-memory/<name>/` (cross-project)
- `project`: `.claude/agent-memory/<name>/` (project-specific, version controlled)
- `local`: `.claude/agent-memory-local/<name>/` (project-specific, gitignored)

This allows subagents to learn and improve across sessions.

### Athanor Current State

We maintain a comprehensive MEMORY.md manually. Auto memory is enabled (`CLAUDE_CODE_DISABLE_AUTO_MEMORY=0`). We have not used subagent persistent memory.

### Recommendations

- Use subagent persistent memory for specialized agents (security reviewer, code reviewer) that should accumulate knowledge
- Our MEMORY.md could benefit from splitting detailed sections into topic files to stay under 200 lines

### Source

- https://code.claude.com/docs/en/memory

---

## 6. Subagents / Agent Capabilities

### Built-in Subagents

| Agent | Model | Tools | Purpose |
|-------|-------|-------|---------|
| **Explore** | Haiku | Read-only | Fast codebase search/analysis, three thoroughness levels |
| **Plan** | Inherits | Read-only | Plan mode research |
| **General-purpose** | Inherits | All | Complex multi-step tasks |
| **Bash** | Inherits | Bash | Terminal commands in separate context |
| **statusline-setup** | Sonnet | -- | Configuring `/statusline` |
| **Claude Code Guide** | Haiku | -- | Questions about Claude Code features |

### Custom Subagent Configuration

Subagents are Markdown files with YAML frontmatter in `.claude/agents/` (project) or `~/.claude/agents/` (user).

| Field | Description |
|-------|-------------|
| `name` | Unique identifier |
| `description` | When Claude should delegate |
| `tools` | Allowed tools (inherits all if omitted) |
| `disallowedTools` | Tools to deny |
| `model` | `sonnet`, `opus`, `haiku`, or `inherit` |
| `permissionMode` | `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan` |
| `maxTurns` | Maximum agentic turns |
| `skills` | Skills to preload at startup |
| `mcpServers` | MCP servers available |
| `hooks` | Lifecycle hooks scoped to subagent |
| `memory` | Persistent memory scope (`user`, `project`, `local`) |
| `background` | `true` = always run as background task |
| `isolation` | `worktree` = run in temporary git worktree |
| `color` | Background color for UI identification |

### Key Patterns

- **`isolation: worktree`**: Runs in a separate git worktree. Auto-cleaned if no changes.
- **`Task(agent_type)` restriction**: In `tools` field, limit which subagents can be spawned.
- **Deny specific agents**: `"deny": ["Task(Explore)"]` in permissions.
- **CLI-defined subagents**: `claude --agents '{JSON}'` for ephemeral session-only agents.
- **Ctrl+B**: Background a running task/subagent.
- **Resume subagents**: Retain full conversation history by asking Claude to "continue that review."

### Agent Teams (Experimental)

Enable with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. Multiple independent Claude Code sessions with:
- Team lead that coordinates
- Shared task list with dependency management
- Peer-to-peer messaging between teammates
- `TeammateIdle` and `TaskCompleted` hooks for quality gates
- In-process or split-pane (tmux/iTerm2) display modes
- Keyboard: `Shift+Down` cycle teammates, `Ctrl+T` toggle task list, `Enter` view session

### Athanor Current State

We have agent teams enabled. We have `.claude/agents/` directory but no custom subagents defined. **This is a major gap.**

### Recommendations

- Create custom subagents for recurring tasks:
  - `infrastructure-checker`: Read-only Haiku agent for health checks
  - `deploy-reviewer`: Reviews ansible changes before deployment
  - `doc-updater`: Keeps docs in sync after changes
- Use `memory: user` on frequently used agents so they accumulate knowledge
- Use `isolation: worktree` for agents doing risky code changes

### Source

- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/agent-teams

---

## 7. MCP Servers

### What It Is

Model Context Protocol servers connect Claude to external services and tools. They load at session start and their tool definitions consume context every request.

### Key Configuration

| Setting | Purpose |
|---------|---------|
| `enableAllProjectMcpServers` | Auto-approve all project MCP servers |
| `enabledMcpjsonServers` | Specific servers to approve |
| `disabledMcpjsonServers` | Specific servers to reject |
| `ENABLE_TOOL_SEARCH` | `auto` (default), `true`, `false`, `auto:N` |
| `MCP_TIMEOUT` | Startup timeout (ms) |
| `MCP_TOOL_TIMEOUT` | Tool execution timeout (ms) |
| `MAX_MCP_OUTPUT_TOKENS` | Max MCP tool output (default: 25000) |

### Tool Search (Context Optimization)

Enabled by default. Loads MCP tools up to 10% of context, defers the rest until needed. Critical for having many MCP servers without bloating context. Configure with `ENABLE_TOOL_SEARCH=auto:N` to set the percentage.

### MCP Prompts

MCP servers can expose prompts that appear as `/mcp__<server>__<prompt>` commands.

### MCP Bridge Pattern

Athanor uses `scripts/mcp-athanor-agents.py` as an MCP bridge, exposing 14 tools from our local agent framework to Claude Code. This pattern (local service -> MCP server wrapper -> Claude Code) is powerful for integrating custom infrastructure.

### Athanor Current State

We have: sequential-thinking, context7 (x3 instances!), filesystem, grafana, athanor-agents. Plus github, brave-search, playwright, memory, desktop-commander in user scope.

### Issues Found

- **Triple Context7**: We have `mcp__context7__*`, `mcp__plugin_context7_context7__*`, and `mcp__claude_ai_Context7__*` all allowed. This is likely three instances of the same server, tripling context cost. Should deduplicate.
- **Desktop Commander**: Listed in permissions but may not provide much value beyond native Bash tool for our use case.

### Source

- https://code.claude.com/docs/en/mcp

---

## 8. Settings and Configuration

### Complete Settings Schema

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": { "allow": [], "ask": [], "deny": [] },
  "env": {},
  "sandbox": {},
  "hooks": {},
  "model": "string",
  "availableModels": ["string"],
  "apiKeyHelper": "/path/to/script.sh",
  "cleanupPeriodDays": 30,
  "outputStyle": "string",
  "language": "string",
  "attribution": { "commit": "string", "pr": "string" },
  "companyAnnouncements": ["string"],
  "statusLine": { "type": "command", "command": "..." },
  "fileSuggestion": { "type": "command", "command": "..." },
  "enabledPlugins": {},
  "extraKnownMarketplaces": {},
  "alwaysThinkingEnabled": true,
  "plansDirectory": "string",
  "showTurnDuration": true,
  "spinnerVerbs": { "mode": "append", "verbs": [] },
  "spinnerTipsEnabled": true,
  "spinnerTipsOverride": { "tips": [], "excludeDefault": true },
  "terminalProgressBarEnabled": false,
  "prefersReducedMotion": true,
  "teammateMode": "auto|in-process|tmux",
  "autoMemoryEnabled": true,
  "respectGitignore": false
}
```

### Key Environment Variables We Should Know

| Variable | Purpose | Athanor Status |
|----------|---------|---------------|
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | Agent teams | Set to 1 |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Compaction threshold (1-100) | Set to 80 |
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY` | Force memory on/off | Set to 0 |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | Max output tokens (default 32000, max 64000) | Not set |
| `MAX_THINKING_TOKENS` | Extended thinking budget | Not set |
| `CLAUDE_CODE_EFFORT_LEVEL` | `low`, `medium`, `high` | Not set |
| `CLAUDE_CODE_SIMPLE` | Minimal mode (Bash/Read/Edit only) | Not set |
| `BASH_DEFAULT_TIMEOUT_MS` | Default bash timeout | Not set |
| `BASH_MAX_TIMEOUT_MS` | Max bash timeout | Not set |
| `SLASH_COMMAND_TOOL_CHAR_BUDGET` | Override skill description budget | Not set |
| `ENABLE_TOOL_SEARCH` | MCP tool search mode | Not set (default auto) |
| `CLAUDE_CODE_SHELL_PREFIX` | Prefix for all bash commands | Not set |
| `CLAUDE_CODE_EXIT_AFTER_STOP_DELAY` | Auto-exit delay (ms) | Not set |

### Settings We Should Consider Adding

1. **`statusLine`**: Custom status bar showing context usage, costs, git branch, GPU status
2. **`alwaysThinkingEnabled: true`**: Extended thinking by default for complex work
3. **`CLAUDE_CODE_MAX_OUTPUT_TOKENS: 64000`**: Maximum output for comprehensive responses
4. **`showTurnDuration: true`**: See how long each turn takes
5. **`attribution`**: Custom commit/PR attribution format
6. **`fileSuggestion`**: Custom `@` autocomplete script that includes remote files, docs, etc.

### Source

- https://code.claude.com/docs/en/settings

---

## 9. Plugins

### What It Is

Plugins bundle skills, hooks, subagents, MCP servers, and LSP servers into a single installable unit. Distributed through marketplaces.

### Plugin Structure

```
my-plugin/
  .claude-plugin/     # Metadata (REQUIRED)
  commands/           # Slash commands
  agents/             # Subagent definitions
  skills/             # SKILL.md files
  hooks/hooks.json    # Hook definitions
  .mcp.json           # MCP server definitions
  .lsp.json           # LSP server configurations
```

### Installation

```
/plugin                    # Browse marketplace
/plugin install name@source
```

### Available Marketplaces

Anthropic maintains `claude-plugins-official`. Over 9,000 community plugins exist across ClaudePluginHub, Claude-Plugins.dev, and others.

### Popular Plugins (Feb 2026)

| Plugin | Installs | Purpose |
|--------|----------|---------|
| Frontend Design | 96K | Frontend development |
| Context7 | 71K | Live documentation |
| Ralph Loop | 57K | Iterative development |
| Code Review | 50K | Review automation |
| Playwright | 28K | Browser testing |
| Security Guidance | 25K | Security checks |

### Configuration in settings.json

```json
{
  "enabledPlugins": { "formatter@acme-tools": true },
  "extraKnownMarketplaces": {
    "acme-tools": { "source": { "source": "github", "repo": "acme-corp/plugins" } }
  }
}
```

### Athanor Current State

We are not using any plugins. This is an untapped area.

### Recommendations

- Evaluate "Code Review" plugin for automated review
- Evaluate code intelligence plugins for TypeScript (EoBQ, Command Center) and Python (agents)
- Consider creating our own Athanor plugin to package our skills/hooks/agents for portability

### Source

- https://code.claude.com/docs/en/discover-plugins
- https://github.com/anthropics/claude-code/blob/main/plugins/README.md

---

## 10. Keyboard Shortcuts and Interactive Features

### All Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Esc` | Stop Claude mid-action |
| `Esc + Esc` | Rewind menu (restore code/conversation/both, or summarize) |
| `Shift+Tab` or `Alt+M` | Toggle permission modes (Normal, Auto-Accept, Plan) |
| `Ctrl+G` | Open prompt in default text editor |
| `Ctrl+O` | Toggle verbose output |
| `Ctrl+B` | Background running tasks (tmux: press twice) |
| `Ctrl+T` | Toggle task list |
| `Ctrl+R` | Reverse search command history |
| `Ctrl+V` | Paste image from clipboard |
| `Ctrl+L` | Clear terminal screen |
| `Ctrl+F` | Kill all background agents (press twice to confirm) |
| `Ctrl+D` | Exit session |
| `Alt+P` | Switch model without clearing prompt |
| `Alt+T` | Toggle extended thinking |
| `\` + Enter | Multiline input |
| `!` prefix | Direct bash mode |
| `@` | File path autocomplete |
| `/` | Command/skill autocomplete |

### Agent Team Shortcuts

| Shortcut | Action |
|----------|--------|
| `Shift+Up/Down` | Cycle through teammates |
| `Ctrl+T` | Toggle task list |
| `Enter` | View selected teammate's session |
| `Escape` | Interrupt teammate |

### All Built-in Commands

| Command | Purpose |
|---------|---------|
| `/clear` | Clear conversation |
| `/compact [instructions]` | Compact with focus |
| `/config` | Settings interface |
| `/context` | Visualize context usage as colored grid |
| `/cost` | Token usage statistics |
| `/copy` | Copy last response (with code block picker) |
| `/debug [description]` | Troubleshoot session |
| `/doctor` | Health check installation |
| `/exit` | Exit REPL |
| `/export [filename]` | Export conversation |
| `/help` | Usage help |
| `/hooks` | Manage hooks interactively |
| `/init` | Initialize CLAUDE.md |
| `/mcp` | Manage MCP connections |
| `/memory` | Edit memory files |
| `/model` | Select model (left/right for effort level) |
| `/permissions` | View/update permissions |
| `/plan` | Enter plan mode |
| `/plugin` | Browse/install plugins |
| `/rename <name>` | Rename session |
| `/resume [session]` | Resume conversation |
| `/rewind` | Rewind conversation/code |
| `/stats` | Usage visualization, streaks, model preferences |
| `/status` | Version, model, account, connectivity |
| `/statusline` | Configure status bar |
| `/tasks` | List/manage background tasks |
| `/teleport` | Resume remote session from claude.ai |
| `/desktop` | Hand off to Desktop app |
| `/theme` | Change color theme |
| `/todos` | List TODO items |
| `/usage` | Plan limits and rate limit status |
| `/vim` | Enable vim editing mode |

### Status Line

Custom script that runs in the terminal status bar. Receives JSON session metadata (model, tokens, cost, context usage). Configure with `/statusline` or `statusLine` in settings.json. Community tools: `ccstatusline` (React/Ink, themes, Powerline support).

### Other Interactive Features

- **Vim mode**: Full vim keybindings for input editing (`/vim`)
- **Task list**: `Ctrl+T` to toggle; shared across agent teams; persists through compaction
- **PR review status**: Clickable PR link in footer with color-coded review state
- **Prompt suggestions**: Auto-generated from git history, Tab to accept
- **Checkpoints**: Every action creates a checkpoint; rewind code/conversation independently
- **Session naming**: `/rename` for findable sessions, treat like branches
- **Export**: `/export` to save conversation to file or clipboard

### Source

- https://code.claude.com/docs/en/interactive-mode
- https://code.claude.com/docs/en/statusline

---

## 11. Worktrees

### What It Is

Git worktrees allow running Claude in an isolated copy of the repository. The Desktop app creates worktrees automatically for each session. In CLI, use `--worktree` flag or `isolation: "worktree"` in subagent config.

### Key Features

- Each worktree gets its own branch
- Changes are isolated from main working directory
- Auto-cleaned if subagent makes no changes
- `WorktreeCreate` and `WorktreeRemove` hooks for custom setup/teardown
- Separate auto memory directories per worktree

### Use Cases

- Risky refactoring in isolation
- Parallel Claude sessions on different features
- Subagents that modify code without affecting main tree

### Source

- https://code.claude.com/docs/en/common-workflows#run-parallel-claude-code-sessions-with-git-worktrees

---

## 12. CLI Flags and Headless Mode

### Key CLI Flags

| Flag | Purpose |
|------|---------|
| `claude -p "prompt"` | Headless mode (no interactive session) |
| `--output-format json\|stream-json` | Structured output for scripts |
| `--continue` | Resume most recent session |
| `--resume` | Pick from recent sessions |
| `--allowedTools` | Restrict tools for batch operations |
| `--disallowedTools` | Block specific tools |
| `--agents '{JSON}'` | Session-only subagent definitions |
| `--agent <name>` | Run as a specific agent (main thread) |
| `--add-dir` | Additional working directories |
| `--worktree` | Create isolated git worktree |
| `--dangerously-skip-permissions` | Bypass all checks (use in sandbox only) |
| `--verbose` | Debug output |
| `--teammate-mode in-process\|tmux` | Agent team display override |

### Fan-Out Pattern

```bash
for file in $(cat files.txt); do
  claude -p "Migrate $file from React to Vue" \
    --allowedTools "Edit,Bash(git commit *)"
done
```

### Pipe Input

```bash
cat error.log | claude -p "What caused this error?"
```

### Source

- https://code.claude.com/docs/en/best-practices
- https://code.claude.com/docs/en/headless

---

## Gap Analysis: Athanor vs. Available Features

### Currently Using Well
- [x] CLAUDE.md with good structure
- [x] MEMORY.md with comprehensive state
- [x] 5 hooks (PreToolUse, Notification, Stop, PreCompact, SessionStart)
- [x] 4 path-scoped rules (not yet using `paths:` frontmatter)
- [x] 10 skills/commands
- [x] Agent teams enabled
- [x] MCP servers (7+ configured)
- [x] Comprehensive permission allowlist
- [x] Auto-compaction at 80%

### Not Using (Should Evaluate)

| Feature | Priority | Effort | Impact |
|---------|----------|--------|--------|
| **Custom subagents** in `.claude/agents/` | High | Low | High -- specialize for infrastructure, review, docs |
| **Path-scoped rules** (`paths:` frontmatter) | High | Low | Medium -- reduces context noise |
| **Status line** | High | Low | High -- persistent context/cost visibility |
| **Plugins** | Medium | Low | Medium -- code intelligence, review automation |
| **PostToolUse hooks** (auto-lint) | Medium | Low | Medium -- catches issues immediately |
| **UserPromptSubmit hooks** (context injection) | Medium | Medium | Medium -- dynamic environment info |
| **Subagent persistent memory** | Medium | Low | High -- agents learn across sessions |
| **Skill `context: fork`** | Medium | Low | Medium -- preserve main context |
| **`disable-model-invocation`** on deploy skills | Medium | Low | Low -- safety improvement |
| **Deduplicate Context7 MCP** | High | Low | Medium -- reduce wasted context |
| **`alwaysThinkingEnabled`** | Low | Low | Low -- already available with Alt+T |
| **`CLAUDE_CODE_MAX_OUTPUT_TOKENS: 64000`** | Low | Low | Low -- situational benefit |
| **Custom `fileSuggestion` script** | Low | Medium | Low -- nice-to-have |
| **SessionEnd hook** | Low | Low | Low -- cleanup/summary |

---

## Recommendations (Priority Order)

### 1. Create Custom Subagents (High Priority, Low Effort)

Create `.claude/agents/` files for:
- `infrastructure-checker.md`: Haiku model, read-only, checks health across nodes
- `deploy-reviewer.md`: Reviews ansible/docker changes before deployment
- `doc-updater.md`: Updates docs after code changes, with `memory: project`

### 2. Add Path Scoping to Rules (High Priority, Low Effort)

Add `paths:` frontmatter to all 4 existing rule files. Immediately reduces context noise.

### 3. Configure Status Line (High Priority, Low Effort)

Run `/statusline` to set up a status bar showing context usage, model, git branch, and cost. Critical for managing the #1 resource constraint (context window).

### 4. Deduplicate Context7 (High Priority, Low Effort)

Remove duplicate Context7 MCP server instances from settings. Keep one.

### 5. Add PostToolUse Lint Hook (Medium Priority, Low Effort)

Auto-run linting after file edits. Catches issues before they compound.

### 6. Add `disable-model-invocation: true` to Deploy Skills (Medium Priority, Low Effort)

Prevent Claude from autonomously triggering deployment. Safety improvement.

### 7. Evaluate Plugins (Medium Priority, Low Effort)

Browse `/plugin` marketplace for code intelligence (TypeScript, Python) and code review plugins.

### 8. Enable Subagent Persistent Memory (Medium Priority, Low Effort)

Add `memory: user` to frequently-used custom subagents.

---

Last updated: 2026-02-26

Sources:
- https://code.claude.com/docs/en/best-practices
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/memory
- https://code.claude.com/docs/en/skills
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/agent-teams
- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/features-overview
- https://code.claude.com/docs/en/interactive-mode
- https://code.claude.com/docs/en/discover-plugins
- https://code.claude.com/docs/en/statusline
- https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/
- https://github.com/disler/claude-code-hooks-mastery
- https://github.com/anthropics/claude-code/blob/main/plugins/README.md
