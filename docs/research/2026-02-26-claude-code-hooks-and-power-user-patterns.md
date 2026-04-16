# Claude Code Hooks & Power-User Patterns

**Date:** 2026-02-26
**Status:** Research complete
**Scope:** Hooks, automation, security, notifications, statusline, permissions, CI/CD

---

## Context

Claude Code supports 17 lifecycle hook events, three hook handler types (command, prompt, agent), hierarchical settings at five scope levels, and regex-based matchers. Athanor already runs 7 hooks across 6 events. This research surveys what advanced users and open-source projects are actually running, identifies gaps in our current setup, and catalogs patterns worth adopting.

### Athanor's Current Hook Inventory

| Event | Script | What It Does |
|-------|--------|--------------|
| PreToolUse | `pre-tool-use-protect-paths.sh` | Blocks writes to SSH keys, Unraid configs, parity |
| PostToolUse | `post-tool-use-typecheck.sh` | Runs `tsc --noEmit` on dashboard .ts/.tsx edits |
| UserPromptSubmit | `user-prompt-context.sh` | Injects timestamp + git branch + dirty count |
| Notification | (inline) | `notify-send` for permission_prompt and idle_prompt |
| Stop | `stop-autocommit.sh` | Auto-commits state files (CLAUDE.md, BUILD-MANIFEST, etc.) |
| PreCompact | `pre-compact-save.sh` | Snapshots git state + infra health to /tmp for recovery |
| SessionStart | `session-start.sh` | Prints branch, last commit, uncommitted changes, build principle |
| SessionStart | `session-start-health.sh` | Parallel SSH health checks on all 3 nodes (5s timeout) |
| SessionStart(compact) | (inline) | Restores pre-compaction state from /tmp |

---

## 1. Hook Events Reference (All 17)

Source: [Official hooks reference](https://code.claude.com/docs/en/hooks)

| Event | Fires When | Can Block? | Matcher Field |
|-------|-----------|------------|---------------|
| **SessionStart** | Session begins/resumes/post-compact | No | source: `startup`, `resume`, `clear`, `compact` |
| **SessionEnd** | Session terminates | No | reason: `clear`, `logout`, `prompt_input_exit`, `other` |
| **UserPromptSubmit** | User submits prompt, before processing | No | none (always fires) |
| **PreToolUse** | Before tool executes | **Yes** (exit 2 or JSON deny) | tool name |
| **PermissionRequest** | Permission dialog appears | **Yes** | tool name |
| **PostToolUse** | After tool succeeds | **Yes** (decision: "block") | tool name |
| **PostToolUseFailure** | After tool fails | No | tool name |
| **Notification** | Claude sends notification | No | type: `permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog` |
| **SubagentStart** | Subagent spawns | No | agent type |
| **SubagentStop** | Subagent finishes | No | agent type |
| **Stop** | Claude finishes responding | **Yes** (decision: "block") | none (always fires) |
| **TeammateIdle** | Agent team member goes idle | No | none (always fires) |
| **TaskCompleted** | Task marked complete | No | none (always fires) |
| **ConfigChange** | Config file changes during session | **Yes** | source: `user_settings`, `project_settings`, etc. |
| **WorktreeCreate** | Worktree created | No | none |
| **WorktreeRemove** | Worktree removed | No | none |
| **PreCompact** | Before context compaction | No | trigger: `manual`, `auto` |

### Hook Handler Types

1. **command** -- Shell command, receives JSON on stdin, returns via exit code + stdout/stderr
2. **prompt** -- Single-turn LLM call (Haiku by default, configurable model). Returns `{"ok": true}` or `{"ok": false, "reason": "..."}`
3. **agent** -- Multi-turn subagent with tool access (Read, Grep, Glob, Bash). Same output format as prompt but can inspect codebase.

### Exit Codes

- **0**: Allow / proceed. stdout added as context for SessionStart/UserPromptSubmit.
- **2**: Block the action. stderr fed to Claude as feedback.
- **Other**: Proceed anyway. stderr logged but not shown (visible with Ctrl+O verbose mode).

### JSON Decision Output (PreToolUse)

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|deny|ask",
    "permissionDecisionReason": "Use rg instead of grep for better performance"
  }
}
```

### Context Injection (UserPromptSubmit)

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Injected text visible to Claude"
  }
}
```

