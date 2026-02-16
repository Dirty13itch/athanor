# Athanor Conventions

Code and configuration conventions for the Athanor project.

## Directory Structure

```
athanor/
├── CLAUDE.md              — Project instructions (read every session)
├── docs/
│   ├── VISION.md          — Source of truth
│   ├── BUILD-ROADMAP.md   — Build progress tracker
│   ├── research/          — YYYY-MM-DD-slug.md
│   ├── decisions/         — ADR-NNN-slug.md
│   ├── hardware/          — Audit results, inventory
│   └── projects/          — Per-project docs
├── projects/              — Project workspaces
├── scripts/               — Utility scripts
│   └── setup/             — Node bootstrap scripts
└── .claude/
    ├── settings.json      — Permissions
    ├── commands/           — Slash commands (skills)
    ├── skills/            — Skill reference docs
    └── hooks/             — Event hooks
```

## Infrastructure Layout on Nodes

```
/opt/athanor/              — All Athanor services on compute nodes
├── vllm/
│   └── docker-compose.yml
├── comfyui/
│   └── docker-compose.yml
├── monitoring/
│   └── docker-compose.yml
└── {service}/
    └── docker-compose.yml

/mnt/vault/                — NFS mounts from VAULT
├── models/                — AI model storage
├── data/                  — Media and data
└── appdata/               — Application config
```

## Naming Conventions

- **Containers**: lowercase, hyphen-separated: `vllm`, `comfyui`, `node-exporter`
- **Compose projects**: match directory name under /opt/athanor/
- **Research docs**: `YYYY-MM-DD-slug.md`
- **ADRs**: `ADR-NNN-slug.md` (sequential, never delete)
- **Scripts**: descriptive, hyphen-separated: `vault-ssh.py`, `post-install-audit.sh`

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
- Pin image tags in production (not `:latest`)

## Git Conventions

- Commit messages: imperative, concise, describe the "what"
- State file updates: prefix with "State: "
- ADR commits: "ADR-NNN: {title}"
- Research commits: "Research: {topic}"
- Infrastructure commits: "Deploy: {service} on {node}" or "Config: {what changed}"

## Network Conventions

- Services bind `0.0.0.0` for cross-node access
- Use SSH config aliases (`node1`, `node2`, `vault`) not raw IPs
- Standard ports documented in each service's skill/ADR
- No reverse proxy yet — direct port access

## Security

- No secrets in git (use environment variables or Docker secrets)
- SSH key auth only (no passwords in scripts — vault-ssh.py is the exception for Unraid dropbear)
- VAULT root password is in MEMORY.md only (not committed)
