# State Update

How to update Athanor state files after infrastructure changes.

## Files to Update

| File | What It Tracks | When to Update |
|------|---------------|----------------|
| `docs/BUILD-ROADMAP.md` | Phase checklist | When tasks are completed or added |
| `docs/VISION.md` (Current State) | High-level system state | When major milestones change |
| `docs/hardware/inventory.md` | Hardware allocation | When hardware moves between nodes |
| `MEMORY.md` | Session-persistent state | When IPs, credentials, or status changes |

## Process

1. After any infrastructure change (deploy, config, hardware):
   - Identify which state files are affected
   - Update the specific sections that changed
   - Use checkboxes `[x]` in BUILD-ROADMAP.md for completed items
   - Update timestamps ("Last updated: YYYY-MM-DD")

2. For MEMORY.md (auto memory):
   - Update the "Build Phase Status" section
   - Update "Next Priorities" if the queue changed
   - Add new gotchas discovered during work

3. Commit state file changes:
   ```bash
   git add docs/BUILD-ROADMAP.md docs/VISION.md
   git commit -m "Update state: {what changed}"
   ```

## State File Locations

```
C:\Users\Shaun\athanor\docs\BUILD-ROADMAP.md     — Build progress
C:\Users\Shaun\athanor\docs\VISION.md             — System overview
C:\Users\Shaun\athanor\docs\hardware\inventory.md — Hardware
C:\Users\Shaun\.claude\projects\C--Users-Shaun-athanor\memory\MEMORY.md — Auto memory
```

## Example: After Deploying vLLM on Node 1

1. BUILD-ROADMAP.md: Check off `[x] Deploy vLLM on Node 1 — single GPU test first`
2. VISION.md Current State: Add "vLLM running on Node 1"
3. MEMORY.md: Update "Build Phase Status" with vLLM details
4. Commit: `git commit -m "State: vLLM deployed on Node 1"`