### Environment Variable Persistence (SessionStart only)

Write `export FOO=bar` to `$CLAUDE_ENV_FILE` to persist env vars for all subsequent Bash calls in the session. Known caveat: `CLAUDE_ENV_FILE` may be empty in some contexts (plugin hooks).

---

## 2. Real-World Hook Patterns People Are Running

### 2.1 Security & Protection

**Destructive command blocker** (Steve Kinney, aiorg.dev)

```bash
#!/usr/bin/env bash
set -euo pipefail
cmd=$(jq -r '.tool_input.command // ""')

deny_patterns=(
  'rm\s+-rf\s+/'
  'git\s+reset\s+--hard'
  'curl\s+http'
)

for pat in "${deny_patterns[@]}"; do
  if echo "$cmd" | grep -Eiq "$pat"; then
    echo "Blocked command: matches denied pattern '$pat'" 1>&2
    exit 2
  fi
done
exit 0
```

**Package manager enforcement** (Steve Kinney)

```bash
#!/usr/bin/env bash
set -euo pipefail
cmd=$(jq -r '.tool_input.command // ""')

if [ -f pnpm-lock.yaml ] && echo "$cmd" | grep -Eq '\bnpm\b'; then
  echo "This repo uses pnpm. Replace 'npm' with 'pnpm'." 1>&2
  exit 2
fi
exit 0
```

**Protected file guard** (Anthropic official example)

```bash
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

PROTECTED_PATTERNS=(".env" "package-lock.json" ".git/")

for pattern in "${PROTECTED_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]]; then
    echo "Blocked: $FILE_PATH matches protected pattern '$pattern'" >&2
    exit 2
  fi
done
exit 0
```

**Universal MCP permission hook** (doobidoo/GitHub Gist) -- Node.js script that auto-approves safe MCP operations (get/list/read/search) while requiring confirmation for destructive ones (delete/write/create/deploy). Patterns:
- SAFE: `get`, `list`, `read`, `retrieve`, `fetch`, `search`, `find`, `query`, `check`, `status`, `health`, `view`, `show`, `describe`, `inspect`
- DESTRUCTIVE: `delete`, `remove`, `destroy`, `drop`, `clear`, `wipe`, `purge`, `write`, `create`, `deploy`, `publish`, `execute`, `run`

**Dependency install gate** (Pixelmojo)

```javascript
const fs = require('fs')
const data = JSON.parse(fs.readFileSync('/dev/stdin', 'utf8'))
const cmd = data.command || ''
const isInstall = cmd.match(/npm install|yarn add|pip install|pnpm add/)
if (isInstall && !cmd.includes('--save-dev')) {
  console.error('BLOCKED: Production deps require approval.')
  process.exit(1)
}
```

### 2.2 Auto-Formatting & Linting

**Prettier after every edit** (Anthropic official)

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.file_path' | xargs npx prettier --write"
          }
        ]
      }
    ]
  }
}
```

**ESLint + TypeScript combined** (aiorg.dev)

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'FILE=$(jq -r \".tool_input.file_path\" <<< \"$(cat)\"); if [[ \"$FILE\" == *.ts || \"$FILE\" == *.tsx || \"$FILE\" == *.js || \"$FILE\" == *.jsx ]]; then npx eslint --fix \"$FILE\" 2>/dev/null; fi; exit 0'"
          }
        ]
      }
    ]
  }
}
```

**TypeScript type-checking with timeout** (aiorg.dev)

```json
{
  "matcher": "Write|Edit",
  "hooks": [
    {
      "type": "command",
      "command": "bash -c 'FILE=$(jq -r \".tool_input.file_path\" <<< \"$(cat)\"); if [[ \"$FILE\" == *.ts || \"$FILE\" == *.tsx ]]; then npx tsc --noEmit 2>&1 | head -20; fi; exit 0'",
      "timeout": 30
    }
  ]
}
```

