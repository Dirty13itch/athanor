# Wan2GP Remote-Only Watch Packet

Source of truth:
- `reports/reconciliation/wan2gp-remote-only-watch-latest.json`
- `config/automation-backbone/reconciliation-source-registry.json`
- `docs/operations/ATHANOR-ECOSYSTEM-REGISTRY.md`
- `docs/operations/ATHANOR-TENANT-QUEUE.md`

## Purpose

Keep `Dirty13itch/Wan2GP` governed as an explicit remote-only portfolio repo while no confirmed local clone exists.

This packet exists because the portfolio classification is already locked, but the repo still has no governed local working root.

## Current Facts

- GitHub repo: `Dirty13itch/Wan2GP`
- Current posture: remote-only `standalone-external`
- Confirmed local clone: none
- Current working-clone note: the targeted 3-depth `C:\` sweep found only Athanor research/docs references and downloaded model files, not a governed repo root

## Execution Rules

- Do not invent or register a local implementation root for Wan2GP until a real working clone exists.
- Keep Wan2GP governed as a remote-only standalone-external repo while no confirmed local clone is present.
- If a local clone appears later, add it to `reconciliation-source-registry.json`, rerun the GitHub portfolio sync, and revalidate Athanor truth before treating that clone as part of active reconciliation work.

## Completion Condition

This packet is complete only when one of these becomes true:

- Wan2GP remains explicitly governed as remote-only and does not drift back into ambiguous status
- or a real local clone appears, is registered, and is reclassified through the normal reconciliation flow
