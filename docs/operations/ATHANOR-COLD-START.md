# Athanor Cold Start

## Purpose

Use this document when the operator workstation restarts, generated reports are stale, or a runtime incident interrupts the usual flow. `C:/Athanor` is the adopted-system authority. `C:/athanor-devstack` is the forge, not runtime truth.

## Four Planes

- `build_system`: `C:/athanor-devstack`
- `adopted_system`: `C:/Athanor`
- `runtime_state`: live homelab
- `operator_local`: `C:/Users/Shaun/.codex`

Truth order:

1. Live probes and Athanor registries for runtime-facing truth
2. Athanor active-root docs for intended adopted truth
3. Devstack lanes, packets, board, and atlas for build truth
4. Operator-local helpers and archive evidence as non-authoritative context

## Cold Start Steps

1. Read `STATUS.md`, `PROJECT.md`, and `docs/operations/ATHANOR-OPERATING-SYSTEM.md`.
2. Run `python scripts/validate_platform_contract.py`.
3. Review the current registries that match the affected surface.
4. If the task is build-system work, switch to `C:/athanor-devstack` and use the forge lane/packet flow before editing.
5. If the task is runtime-facing, verify the live packet, service, or host state before changing anything.

## Recovery Rules

- Reconstruct the current state from repo truth, registries, and generated surfaces instead of relying on old chat memory.
- Athanor owns adopted truth and runtime packet contracts.
- Devstack does not override Athanor runtime truth after adoption.
- Operator-local helpers may accelerate work but may never become sole truth for adopted behavior.
- Treat startup docs as doctrine and re-entry only; read devstack board, atlas, packets, and Athanor registries for live state.
- A build change is not complete until the canonical Athanor surface is updated and packet-linked where required.