**Auto-run tests on test file changes** (aiorg.dev)

```json
{
  "matcher": "Write|Edit",
  "hooks": [
    {
      "type": "command",
      "command": "bash -c 'FILE=$(jq -r \".tool_input.file_path\" <<< \"$(cat)\"); if [[ \"$FILE\" == *.test.* || \"$FILE\" == *.spec.* ]]; then npx vitest run \"$FILE\" 2>&1 | tail -5; fi; exit 0'",
      "timeout": 30,
      "async": true
    }
  ]
}
```

### 2.3 Context Injection

**Post-compaction context restore** (Anthropic official)

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Reminder: use Bun, not npm. Run bun test before committing. Current sprint: auth refactor.'"
          }
        ]
      }
    ]
  }
}
```

**Branch + recent commits on startup** (aiorg.dev)

```json
{
  "matcher": "startup|resume",
  "hooks": [
    {
      "type": "command",
      "command": "bash -c 'BRANCH=$(git -C \"$CLAUDE_PROJECT_DIR\" branch --show-current 2>/dev/null); echo \"Current branch: $BRANCH. Recent commits: $(git -C \"$CLAUDE_PROJECT_DIR\" log --oneline -3 2>/dev/null)\"'"
    }
  ]
}
```

**Environment variable injection via CLAUDE_ENV_FILE** (aiorg.dev)

```json
{
  "matcher": "startup",
  "hooks": [
    {
      "type": "command",
      "command": "bash -c 'if [ -n \"$CLAUDE_ENV_FILE\" ]; then echo \"export NODE_ENV=development\" >> \"$CLAUDE_ENV_FILE\"; echo \"export NEXT_TELEMETRY_DISABLED=1\" >> \"$CLAUDE_ENV_FILE\"; fi; exit 0'"
    }
  ]
}
```

**Auto-refresh context every N prompts** (John Lindquist, ScriptKit creator)

TypeScript hook using Bun that tracks prompt count per session in `/tmp/` and re-injects tool reminders every 3 prompts via `additionalContext`:

```typescript
const FREQUENCY = 3  // Every 3 prompts
const START_AFTER = 3 // Don't show until prompt 3

