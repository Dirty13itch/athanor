---
name: verify-inventory
description: Cross-reference hardware inventory against node configs, detect discrepancies
triggers:
  - "verify inventory"
  - "audit hardware"
  - "check inventory"
  - "hardware audit"
agent: infra-auditor
context: fork
---

# Verify Inventory Skill

## Purpose
Cross-reference `docs/archive/hardware/hardware-inventory.md` against node audits and architecture documents to detect discrepancies.

## Procedure
1. Read `docs/archive/hardware/hardware-inventory.md` completely
2. Read `docs/hardware/CURRENT-STATE.md` and `docs/hardware/COMPLETE-SYSTEM-BREAKDOWN.md`
3. Read node audits: `docs/hardware/*-audit-*.md`
4. For each node (DEV, Node1, Node2, VAULT):
   - Compare documented CPU, RAM, GPU, motherboard, PSU against audit findings
   - Flag any mismatches between inventory and architecture assumptions
5. Check `docs/hardware/loose-inventory.md` - verify unallocated components
6. Produce summary table:

| Component | Inventory Says | Audit Says | Status |
|-----------|---------------|------------|--------|
| ...       | ...           | ...        | verified/mismatch/unreachable |

## Output
Structured report with findings, discrepancies, and recommended actions.
