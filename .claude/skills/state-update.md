---
name: State Update
description: How to update Athanor state files after infrastructure or documentation changes.
---

# State Update

How to update Athanor state files after any change to infrastructure, services, or documentation.

## Files to Update

| File | What It Tracks | When to Update |
|------|---------------|----------------|
| `CLAUDE.md` | Role, hardware, services, state, gotchas, blockers | When services, state, or blockers change |
| `docs/BUILD-MANIFEST.md` | Executable build plan with priorities | When tasks complete or new ones are added |
| `docs/SYSTEM-SPEC.md` | Complete operational specification | When architecture, services, or agents change |
| `docs/SERVICES.md` | Live service inventory | When services are deployed, removed, or change ports |
| `docs/VISION.md` | High-level vision and current state | When major milestones change |
| `docs/hardware/inventory.md` | Hardware allocation and specs | When hardware moves between nodes |
| `docs/design/agent-contracts.md` | Agent behavior contracts | When agent tools, escalation, or boundaries change |
| `docs/design/intelligence-layers.md` | Intelligence layer status | When layers are deployed or extended |
| `MEMORY.md` (auto-memory) | Session continuity, patterns, decisions | After every session with significant findings |

## Process

1. After any infrastructure change (deploy, config, hardware, agent):
   - Identify which state files are affected
   - Update the specific sections that changed
   - Update timestamps where present ("Last updated: YYYY-MM-DD")
   - Keep descriptions consistent across files (don't say "8 agents" in one and "7" in another)

2. For CLAUDE.md specifically:
   - Update the Current State section if services/state changed
   - Update Blockers table if items were resolved or new ones found
   - Update Hardware table if hardware changed
   - Update Key Gotchas if new gotchas were discovered

3. For auto-memory (MEMORY.md):
   - Update build progress
   - Record new patterns, corrections, or gotchas
   - Keep within 200-line limit (lines after 200 are truncated at session start)

## Commit Convention

```bash
git add CLAUDE.md docs/BUILD-MANIFEST.md docs/SYSTEM-SPEC.md  # stage what changed
git commit -m "state: {what changed}"
```

Prefix with `state:` for tracking updates. Use specific descriptions ("state: vLLM upgraded to v0.16.0", not "state: update docs").
