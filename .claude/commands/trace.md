---
description: Trace a feature across all reference repos and the live Athanor codebase. Finds every implementation, compares approaches, and recommends the best path to port.
allowed-tools: Read, Grep, Glob, Bash(grep:*), Bash(git:*), Agent
---

Trace the feature "$ARGUMENTS" across all repos in ~/repos/reference/ and the live ~/repos/athanor/ repo.

For each repo that has this feature:
1. Find the relevant source files (grep for function names, class names, config keys)
2. Read the implementation
3. Note the approach, dependencies, and design decisions
4. Note what worked and what was abandoned (check git log for relevant commits)

Then produce:
- A comparison table: repo | approach | status | dependencies | notes
- The strongest implementation (most complete, best tested, cleanest code)
- A recommendation for how to bring this into athanor/ with minimal adaptation
- Specific files to copy or adapt, with the changes needed

Reference repos (READ ONLY):
- ~/repos/reference/hydra/ — 74K LOC Python, predecessor system
- ~/repos/reference/kaizen/ — GWT cognitive architecture, SGLang-based
- ~/repos/reference/local-system/ — 4th iteration design docs
- ~/repos/reference/system-bible/ — Locked hardware decisions
