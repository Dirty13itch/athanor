# Athanor Dev Stack — How to Use Everything

## Quick Access Points

| What | URL/Command | From Where |
|------|-------------|------------|
| **Open WebUI** (chat with any model, uncensored) | http://192.168.1.189:3080 | Any browser on LAN |
| **Command Center UI** (system dashboard) | http://192.168.1.189:3001 | Any browser on LAN |
| **Claude Code** (primary coding agent) | `ssh dev` then `claude` | Any terminal |
| **VS Code Remote** (IDE with AI extensions) | VS Code > Remote-SSH > dev | DESK |
| **Governor** (task queue + agent dispatch) | http://192.168.1.189:8760 | API or browser |
| **Arize Phoenix** (agent tracing) | http://192.168.1.189:6006 | Any browser |
| **Grafana** (monitoring dashboards) | http://192.168.1.203:3000 | Any browser |
| **OpenFang** (phone/Telegram control) | http://192.168.1.189:4200 | Browser or Telegram |
| **ttyd** (web terminal) | http://192.168.1.189:7681 | Steam Deck browser |

## Daily Workflow

### Starting Your Day
1. SSH into DEV: `ssh dev`
2. Check system health: `bash ~/repos/athanor/scripts/drift-check.sh`
3. Check overnight work: `git log --all --oneline --since="12 hours ago"`
4. Review governor queue: `curl -s http://localhost:8760/status | python3 -m json.tool`
5. Open VS Code with Remote-SSH to DEV for editing

### Interactive Coding (you at keyboard)
**Claude Code** (hardest problems, architecture):
```bash
cd ~/repos/athanor
claude  # starts Claude Code with Opus 4.6, 1M context
```

**aider** (pair programming, clean git commits):
```bash
cd ~/repos/athanor
aider  # uses local Qwen3.5-27B via LiteLLM, free
```

**OpenCode** (local models, parallel agents):
```bash
cd ~/repos/athanor
opencode  # 75+ providers, /multi for parallel agents
```

**Goose** (system automation, infra tasks):
```bash
goose  # MCP-native, recipes for repeatable workflows
```

### VS Code AI Extensions
Open VS Code, Remote-SSH to DEV:
- **Cline** (agentic editing): Open command palette > Cline > type your request
- **Continue.dev** (autocomplete): Just type — Tab completions from local Qwen 2.5 Coder 7B
- **Copilot** (inline suggestions): Cloud-powered suggestions alongside local

### Uncensored / Sovereign Chat
Open http://192.168.1.189:3080 (Open WebUI)
- Select model "uncensored" or "creative" from dropdown
- These route to the abliterated Qwen3.5-35B on WORKSHOP — no content restrictions
- Safe coding queries automatically route to cloud models (Claude/GPT) for best quality

### Content-Aware Routing (automatic)
The classifier at :8740 categorizes every request:
- **Safe** (coding, docs, analysis) -> Cloud models (best quality)
- **Unsafe** (NSFW, adult, controversial) -> Local abliterated model (no refusals)
- You dont need to think about this — it happens automatically via LiteLLM

## Autonomous Coding (agents work while you sleep)

### Add Tasks to the Governor Queue
```bash
# Add a single task
curl -X POST http://localhost:8760/tasks \
  -H "Content-Type: application/json" \
  -d {title: Add unit tests for Gateway, description: Write pytest tests for /health, /v1/chat, /v1/models endpoints, repo: athanor, complexity: medium}

# Add multiple tasks
curl -X POST http://localhost:8760/queue/batch \
  -H "Content-Type: application/json" \
  -d [{title: Fix lint errors in scripts/, description: Run ruff check and fix all auto-fixable issues, repo: athanor, complexity: low}, {title: Add API docs to Memory service, description: Add OpenAPI docstrings to all endpoints, repo: athanor, complexity: low}]
```

### Dispatch Tasks to Agents
```bash
# Auto-assign and launch (creates git worktree + tmux session)
curl -X POST http://localhost:8760/dispatch-and-run

# Check what agents are doing
curl http://localhost:8760/agents | python3 -m json.tool

# Check logs for a task
curl http://localhost:8760/logs/task-0001 | python3 -m json.tool
```

### Overnight Pipeline
- **10pm**: Governor automatically dispatches queued tasks to subscription agents
- **7am**: Morning summary sent via ntfy with overnight results
- **You**: Review PRs in the morning, merge what looks good

### Which Subscription Handles What
| Subscription | Agent | Best For |
|-------------|-------|----------|
| Claude Max ($200) | `claude` | Architecture, complex features, debugging |
| ChatGPT Pro ($200) | `codex` | Cloud sandbox tasks, well-scoped features |
| Copilot Pro+ ($39) | `copilot` | Unlimited routine work (GPT-5 mini = free) |
| Kimi Code ($19) | `kimi` | 100-agent batch swarms |
| GLM Z.ai ($30) | LiteLLM | Agent chains, overflow |
| Gemini Adv ($20) | `gemini` | 1M context analysis, planning |

## Monitoring & Debugging

### Quick Health Check
```bash
bash ~/repos/athanor/scripts/drift-check.sh  # 39 service checks
```

### Service Logs
```bash
sudo journalctl -u local-system-gateway -f     # Gateway
sudo journalctl -u athanor-classifier -f        # Content classifier
sudo journalctl -u athanor-governor -f          # Governor
docker logs -f open-webui                       # Open WebUI
docker logs -f vllm-embedding                   # Embedding model
```

### GPU Status
```bash
nvidia-smi                                       # DEV GPU
ssh foundry nvidia-smi                           # FOUNDRY GPUs
ssh workshop nvidia-smi                          # WORKSHOP GPUs
```

### Model Endpoints
```bash
# Coordinator (Qwen3.5-27B, TP=4)
curl http://192.168.1.244:8000/v1/models

# Coder (Devstral Small 2, 4090)
curl http://192.168.1.244:8006/v1/models

# Sovereign brain (abliterated, 5090)
curl http://192.168.1.225:8010/v1/models

# FIM autocomplete (Ollama, 5060 Ti)
curl http://192.168.1.225:11434/api/tags

# All models via LiteLLM
LKEY=$(cat ~/.secrets/litellm-master-key)
curl -H "Authorization: Bearer $LKEY" http://192.168.1.203:4000/v1/models
```

## Shell Tools (all configured in .bashrc)
```bash
ls          # eza with icons
cat file    # bat with syntax highlighting
cd dir      # zoxide (smart jump: z dirname)
Ctrl-R      # fzf fuzzy history search (atuin-powered)
lazygit     # TUI git client
lazydocker  # TUI Docker manager
btop        # system monitor
```

## Key Files & Configs
| File | Purpose |
|------|---------|
| `~/.claude/` | Claude Code config, hooks, agents, skills |
| `~/.secrets/` | All API keys and credentials |
| `~/repos/athanor/` | Main monorepo |
| `~/repos/athanor/scripts/drift-check.sh` | 39-check health verification |
| `~/repos/athanor/services/governor/` | Governor service + SQLite queue |
| `~/repos/athanor/services/classifier/` | Content classifier service |
| `~/repos/athanor/AGENTS.md` | Agent behavior spec (Linux Foundation) |
| `~/repos/athanor/.claude/agents/` | 9 Claude Code agent definitions |
| `~/.continue/config.json` | Continue.dev IDE config |
| `~/.config/goose/profiles.yaml` | Goose automation profiles |
