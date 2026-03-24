---
name: architecture-decision
description: Structured process for making and documenting architecture decisions with ADR format
triggers:
  - "architecture decision"
  - "ADR"
  - "design decision"
  - "should we use"
agent: researcher
context: fork
---

# Architecture Decision Skill

## Purpose
Guide structured decision-making for infrastructure and software architecture choices. Produces Architecture Decision Records (ADRs) consistent with existing format in `docs/decisions/`.

## Before Starting
1. Read `docs/decisions/` to see existing ADRs (currently ADR-001 through ADR-012)
2. Read relevant research in `docs/research/`
3. Check `docs/BLOCKED.md` for known blockers
4. Read hardware constraints from `docs/hardware/inventory.md`

## Procedure
1. Define the decision context — what problem are we solving?
2. Identify constraints from hardware inventory
3. Research and compare minimum 3 options
4. Evaluate against criteria:
   - Performance (benchmarks, throughput, latency)
   - Compatibility (with existing stack)
   - Sovereignty (data control, zero telemetry, local-first)
   - Complexity (operational burden, maintenance)
   - Future-proofing (upgrade path, community health)
5. Produce ADR following existing format in `docs/decisions/`:

```markdown
# ADR-XXX: [Title]

**Date:** YYYY-MM-DD
**Status:** Proposed | Accepted | Superseded
**Context:** [What problem/decision]
**Constraints:** [Hardware/software limits]

## Options Considered
### Option A: [Name]
- Pros: ...
- Cons: ...
- Evidence: ...

### Option B: [Name]
...

## Decision
[Which option and why]

## Consequences
[What changes, what tradeoffs accepted]
```

## Rules
- Right over fast — don't rush to a recommendation
- Hardware inventory is a hard constraint, not a suggestion
- Sovereignty preference: local > federated > cloud
- If decision requires hardware not in inventory, flag it explicitly
- Number sequentially after ADR-012