if (stats.promptCount >= START_AFTER && stats.promptCount % FREQUENCY === 0) {
  messages.push(`<reminder type="tools">
**Available Tools Refresh** (prompt ${stats.promptCount})
...
</reminder>`)
}
```

### 2.4 Notification Patterns

**macOS with terminal-notifier + sounds** (d12frosted.io / Boris Buliga)

```json
{
  "Notification": [
    {
      "matcher": "*",
      "hooks": [
        {
          "type": "command",
          "command": "~/.config/claude/notify.sh 'Awaiting your input' && afplay /System/Library/Sounds/Glass.aiff"
        }
      ]
    }
  ],
  "Stop": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "~/.config/claude/notify.sh 'Task completed' && afplay /System/Library/Sounds/Hero.aiff"
        }
      ]
    }
  ]
}
```

The notify.sh script resolves the git repo name and yabai workspace for context-rich notifications using `terminal-notifier -sender com.anthropic.claudefordesktop` to show Claude's app icon.

**Linux notify-send** (Anthropic official, what Athanor uses)

```json
{
  "matcher": "permission_prompt|idle_prompt",
  "hooks": [
    {
      "type": "command",
      "command": "notify-send 'Claude Code' 'Needs your attention' --urgency=normal"
    }
  ]
}
```

**TTS notifications** (tihomiro/claude-code-boilerplate)

Uses a priority chain: ElevenLabs -> OpenAI -> pyttsx3. The Stop hook generates an AI-summarized completion message and reads it aloud.

**Cross-platform audio hooks** (ChanMeng666/claude-code-audio-hooks)

Plays different sounds for different events. Desktop notifications + audio cues + optional text-to-speech.

### 2.5 Audit & Logging

**Command audit log** (Steve Kinney, multiple repos)

```bash
#!/usr/bin/env bash
set -euo pipefail
cmd=$(jq -r '.tool_input.command // ""')
printf '%s %s\n' "$(date -Is)" "$cmd" >> .claude/bash-commands.log
exit 0
```

**MCP tool audit** (aiorg.dev)

```json
{
  "PostToolUse": [
    {
      "matcher": "mcp__.*",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'INPUT=$(cat); TOOL=$(echo \"$INPUT\" | jq -r \".tool_name\"); echo \"$(date +%H:%M:%S) $TOOL\" >> \"$CLAUDE_PROJECT_DIR\"/.claude/mcp-audit.log; exit 0'"
        }
      ]
    }
  ]
}
```

**Full session logging** (tihomiro/claude-code-boilerplate)

Logs every event type to separate JSON files in `.claude/logs/`:
- `user_prompt_submit.json` -- all prompts
- `pre_tool_use.json` -- all tool calls with inputs
- `post_tool_use.json` -- all results
- `chat.json` -- readable transcript (Stop hook with `--chat` flag)
- `transcript_backups/` -- timestamped backups before compaction

**Config change auditing** (Anthropic official)

```json
{
  "ConfigChange": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "jq -c '{timestamp: now | todate, source: .source, file: .file_path}' >> ~/claude-config-audit.log"
        }
      ]
    }
  ]
}
```

### 2.6 Stop Hooks -- Verification Before Completion

**Prompt-based completeness check** (Anthropic official)

```json
{
  "Stop": [
    {
      "hooks": [
        {
          "type": "prompt",
          "prompt": "Check if all tasks are complete. If not, respond with {\"ok\": false, \"reason\": \"what remains to be done\"}."
        }
      ]
    }
  ]
}
```

**Agent-based test verification** (Anthropic official)

```json
{
  "Stop": [
    {
      "hooks": [
        {
          "type": "agent",
          "prompt": "Verify that all unit tests pass. Run the test suite and check the results. $ARGUMENTS",
          "timeout": 120
        }
      ]
    }
  ]
}
```

**Combined quality gate** (aiorg.dev)

```json
{
  "Stop": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/verify-tests.sh"
        },
        {
          "type": "prompt",
          "prompt": "Check if the implementation matches what the user asked for. Are there any edge cases missed?",
          "timeout": 30
        }
      ]
    }
  ]
}
```

Important: Stop hooks must check `stop_hook_active` to prevent infinite loops:

```bash
INPUT=$(cat)
if [ "$(echo "$INPUT" | jq -r '.stop_hook_active')" = "true" ]; then
  exit 0  # Allow Claude to stop
fi
```

### 2.7 Custom Permission Policies

**Auto-approve read-only tools** (aiorg.dev)

```json
{
  "PreToolUse": [
    {
      "matcher": "Read|Glob|Grep",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'echo \"{\\\"hookSpecificOutput\\\":{\\\"hookEventName\\\":\\\"PreToolUse\\\",\\\"permissionDecision\\\":\\\"allow\\\"}}\"'"
        }
      ]
    }
  ]
}
```

**Block web access in offline mode** (aiorg.dev)

```json
{
  "PreToolUse": [
    {
      "matcher": "WebFetch|WebSearch",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'echo \"Web access disabled by project policy\" >&2; exit 2'"
        }
      ]
    }
  ]
}
```

**MCP rate limiting** (aiorg.dev)

```bash
#!/bin/bash
INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')
LOGFILE="$CLAUDE_PROJECT_DIR/.claude/mcp-rate.log"

RECENT=$(grep -c "$TOOL" "$LOGFILE" 2>/dev/null || echo 0)
echo "$(date +%s) $TOOL" >> "$LOGFILE"

if [ "$RECENT" -gt 10 ]; then
  echo "Rate limit: $TOOL called $RECENT times in the last minute" >&2
  exit 2
