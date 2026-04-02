# Governor Compatibility Facade Retirement

Source of truth: `config/automation-backbone/platform-topology.json`, `config/automation-backbone/runtime-subsystem-registry.json`, `config/automation-backbone/runtime-migration-registry.json`, `config/automation-backbone/repo-roots-registry.json`, `STATUS.md`
Validated against registry version: `platform-topology.json@2026-04-01.1`, `runtime-subsystem-registry.json@2026-03-29.2`, `runtime-migration-registry.json@2026-03-29.2`, `repo-roots-registry.json@2026-04-02.5`
Mutable facts policy: implementation authority stays in `C:\Athanor`, runtime authority stays on DEV until broader runtime convergence. This runbook now preserves the completed operator sequence, rollback evidence, and acceptance checks for the retired `athanor-governor.service` cutover.

---

## Purpose

Record, verify, and preserve rollback evidence for the retired standalone governor compatibility surface on DEV.

The 2026-03-29 maintenance window already removed the live `:8760` listener, disabled the runtime unit, synced the 9 mapped runtime-owned callers to implementation authority, and the repo-side cleanup has now deleted the last implementation-authority facade file.

This remains an ask-first runtime lane for any future rollback or reactivation because it touches live DEV systemd state.

## Current Truth

- `services/governor/main.py` has been deleted from implementation authority; the only remaining facade history is in rollback evidence, reports, and this runbook.
- Legacy write-capable routes already fail closed with `410`.
- Canonical task and posture truth live at Foundry agent-server surfaces such as `/v1/tasks`, `/v1/tasks/stats`, and `/v1/governor`.
- The standalone governor `:8760` identity is no longer part of canonical topology, and the 2026-03-29 collector now proves DEV no longer runs `athanor-governor.service` as a live listener.
- The completed maintenance window backed up the unit and journal under `/home/shaun/.athanor/backups/governor-facade-cutover`, stopped the service, removed the unit, and left `systemctl is-enabled athanor-governor.service` at `not-found`.
- The last live caller set covered by the cutover included `scripts/drift-check.sh`, `scripts/smoke-test.sh`, `services/cluster_config.py`, `services/gateway/main.py`, `services/governor/status_report.py`, `services/governor/overnight.py`, `services/governor/act_first.py`, `services/governor/self_improve.py`, and `services/sentinel/checks.py`.
- The latest collector snapshot hashes those 9 runtime-owned callers against implementation authority and now shows all 9 as content-match with zero observed runtime `:8760` references.
- Use [RUNTIME-MIGRATION-REPORT.md](/C:/Athanor/docs/operations/RUNTIME-MIGRATION-REPORT.md) as the caller-by-caller audit record and rollback reference for the completed cutover.
- Use [GOVERNOR-FACADE-CUTOVER-PACKET.md](/C:/Athanor/docs/operations/GOVERNOR-FACADE-CUTOVER-PACKET.md) as the retained backup-and-replace packet only if rollback or drift reopening becomes necessary.
- The truth collector now cross-checks the observed DEV caller set against `config/automation-backbone/runtime-migration-registry.json`, so any new unmapped `:8760` caller becomes explicit drift instead of silent runtime residue.
- The runtime-migration report now also includes a dedicated `Runtime Sync Verification Checklist` plus per-caller sync order, runtime file paths, sync decision, explicit sync strategy, rollback target, content-sync state, short hashes, and size or line-count deltas against `C:\Athanor`, so the completed cutover remains a deterministic rollback reference instead of a manual grep hunt.
- Troubleshooting may still probe `http://127.0.0.1:8760/health`, but only as an explicit rollback-or-drift audit step after canonical `/v1/governor` and `/v1/tasks/stats` checks are already green.

## Retirement State

The retirement gate is now satisfied:

1. No live operator surface, helper, or automation still depends on `http://127.0.0.1:8760`.
2. Canonical `/v1/governor`, `/v1/tasks`, and `/v1/tasks/stats` cover the remaining read paths cleanly.
3. `athanor-governor.service` was removed without regressing dashboard, helper, or collector behavior.
4. The DEV runtime repo and deployed helper estate are reconciled so the remaining `:8760` callers are gone, not just hidden.
5. Repo truth, reports, troubleshooting, and tests all now agree that the implementation-authority facade file is deleted.

If any of those ever regress, treat it as rollback or drift work, not a reason to recreate a second implementation-authority task surface casually.

## Preflight

1. Review `STATUS.md`.
2. Review `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`.
3. Review `docs/operations/TRUTH-DRIFT-REPORT.md`.
4. Review `docs/TROUBLESHOOTING.md`.
5. Regenerate or verify truth reports before touching runtime state.
6. Verify the cutover backup root at `/home/shaun/.athanor/backups/governor-facade-cutover` still exists.
7. Verify the saved DEV systemd unit and journal evidence still exist under that backup root before considering rollback or repo-side deletion.

## Read-Only Audit Commands

Use these to verify the retired state before deciding whether any rollback is warranted:

```bash
python scripts/collect_truth_inventory.py
python scripts/generate_truth_inventory_reports.py --check
ssh dev 'systemctl status athanor-governor --no-pager || true'
ssh dev 'systemctl cat athanor-governor || true'
ssh dev 'journalctl -u athanor-governor -n 200 --no-pager'
ssh dev 'ss -ltnp | grep 8760 || true'
ssh dev "curl -sf http://127.0.0.1:8760/health" | python3 -m json.tool || true
ssh foundry "curl -s http://127.0.0.1:9000/v1/governor" | python3 -m json.tool
ssh foundry "curl -s http://127.0.0.1:9000/v1/tasks/stats" | python3 -m json.tool
```

Do not treat a successful `:8760` probe during any future rollback as proof that the facade is still needed. The desired steady state is no live listener.

## Change Sequence

1. Preserve the completed backup root and journal evidence under `/home/shaun/.athanor/backups/governor-facade-cutover`.
2. Re-run the canonical agent-server posture and task stats checks if you need to reconfirm post-cutover health.
3. Use [RUNTIME-MIGRATION-REPORT.md](/C:/Athanor/docs/operations/RUNTIME-MIGRATION-REPORT.md) to confirm all 9 mapped callers remain `content_match` and `cutover_verified`.
4. Use [GOVERNOR-FACADE-CUTOVER-PACKET.md](/C:/Athanor/docs/operations/GOVERNOR-FACADE-CUTOVER-PACKET.md) as the retained command packet and rollback reference for this completed maintenance window.
5. Keep repo truth, troubleshooting, reports, and contracts aligned so `:8760` stays a rollback-only surface.
6. Preserve this runbook, the generated cutover packet, and the backup root as the only sanctioned rollback path.

## Acceptance Checks

After the completed live runtime pass, or during any later audit:

```bash
ssh dev 'systemctl is-active athanor-governor || true'
ssh dev 'systemctl is-enabled athanor-governor || true'
ssh dev 'ss -ltnp | grep 8760 || true'
python scripts/collect_truth_inventory.py
python scripts/generate_truth_inventory_reports.py --check
python scripts/validate_platform_contract.py
cd projects/agents && .\.venv\Scripts\python -m pytest tests -q
```

Success criteria:

- `athanor-governor.service` remains stopped or absent in the steady retired state.
- No live listener remains on `:8760`.
- No new `GET /queue` or `GET /health` entries land in the `athanor-governor` journal after the maintenance-window cutover.
- Canonical task-engine and governor posture surfaces remain healthy.
- Reports, troubleshooting, and repo contracts treat the retired compatibility facade as deleted implementation code plus rollback-only runtime evidence.

## Rollback

1. Restore the saved systemd unit.
2. Run `sudo systemctl daemon-reload`.
3. Run `sudo systemctl enable --now athanor-governor`.
4. Re-run the read-only audit commands.
5. Confirm the collector and truth reports are back to the prior known-good state.
