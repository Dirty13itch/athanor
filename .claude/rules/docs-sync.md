---
paths:
  - "docs/**"
  - "ansible/**"
  - "projects/**"
  - "CLAUDE.md"
  - "STATUS.md"
---

# Documentation Sync

After any operational change, update all affected docs atomically (same commit).

## After Deploying a Service
- `docs/SERVICES.md` — add/update entry
- `docs/SYSTEM-SPEC.md` — update service inventory
- `docs/BUILD-MANIFEST.md` — mark item complete if applicable
- `STATUS.md` — update cluster state

## After GPU Reassignment
- `docs/hardware/inventory.md` — update GPU allocation
- `.claude/rules/vllm.md` — update deployment section
- `.claude/skills/gpu-placement.md` — update placement table
- `docs/SYSTEM-SPEC.md` — update model inventory table

## After Model Swap
- Grep all references to old model name: `grep -rn "old-model" .`
- Update: LiteLLM config, vLLM args, SYSTEM-SPEC, SERVICES, MEMORY.md
- One commit for all changes

## After Port Change
- Grep all references: `grep -rn ":old_port" .`
- Update: Ansible vars, docker-compose, SERVICES.md, SYSTEM-SPEC.md, firewall rules
- One commit for all changes

## Validation
- `python3 scripts/check-doc-refs.py` — finds broken internal links
- Manual: grep for the changed value across entire repo