fi
exit 0
```

### 2.8 Pre-PR Test Gate

**Block PR creation if tests fail** (Steve Kinney)

```json
{
  "PreToolUse": [
    {
      "matcher": "mcp__github__create_pull_request",
      "hooks": [
        {
          "type": "command",
          "command": ".claude/hooks/pre-pr-requires-tests.sh"
        }
      ]
    }
  ]
}
```

---

## 3. Status Line Configurations

Source: [Official statusline docs](https://code.claude.com/docs/en/statusline)

### How It Works

The statusline script receives JSON on stdin with fields: `model`, `context_window.remaining_percentage`, `context_window.total_read`, `context_window.total_write`, `cwd`, and more. The script outputs text (with ANSI color codes supported) that appears at the bottom of the Claude Code terminal.

### Athanor's Current Statusline

```bash
#!/bin/bash
input=$(cat)
model=$(echo "$input" | jq -r '.model // "unknown"')
ctx_pct=$(echo "$input" | jq -r '.context_window.remaining_percentage // empty')
input_tok=$(echo "$input" | jq -r '.context_window.total_read // 0')
output_tok=$(echo "$input" | jq -r '.context_window.total_write // 0')
cwd=$(echo "$input" | jq -r '.cwd // empty')
cost=$(echo "scale=2; ($input_tok * 15 + $output_tok * 75) / 1000000" | bc 2>/dev/null || echo "0")
branch=""
if [ -n "$cwd" ] && [ -d "$cwd/.git" ]; then
  branch=$(git -C "$cwd" branch --show-current 2>/dev/null)
fi
parts=()
[ -n "$model" ] && parts+=("$model")
[ -n "$ctx_pct" ] && parts+=("ctx:${ctx_pct}%")
[ "$cost" != "0" ] && [ "$cost" != "0.00" ] && parts+=("\$${cost}")
[ -n "$branch" ] && parts+=("$branch")
IFS=' | '
echo "${parts[*]}"
```

### Notable Third-Party Status Lines

**ccstatusline** (github.com/sirmalloc/ccstatusline)
- Powerline-style rendering with arrow separators
- Multi-line support, interactive TUI for configuration
- npm install: `npx ccstatusline`

**claude-powerline** (github.com/Owloops/claude-powerline)
- vim-style powerline with real-time usage tracking
- Git integration, custom themes

**ccusage statusline** (ccusage.com)
- Session cost, daily total cost, burn rate
- Block details for current session

### Comprehensive Statusline Example (aihero.dev)

```bash
#!/bin/bash
input=$(cat)
cwd=$(echo "$input" | sed -n 's/.*"current_dir":"\([^"]*\)".*/\1/p')

if git -C "$cwd" rev-parse --git-dir > /dev/null 2>&1; then
  repo_name=$(echo "$cwd" | sed "s|^$HOME/repos/||")
  branch=$(git -C "$cwd" --no-optional-locks rev-parse --abbrev-ref HEAD 2>/dev/null)
  staged=$(git -C "$cwd" --no-optional-locks diff --cached --name-only 2>/dev/null | wc -l)
  unstaged=$(git -C "$cwd" --no-optional-locks diff --name-only 2>/dev/null | wc -l)
  untracked=$(git -C "$cwd" --no-optional-locks ls-files --others --exclude-standard 2>/dev/null | wc -l)

  printf '\033[01;36m%s\033[00m | \033[01;32m%s\033[00m | S: \033[01;33m%s\033[00m | U: \033[01;33m%s\033[00m | A: \033[01;33m%s\033[00m' \
    "$repo_name" "$branch" "$staged" "$unstaged" "$untracked"
