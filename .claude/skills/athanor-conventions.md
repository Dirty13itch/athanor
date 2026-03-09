---
name: Athanor Conventions
description: Code, configuration, and operational conventions for the Athanor project.
---

# Athanor Conventions

Code and configuration conventions. Follow these when building anything for Athanor.

## Directory Structure

```
athanor/
├── CLAUDE.md              — Project instructions, role, state, gotchas
├── docs/
│   ├── VISION.md          — Source of truth (what and why)
│   ├── SYSTEM-SPEC.md     — Complete operational specification
│   ├── BUILD-MANIFEST.md  — Executable build plan with priorities
│   ├── SERVICES.md        — Live service inventory
│   ├── research/          — YYYY-MM-DD-slug.md
│   ├── decisions/         — ADR-NNN-slug.md
│   ├── design/            — Implementation specs (agent-contracts, intelligence-layers, etc.)
│   ├── hardware/          — Inventory, audits, specs
│   └── projects/          — Per-project docs
├── ansible/               — Single Ansible IaC tree (inventory, roles, playbooks, vault)
├── projects/              — Project workspaces (agents, dashboard, eoq, gpu-orchestrator)
├── scripts/               — Utility scripts (vault-ssh.py, index-knowledge.py, build-profile.sh)
└── .claude/
    ├── settings.json      — Plugin config
    ├── settings.local.json— Permissions, MCP, sandbox
    ├── commands/           — Slash commands (/orient, /build, /status, /research, /decide)
    ├── skills/            — Skill reference docs (auto-invoked by description matching)
    └── hooks/             — Event hooks (SessionStart, Stop, PreCompact, PreToolUse)
```

## Infrastructure Layout on Nodes

```
/opt/athanor/              — All Athanor services on compute nodes
├── vllm/                  — vLLM inference (custom build, v0.16.0)
├── agents/                — Agent server (LangGraph + LiteLLM)
├── comfyui/               — Creative pipeline (Flux + Wan2.x)
├── dashboard/             — Command Center (Next.js PWA)
├── gpu-orchestrator/      — GPU zone management
├── monitoring/            — node-exporter + dcgm-exporter
├── voice/                 — wyoming-whisper + Speaches
└── {service}/
    └── docker-compose.yml

/mnt/vault/                — NFS mounts from VAULT
├── models/                — AI model storage (~200 GB)
├── data/                  — Media and data (backups, adult, etc.)
└── system/                — System configs shared across nodes
```

## Naming Conventions

- **Containers**: lowercase, hyphen-separated: `vllm`, `comfyui`, `node-exporter`
- **Compose projects**: match directory name under /opt/athanor/
- **Research docs**: `YYYY-MM-DD-slug.md` (date of research, not publication)
- **ADRs**: `ADR-NNN-slug.md` (sequential, never delete, never renumber)
- **Scripts**: descriptive, hyphen-separated: `vault-ssh.py`, `build-profile.sh`
- **Nodes**: Foundry (Node 1, .244), Workshop (Node 2, .225), VAULT (.203), DEV (.189)
- **Agents**: lowercase, hyphen-separated: `general-assistant`, `media-agent`, `stash-agent`

## Docker Compose Standards

- Always include `restart: unless-stopped`
- Always include `container_name:` (explicit naming)
- Always include log rotation:
  ```yaml
  logging:
    driver: json-file
    options:
      max-size: "50m"
      max-file: "3"
  ```
- Set `TZ=America/Chicago` for all containers
- Use health checks for services with HTTP endpoints
- Pin image tags in production (not `:latest` unless tracking upstream)
- GPU services: include `ipc: host`, `ulimits: memlock: -1`

## Git Conventions

- Commit messages: imperative mood, concise, describe the "what"
- Prefixes: `feat:`, `fix:`, `docs:`, `state:`, `refactor:`, `deploy:`, `config:`
- State file updates: `state: {what changed}`
- ADR commits: `docs: ADR-NNN {title}`
- Research commits: `docs: research {topic}`
- Infrastructure commits: `deploy: {service} on {node}` or `config: {what changed}`
- Co-author line on all Claude-assisted commits:
  `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`

## Network Conventions

- Services bind `0.0.0.0` for cross-node access
- Use SSH config aliases (`node1`, `node2`, `vault`) not raw IPs
- 10GbE for data plane, 1GbE for management
- MTU 9000 (jumbo frames) on all server 10GbE NICs
- Standard ports documented in `docs/SERVICES.md`
- No reverse proxy yet — direct port access

## Security

- No secrets in git (use environment variables or Ansible vault)
- SSH key auth only (no passwords in scripts — `vault-ssh.py` is the exception for Unraid dropbear)
- MCP server credentials via env vars (not hardcoded in `.mcp.json`)
- Protected paths enforced by PreToolUse hook
