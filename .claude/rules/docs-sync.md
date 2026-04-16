---
paths:
  - "docs/**"
  - "ansible/**"
  - "projects/**"
  - "CLAUDE.md"
  - "STATUS.md"
---

# Documentation Sync

After any operational change, update all affected docs atomically when the change is actually being published. Generated reports, the restart brief, finish scoreboard, and runtime packet inbox still outrank narrative doc edits for current mutable state.

## After Deploying a Service
- `docs/SERVICES.md` - add or update entry
- `docs/SYSTEM-SPEC.md` - update service inventory
- `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md` - update the live execution order if priorities changed
- `STATUS.md` - update cluster state

## After GPU Reassignment
- `config/automation-backbone/hardware-inventory.json` - active hardware truth
- `docs/operations/HARDWARE-REPORT.md` - regenerate the summary after inventory changes
- `docs/archive/hardware/hardware-inventory.md` - update only if the historical owned-hardware ledger itself changed
- `.claude/rules/vllm.md` - update deployment section
- `.claude/skills/gpu-placement.md` - update placement table
- `docs/SYSTEM-SPEC.md` - update model inventory table

## After Model Swap
- Grep all references to old model name: `grep -rn "old-model" .`
- Update: LiteLLM config, vLLM args, SYSTEM-SPEC, SERVICES, MEMORY.md
- One commit for all changes

## After Port Change
- Grep all references: `grep -rn ":old_port" .`
- Update: Ansible vars, docker-compose, SERVICES.md, SYSTEM-SPEC.md, firewall rules
- One commit for all changes

## Validation
- `python3 scripts/check-doc-refs.py` - finds broken internal links
- Manual: grep for the changed value across entire repo