fi
```

Performance tip: Cache git info to a temp file and refresh every 5 seconds. `--no-optional-locks` prevents git from blocking on repo access.

---

## 4. Permission Configuration

### Three-Tier Evaluation Order

Deny -> Ask -> Allow. First match wins. Deny always takes precedence.

### Complete Permission Syntax

```
Bash(command_prefix:*)     -- Match bash commands by prefix
Read(glob_pattern)         -- Match file reads
Write(glob_pattern)        -- Match file writes
Edit(glob_pattern)         -- Match file edits
WebFetch(domain:example.com) -- Match web fetches by domain
mcp__server__tool(*)       -- Match MCP tool calls
```

### Recommended Security Configuration

```json
{
  "permissions": {
    "allow": [
      "Bash(npm run lint)",
      "Bash(npm run test *)",
      "Bash(git status)",
      "Bash(git diff *)",
      "Bash(git log *)"
    ],
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)",
      "Read(~/.ssh/**)",
      "Bash(rm -rf *)",
      "Bash(git push --force *)",
      "Bash(curl *)",
      "Bash(wget *)"
    ]
  }
}
```

### Known Limitation (Critical)

GitHub issue #6699 reports that deny permissions in settings.json are not reliably enforced in all versions. The recommended workaround is to use PreToolUse hooks for critical protections, as hooks are deterministic and always execute. Our existing `pre-tool-use-protect-paths.sh` follows this pattern correctly.

### Sandbox Configuration

```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "network": {
      "allowedDomains": ["github.com", "*.npmjs.org"],
      "allowLocalBinding": false
    }
  }
}
```

Sandbox uses bubblewrap on Linux, seatbelt on macOS. Restricts filesystem access outside project directory and blocks network except allowed domains.

---

## 5. CI/CD Integration

### GitHub Actions (Official)

Source: [claude-code-action](https://github.com/anthropics/claude-code-action)

```yaml
name: Claude Code Review
on:
  pull_request:
    types: [opened, synchronize]
  issue_comment:
    types: [created]

jobs:
  claude-review:
    if: |
      github.event_name == 'pull_request' ||
      (github.event_name == 'issue_comment' && contains(github.event.comment.body, '@claude'))
    runs-on: ubuntu-latest
    steps:
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

Setup: Run `/install-github-app` inside Claude Code terminal.

### Code Review Plugin

```json
{
  "enabledPlugins": {
    "code-review@claude-plugins-official": true
  }
}
```

Multi-agent parallel review: launches specialized agents to audit from different perspectives (security, performance, style). Uses confidence scoring to filter false positives.

### Headless Mode for Pipelines

```bash
# Run a one-shot task
claude -p "Review the changes in this PR and suggest improvements" \
  --output-format stream-json

# With permission bypass for CI
claude -p "Fix all TypeScript errors" \
  --permission-mode bypassPermissions
```

### GitLab CI/CD

Built on Claude Code CLI and Agent SDK. Same `-p` flag pattern.

### Automation Stats (2026)

- Teams using Claude Code for automated review report ~40% reduction in review time
- 60%+ of enterprise teams using Claude Code leverage headless mode for at least one CI/CD workflow

---

## 6. Notable GitHub Repositories for Hooks

