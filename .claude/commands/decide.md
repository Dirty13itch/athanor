---
description: Create an Architecture Decision Record. Documents a decision with context, options, rationale, and consequences.
allowed-tools: Read, Write, Edit, Bash(ls:*), Bash(cat:*), Bash(find:*), Grep, Glob
---

Create an ADR for: $ARGUMENTS

1. Find next ADR number: `ls docs/decisions/ADR-*.md 2>/dev/null | sort -V | tail -1`
2. Check docs/research/ for related research
3. Read docs/VISION.md to verify alignment with principles
4. Create the ADR

Save as: docs/decisions/ADR-{NNN}-{slug}.md

Template:
```
# ADR-{NNN}: {Title}

**Status:** Proposed | Accepted | Superseded by ADR-XXX
**Date:** {YYYY-MM-DD}
**Research:** {links to docs/research/ files}

## Context
What problem or question prompted this decision?

## Options Considered
### Option A: {name}
- Pros:
- Cons:
- Evidence:

### Option B: {name}
- Pros:
- Cons:
- Evidence:

## Decision
What are we doing?

## Rationale
Why this option? Cite evidence. Apply the One-Person Scale filter.

## Consequences
What becomes easier or harder?

## References
- {URLs, datasheets, benchmarks}
```
