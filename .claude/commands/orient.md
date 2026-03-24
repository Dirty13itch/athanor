---
description: Orient yourself at the start of a session. Read the vision, check recent activity, find where we left off.
allowed-tools: Read, Bash(git:*), Bash(cat:*), Bash(ls:*), Bash(find:*), Bash(head:*), Grep, Glob, LS
---

Orient to the current state of Athanor.

1. Read CLAUDE.md
2. Read docs/VISION.md
3. Run `git log --oneline -20` to see recent activity
4. List recent research: `ls -lt docs/research/ | head -10`
5. List recent decisions: `ls -lt docs/decisions/ | head -10`
6. Check for TODOs: `grep -r "TODO\|FIXME\|OPEN QUESTION\|NEXT" docs/ --include="*.md" -l`
7. Check MCP server status with /mcp
8. Summarize:
   - What was last worked on
   - What's next
   - Any open questions or blockers
   - What MCP servers are connected