| Repository | Stars | Description |
|-----------|-------|-------------|
| [disler/claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery) | -- | 13 hook types with Python scripts for all events |
| [decider/claude-hooks](https://github.com/decider/claude-hooks) | -- | Code quality validator, package age checker, Pushover notifications |
| [tihomiro/claude-code-boilerplate](https://github.com/tihomiro/claude-code-boilerplate) | -- | Full logging suite, TTS notifications (ElevenLabs/OpenAI/pyttsx3), session transcripts |
| [johnlindquist/claude-hooks](https://github.com/johnlindquist/claude-hooks) | -- | TypeScript hooks via `npx claude-hooks`, typed payloads |
| [ZacheryGlass/.claude](https://github.com/ZacheryGlass/.claude) | -- | Emoji remover, clean commit guard, GitHub issue guard, protect CLAUDE.md |
| [tarekziade/claude-tools](https://github.com/tarekziade/claude-tools) | -- | Hooks and tools collection |
| [bartolli/claude-code-typescript-hooks](https://github.com/bartolli/claude-code-typescript-hooks) | -- | TypeScript-native hook handlers |
| [777genius/claude-notifications-go](https://github.com/777genius/claude-notifications-go) | -- | Go-based cross-platform notifications, 6 types, click-to-focus, webhooks |
| [ChanMeng666/claude-code-audio-hooks](https://github.com/ChanMeng666/claude-code-audio-hooks) | -- | Audio notification system with different sounds per event |

---

## 7. devenv.nix Integration

Source: [devenv.sh/integrations/claude-code](https://devenv.sh/integrations/claude-code/)

```nix
{
  claude.code.enable = true;
  git-hooks.hooks = {
    rustfmt.enable = true;
    nixfmt.enable = true;
    black.enable = true;
    prettier.enable = true;
  };
}
```

Auto-generates `.mcp.json` for Claude Code. Supports custom hooks, commands, agents, and MCP servers declaratively in Nix.

---

## 8. Patterns Not Yet in Athanor (Gap Analysis)

### High Value -- Should Adopt

| Pattern | What It Does | Effort |
|---------|-------------|--------|
| **Bash command firewall** | Block `rm -rf /`, `git reset --hard`, `DROP TABLE`, `--force` push | Low -- add deny patterns to existing PreToolUse |
| **Secrets guard** | Block read/write of `.env*`, `secrets/`, credentials files | Low -- extend protect-paths.sh |
| **PostToolUse auto-format (EoQ)** | Run prettier on EoQ .ts/.tsx edits | Low -- clone typecheck pattern |
| **Stop hook infinite loop guard** | Check `stop_hook_active` in autocommit | Low -- one-line addition |
| **Session audit log** | Append timestamped bash commands to `.claude/bash-commands.log` | Low -- new PostToolUse |
| **Notification sound** | Play audio on permission_prompt/idle_prompt via paplay or similar | Low -- extend existing Notification hook |
| **MCP audit log** | Track all MCP tool invocations (Grafana, agents, context7) | Low -- new PostToolUse with `mcp__.*` matcher |

### Medium Value -- Consider

| Pattern | What It Does | Effort |
|---------|-------------|--------|
| **Prompt-based Stop verification** | LLM checks if task is truly complete before stopping | Medium -- needs testing to avoid false blocks |
| **Auto-refresh context every N prompts** | Re-inject critical context (tool reminders, project rules) periodically | Medium -- needs TypeScript/Bun or Python |
| **Package manager enforcement** | Block `npm` in projects using `pnpm` | Low but niche |
| **ConfigChange auditing** | Log any settings/skills file modifications | Low |
| **Enhanced statusline** | Add git staged/unstaged/untracked counts, use ANSI colors, cache git info | Medium |
| **SessionEnd cleanup** | Remove temp files on session clear | Low |

### Low Value for Athanor -- Skip

| Pattern | Why Skip |
|---------|----------|
| Auto-commit every edit | Too noisy for a single-operator repo |
| TTS notifications | WSL2 audio is unreliable; Athanor uses push notifications via agent framework |
| Agent-based Stop verification | Token cost for every stop event; overkill for homelab |
| Dependency install gate | Not a large-team concern |
| Rate limiting MCP tools | No abuse vector in single-user setup |

---

## 9. Recommendations for Athanor

### Immediate (next session)

1. **Add bash command firewall to PreToolUse** -- extend `pre-tool-use-protect-paths.sh` to also intercept Bash tool calls and block `rm -rf /`, `git push --force`, `git reset --hard`, `DROP TABLE`.

2. **Add secrets guard** -- extend protect-paths to also block `.env*`, `vault-password`, `*credentials*`, `*secret*` file access.

3. **Add `stop_hook_active` guard** -- prevent potential infinite loop in `stop-autocommit.sh`.

4. **Add EoQ PostToolUse formatting** -- run prettier on EoQ project edits (same pattern as typecheck).

### Short-term (this week)

5. **Bash command audit log** -- PostToolUse on Bash, append timestamped commands to `.claude/bash-commands.log`. Useful for debugging and understanding what Claude ran.

6. **Enhance statusline** -- add ANSI colors, staged/unstaged counts, use `--no-optional-locks` for git operations to prevent hangs, cache results to avoid performance issues.

7. **MCP tool audit** -- PostToolUse on `mcp__.*`, log to `.claude/mcp-audit.log`. Helps understand agent and Grafana tool usage patterns.

### Medium-term

8. **Periodic context refresh** -- UserPromptSubmit hook that re-injects critical reminders every 5 prompts (build principles, current sprint, tool availability).

9. **ConfigChange monitoring** -- log when settings/skills change during session.

10. **Prompt-based Stop hook** -- experiment with a lightweight completeness check using Haiku. Only enable for `/build` mode sessions where work verification matters.

---

## Sources

### Official Documentation
- [Hooks reference](https://code.claude.com/docs/en/hooks) -- Complete event schemas and JSON formats
- [Hooks guide](https://code.claude.com/docs/en/hooks-guide) -- Setup walkthrough and examples
- [Permissions](https://code.claude.com/docs/en/permissions) -- Permission system documentation
- [Settings reference](https://code.claude.com/docs/en/settings) -- Full settings.json schema
- [Statusline](https://code.claude.com/docs/en/statusline) -- Status line customization
- [GitHub Actions](https://code.claude.com/docs/en/github-actions) -- CI/CD integration
- [GitLab CI/CD](https://code.claude.com/docs/en/gitlab-ci-cd) -- GitLab integration

### Blog Posts & Guides
- [Steve Kinney: Claude Code Hook Examples](https://stevekinney.com/courses/ai-development/claude-code-hook-examples) -- 7 practical hook scripts
- [aiorg.dev: 20+ Ready-to-Use Examples](https://aiorg.dev/blog/claude-code-hooks) -- Comprehensive hook catalog
- [d12frosted.io: Claude Code Notifications](https://www.d12frosted.io/posts/2026-01-05-claude-code-notifications) -- macOS notification setup with sounds
- [aihero.dev: Creating the Perfect Status Line](https://www.aihero.dev/creating-the-perfect-claude-code-status-line) -- Git-rich statusline
- [Pixelmojo: Production CI/CD Patterns](https://www.pixelmojo.io/blogs/claude-code-hooks-production-quality-ci-cd-patterns) -- Security gates and prompt hooks
- [Letanure: Automated Quality Checks](https://www.letanure.dev/blog/2025-08-06--claude-code-part-8-hooks-automated-quality-checks) -- TypeScript-specific hooks
- [claudefa.st: Settings Reference](https://claudefa.st/blog/guide/settings-reference) -- Complete config guide
- [Pete Freitag: Permissions](https://www.petefreitag.com/blog/claude-code-permissions/) -- Permission configuration
- [alexop.dev: Notification Hooks](https://alexop.dev/posts/claude-code-notification-hooks/) -- Cross-platform notification setup
- [devenv.sh: Claude Code Integration](https://devenv.sh/integrations/claude-code/) -- Nix-based declarative setup

### GitHub Repositories
- [anthropics/claude-code-action](https://github.com/anthropics/claude-code-action) -- Official GitHub Actions integration
- [anthropics/claude-code-security-review](https://github.com/anthropics/claude-code-security-review) -- Security review action
- [disler/claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery) -- 13 hook types reference implementation
- [tihomiro/claude-code-boilerplate](https://github.com/tihomiro/claude-code-boilerplate) -- Full logging, TTS, security boilerplate
- [johnlindquist/claude-hooks](https://github.com/johnlindquist/claude-hooks) -- TypeScript hooks with typed payloads
- [decider/claude-hooks](https://github.com/decider/claude-hooks) -- Code quality + Pushover notifications
- [doobidoo: Universal Permission Hook](https://gist.github.com/doobidoo/fa84d31c0819a9faace345ca227b268f) -- Auto-approve safe MCP tools
- [ZacheryGlass/.claude](https://github.com/ZacheryGlass/.claude) -- Emoji remover, commit guard, issue guard
- [sirmalloc/ccstatusline](https://github.com/sirmalloc/ccstatusline) -- Powerline statusline
- [Owloops/claude-powerline](https://github.com/Owloops/claude-powerline) -- Vim-style powerline
- [John Lindquist: Auto-Refresh Context](https://gist.github.com/johnlindquist/23fac87f6bc589ddf354582837ec4ecc) -- Context injection every N prompts

### Issues & Known Limitations
- [#6699: deny permissions not enforced](https://github.com/anthropics/claude-code/issues/6699) -- Use PreToolUse hooks instead
- [#10373: SessionStart hooks not working for new conversations](https://github.com/anthropics/claude-code/issues/10373)
- [#15840: CLAUDE_ENV_FILE not provided to SessionStart hooks](https://github.com/anthropics/claude-code/issues/15840)
- [#12117: SessionStart hook not injecting prompt](https://github.com/anthropics/claude-code/issues/12117)
