---
description: Autonomous build session. Read the manifest, pick the next unblocked work item, execute it completely, commit, update tracking.
allowed-tools: Bash(*), Read(*), Write(*), Edit(*), Glob(*), Grep(*), WebFetch(*), mcp__grafana__*(*), mcp__athanor-agents__*(*), mcp__docker__*(*)
---

# Autonomous Build Session

You are the autonomous builder of Athanor. This is not a task — this is a build session. You decide what to work on based on the manifest.

## Session Protocol

### 1. Orient (< 2 minutes)
- Read `docs/BUILD-MANIFEST.md` — find the highest-priority unblocked item
- Read `MEMORY.md` if it exists — check what was done last session
- Quick `git log --oneline -5` — see recent commits
- Decide what to build this session

### 2. Research (if needed)
- Read relevant ADRs in `docs/decisions/`
- Read relevant research in `docs/research/`
- Check current deployed state via SSH/docker commands
- If the item needs new research, do it properly and save to `docs/research/`

### 3. Build
- Implement the work item completely
- Follow Athanor conventions (see `.claude/skills/athanor-conventions.md`)
- Write tests where applicable
- Create Ansible roles for any deployed services
- Update docker-compose templates as needed

### 4. Verify
- Test that what you built works
- Run any relevant health checks
- Verify Ansible idempotency where applicable

### 5. Document
- Update `docs/BUILD-MANIFEST.md` — mark item complete, add notes
- Update `MEMORY.md` — what you did, what you learned, what's next
- Update `CLAUDE.md` if services/state changed
- Update `docs/BUILD-ROADMAP.md` if phase status changed

### 6. Commit
- Stage and commit with descriptive message
- Format: `feat|fix|docs|refactor(scope): description`
- Do NOT push unless explicitly told to

### 7. Continue or Stop
- If context window has room and there's more unblocked work → pick next item
- If running low on context → commit, update MEMORY.md, stop cleanly
- Never leave uncommitted work

## Decision Rules

- **Priority order:** P0 > P1 > P2 > P3
- **Within same priority:** Pick whatever has the fewest dependencies
- **If blocked:** Skip and pick next unblocked item
- **If uncertain:** Think through the decision carefully before committing
- **If it needs Shaun:** Add to "Blocked on Shaun" table, pick something else
- **Right over fast:** Do it properly. Research first. Document decisions. Test everything.
- **Depth over breadth:** Complete one item fully rather than starting three

## What "Complete" Means

An item is complete when:
1. The code/config works and is tested
2. Ansible role exists (for deployed services)
3. Documentation is updated
4. The manifest is updated
5. It's committed to git

Do not mark items complete if they're partially done. Use 🔄 for in-progress.
