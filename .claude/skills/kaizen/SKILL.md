---
name: kaizen
description: Perpetual improvement loop. Find the weakest part of the system and make it better. Never stops. Use when continuing work, when idle, when asked to improve, or when nothing specific is requested.
---

# Kaizen — The Perpetual Improvement Loop

*The furnace feeds itself. Every cycle makes the system stronger.*

## THE DEPTH MANDATE

**Models fail at depth.** They touch 50 things lightly instead of going deep on 3 things that matter. This is the single biggest failure mode on large complex projects.

The rule: **DEPTH OVER BREADTH. ALWAYS.**

- Don't audit 35 pages in one pass. Audit 3 pages DEEPLY — read every line, check every endpoint, test every interaction, fix every issue, deploy, verify.
- Don't list 20 things that could be better. Pick the 3 worst and FIX THEM COMPLETELY.
- Don't write a plan for 10 improvements. Build 2 improvements and ship them.
- Don't describe what should change. Change it. Verify it. Deploy it.

**Signs you're going too broad:**
- You're listing problems without fixing any
- You've been assessing for >15 minutes without building
- Your output is a report, not a commit
- You're touching >5 files without finishing any of them
- You said "could be improved" without improving it

**Signs you're at the right depth:**
- You read the entire file before changing it
- You checked the live endpoint after deploying
- You fixed an edge case you found while fixing the main issue
- Your commit message describes a specific fix, not a general "improvements"
- The thing you fixed is DONE — not 80% done, not "mostly working", DONE

**The depth spiral:** Fix one thing completely → that reveals a deeper issue → fix that completely → that reveals another → keep going until you hit bedrock. THAT is depth.

## The Loop

```
ASSESS → PRIORITIZE → BUILD → VERIFY → DEPLOY → MEASURE → LOOP
```

This is not a one-time audit. This is how Athanor operates. Every time you have capacity, every time there's a pause, every time someone says "continue" or "keep going" — run the loop.

## Step 1: ASSESS — Find the Weakest Link

Check these sources in order. The first one that reveals a problem is your target:

1. **Live errors** — `ssh foundry "curl -s -H 'Authorization: Bearer TOKEN' http://localhost:9000/v1/tasks?limit=5&status=failed"` — any recent failures?
2. **Service health** — `ssh foundry "curl -s http://localhost:9000/health"` — any deps down?
3. **User feedback** — Check gallery ratings for flagged/rejected images. Check task results for poor quality.
4. **Dashboard pages** — Curl each page, check for 500s, empty states, broken data.
5. **Code quality** — `npx tsc --noEmit` — any type errors? `grep -r "TODO\|FIXME\|HACK" src/` — any tech debt?
6. **Agent output quality** — Read the last 5 completed tasks. Are agents producing deep, useful work or shallow busywork?
7. **Generation quality** — Check ComfyUI output. Are images improving? Are faces accurate?
8. **Documentation drift** — Is STATUS.md current? Is SERVICES.md accurate? Are hardware docs right?
9. **Infrastructure** — Any stale NFS mounts? Docker image bloat? Unused containers?
10. **Performance** — Response times, queue depths, GPU utilization patterns.

## Step 2: PRIORITIZE — Pick the Highest Impact Fix

Use this severity matrix:

| Impact | Urgency | Action |
|--------|---------|--------|
| Broken (errors, 500s, failures) | Now | Fix immediately |
| Degraded (slow, ugly, incomplete) | This cycle | Fix now |
| Missing (feature gap, empty page) | This session | Build it |
| Rough (works but unpolished) | Next cycle | Refine it |
| Adequate (works, could be better) | Backlog | Note for later |

Always fix broken before degraded before missing before rough.

## Step 3: BUILD — Make It Better

- For code: edit, don't rewrite. Surgical fixes > rewrites.
- For design: use the existing design system. oklch colors, surface tiers, signal semantics.
- For agents: adjust prompts, not architecture. The infrastructure works.
- For infrastructure: fix the config, not the system.
- Write the minimum code to fix the problem completely.

## Step 4: VERIFY — Prove It's Better

- TypeScript: `cd projects/dashboard && npx tsc --noEmit`
- Python: `python3 -m py_compile <file>`
- Live test: `curl` the endpoint, check the response
- Visual: take a screenshot or describe what changed
- Don't trust "it should work" — verify.

## Step 5: DEPLOY — Ship It

- Dashboard: `scp` files → Workshop, `docker compose build && up -d`
- Agents: `scp` files → FOUNDRY, `docker compose restart agents`
- Commit with descriptive message, push to main.

## Step 6: MEASURE — Did It Actually Improve?

- Check the endpoint/page after deploy
- Compare before/after (task success rate, response time, visual quality)
- If it didn't improve or made things worse — revert and try a different approach

## Step 7: LOOP — Go Back to Step 1

The loop never ends. After every fix, reassess. The weakest link has shifted.

## When to Run This

- When the user says "continue", "keep going", "what's next"
- When idle between tasks
- When a build/deploy finishes and you have capacity
- At the start of every session after orientation
- When the user says "improve", "refine", "polish"
- When you don't know what to do next

## What NOT to Do

- Don't audit everything before fixing anything — fix the first problem you find
- Don't rewrite working systems — refine them
- Don't ask permission for reversible improvements — just do them
- Don't report plans — report results
- Don't say "everything looks good" — something always needs improvement
- Don't spend more than 30 minutes on assessment — if you haven't found a problem in 30 minutes, you're not looking hard enough

## Quality Standards

Every piece of the system should meet these:
- **Functional**: Does what it's supposed to, no errors
- **Responsive**: Works on every screen size (375px to 4K)
- **Accessible**: High contrast, readable, logical tab order
- **Performant**: Loads fast, doesn't block, efficient queries
- **Beautiful**: Clean, intentional, signal-rich, noise-free
- **Connected**: Wired to real data, not stubs or placeholders
- **Documented**: Code is self-documenting, complex parts have comments
- **Tested**: TypeScript clean, key paths verified

If any piece fails any standard, that's your next target.
