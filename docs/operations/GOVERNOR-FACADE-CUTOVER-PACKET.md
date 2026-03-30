# Governor Facade Cutover Packet

Generated from `config/automation-backbone/runtime-migration-registry.json` and the cached truth snapshot by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

This packet is retained as the verified record of the completed DEV `:8760` cutover. Use it to audit what was backed up, replaced, and verified, and only rerun the commands if drift reopens the seam.

- Registry version: `2026-03-29.2`
- Cached truth snapshot: `2026-03-30T16:42:28.938927+00:00`
- Migrations included: `1`

## dev-governor-facade-8760-callers

- Status: `retired`
- Runtime surface: `athanor-governor.service on DEV :8760`
- Runtime owner: `/home/shaun/repos/athanor on DEV`
- Runtime listener: `http://127.0.0.1:8760`
- Observed runtime repo head: `075490f`
- Sync-required callers: `0`
- Runbook: [`docs/runbooks/governor-facade-retirement.md`](/C:/Athanor/docs/runbooks/governor-facade-retirement.md)
- Companion report: [`docs/operations/RUNTIME-MIGRATION-REPORT.md`](/C:/Athanor/docs/operations/RUNTIME-MIGRATION-REPORT.md)

### Recorded Preflight Commands

```bash
python scripts/collect_truth_inventory.py
python scripts/generate_truth_inventory_reports.py --report runtime_migrations --report runtime_cutover --check
python scripts/validate_platform_contract.py
ssh dev 'mkdir -p "/home/shaun/.athanor/backups/governor-facade-cutover"'
ssh dev 'mkdir -p "/home/shaun/.athanor/backups/governor-facade-cutover" && systemctl cat athanor-governor.service > "/home/shaun/.athanor/backups/governor-facade-cutover/athanor-governor.service"'
ssh dev 'journalctl -u athanor-governor.service -n 400 --no-pager > "/home/shaun/.athanor/backups/governor-facade-cutover/athanor-governor.service.pre-cutover.journal.log"'
```

### Recorded Caller Sync Commands

#### scripts/drift-check.sh

- Sync order: `1`
- Sync decision: `already_synced`
- Runtime target: `/home/shaun/repos/athanor/scripts/drift-check.sh`
- Backup target: `/home/shaun/.athanor/backups/governor-facade-cutover/scripts/drift-check.sh`
- Rollback ready: `True`
- Cutover check: Script runs cleanly from implementation authority without any :8760 reference and the DEV runtime copy no longer journals facade traffic.

```bash
ssh dev 'mkdir -p "/home/shaun/.athanor/backups/governor-facade-cutover/scripts"'
# scripts/drift-check.sh already matches implementation authority; no file copy required.
ssh dev 'python3 - <<'"'"'PY'"'"'
from pathlib import Path
path = Path("/home/shaun/repos/athanor/scripts/drift-check.sh")
text = path.read_text(encoding="utf-8") if path.exists() else ""
tokens = ["127.0.0.1:8760", "localhost:8760", "/queue", "/dispatch-and-run", "ATHANOR_GOVERNOR_URL"]
hits = [token for token in tokens if token in text]
print(hits if hits else "clean")
PY'
```

#### scripts/smoke-test.sh

- Sync order: `2`
- Sync decision: `already_synced`
- Runtime target: `/home/shaun/repos/athanor/scripts/smoke-test.sh`
- Backup target: `/home/shaun/.athanor/backups/governor-facade-cutover/scripts/smoke-test.sh`
- Rollback ready: `True`
- Cutover check: Script runs cleanly from implementation authority and the DEV runtime copy no longer hits :8760.

```bash
ssh dev 'mkdir -p "/home/shaun/.athanor/backups/governor-facade-cutover/scripts"'
# scripts/smoke-test.sh already matches implementation authority; no file copy required.
ssh dev 'python3 - <<'"'"'PY'"'"'
from pathlib import Path
path = Path("/home/shaun/repos/athanor/scripts/smoke-test.sh")
text = path.read_text(encoding="utf-8") if path.exists() else ""
tokens = ["127.0.0.1:8760", "localhost:8760", "/queue", "/dispatch-and-run", "ATHANOR_GOVERNOR_URL"]
hits = [token for token in tokens if token in text]
print(hits if hits else "clean")
PY'
```

#### services/cluster_config.py

- Sync order: `3`
- Sync decision: `already_synced`
- Runtime target: `/home/shaun/repos/athanor/services/cluster_config.py`
- Backup target: `/home/shaun/.athanor/backups/governor-facade-cutover/services/cluster_config.py`
- Rollback ready: `True`
- Cutover check: DEV runtime repo no longer exports or defaults any localhost:8760 governor URL.

```bash
ssh dev 'mkdir -p "/home/shaun/.athanor/backups/governor-facade-cutover/services"'
# services/cluster_config.py already matches implementation authority; no file copy required.
ssh dev 'python3 - <<'"'"'PY'"'"'
from pathlib import Path
path = Path("/home/shaun/repos/athanor/services/cluster_config.py")
text = path.read_text(encoding="utf-8") if path.exists() else ""
tokens = ["127.0.0.1:8760", "localhost:8760", "/queue", "/dispatch-and-run", "ATHANOR_GOVERNOR_URL"]
hits = [token for token in tokens if token in text]
print(hits if hits else "clean")
PY'
```

#### services/gateway/main.py

- Sync order: `4`
- Sync decision: `already_synced`
- Runtime target: `/home/shaun/repos/athanor/services/gateway/main.py`
- Backup target: `/home/shaun/.athanor/backups/governor-facade-cutover/services/gateway/main.py`
- Rollback ready: `True`
- Cutover check: Gateway health references canonical task-engine stats and topology-owned dependency ids instead of localhost:8760.

```bash
ssh dev 'mkdir -p "/home/shaun/.athanor/backups/governor-facade-cutover/services/gateway"'
# services/gateway/main.py already matches implementation authority; no file copy required.
ssh dev 'python3 - <<'"'"'PY'"'"'
from pathlib import Path
path = Path("/home/shaun/repos/athanor/services/gateway/main.py")
text = path.read_text(encoding="utf-8") if path.exists() else ""
tokens = ["127.0.0.1:8760", "localhost:8760", "/queue", "/dispatch-and-run", "ATHANOR_GOVERNOR_URL"]
hits = [token for token in tokens if token in text]
print(hits if hits else "clean")
PY'
```

#### services/governor/status_report.py

- Sync order: `5`
- Sync decision: `already_synced`
- Runtime target: `/home/shaun/repos/athanor/services/governor/status_report.py`
- Backup target: `/home/shaun/.athanor/backups/governor-facade-cutover/services/governor/status_report.py`
- Rollback ready: `True`
- Cutover check: Helper reads canonical task and subscription summary surfaces only.

```bash
ssh dev 'mkdir -p "/home/shaun/.athanor/backups/governor-facade-cutover/services/governor"'
# services/governor/status_report.py already matches implementation authority; no file copy required.
ssh dev 'python3 - <<'"'"'PY'"'"'
from pathlib import Path
path = Path("/home/shaun/repos/athanor/services/governor/status_report.py")
text = path.read_text(encoding="utf-8") if path.exists() else ""
tokens = ["127.0.0.1:8760", "localhost:8760", "/queue", "/dispatch-and-run", "ATHANOR_GOVERNOR_URL"]
hits = [token for token in tokens if token in text]
print(hits if hits else "clean")
PY'
```

#### services/governor/overnight.py

- Sync order: `6`
- Sync decision: `already_synced`
- Runtime target: `/home/shaun/repos/athanor/services/governor/overnight.py`
- Backup target: `/home/shaun/.athanor/backups/governor-facade-cutover/services/governor/overnight.py`
- Rollback ready: `True`
- Cutover check: Helper dispatches through /v1/tasks/dispatch and no longer reads /queue or /dispatch-and-run.

```bash
ssh dev 'mkdir -p "/home/shaun/.athanor/backups/governor-facade-cutover/services/governor"'
# services/governor/overnight.py already matches implementation authority; no file copy required.
ssh dev 'python3 - <<'"'"'PY'"'"'
from pathlib import Path
path = Path("/home/shaun/repos/athanor/services/governor/overnight.py")
text = path.read_text(encoding="utf-8") if path.exists() else ""
tokens = ["127.0.0.1:8760", "localhost:8760", "/queue", "/dispatch-and-run", "ATHANOR_GOVERNOR_URL"]
hits = [token for token in tokens if token in text]
print(hits if hits else "clean")
PY'
```

#### services/governor/act_first.py

- Sync order: `7`
- Sync decision: `already_synced`
- Runtime target: `/home/shaun/repos/athanor/services/governor/act_first.py`
- Backup target: `/home/shaun/.athanor/backups/governor-facade-cutover/services/governor/act_first.py`
- Rollback ready: `True`
- Cutover check: Helper reads the canonical task list instead of mutating a local queue snapshot.

```bash
ssh dev 'mkdir -p "/home/shaun/.athanor/backups/governor-facade-cutover/services/governor"'
# services/governor/act_first.py already matches implementation authority; no file copy required.
ssh dev 'python3 - <<'"'"'PY'"'"'
from pathlib import Path
path = Path("/home/shaun/repos/athanor/services/governor/act_first.py")
text = path.read_text(encoding="utf-8") if path.exists() else ""
tokens = ["127.0.0.1:8760", "localhost:8760", "/queue", "/dispatch-and-run", "ATHANOR_GOVERNOR_URL"]
hits = [token for token in tokens if token in text]
print(hits if hits else "clean")
PY'
```

#### services/governor/self_improve.py

- Sync order: `8`
- Sync decision: `already_synced`
- Runtime target: `/home/shaun/repos/athanor/services/governor/self_improve.py`
- Backup target: `/home/shaun/.athanor/backups/governor-facade-cutover/services/governor/self_improve.py`
- Rollback ready: `True`
- Cutover check: Helper submits durable tasks through /v1/tasks and no longer relies on governor-owned queue surfaces.

```bash
ssh dev 'mkdir -p "/home/shaun/.athanor/backups/governor-facade-cutover/services/governor"'
# services/governor/self_improve.py already matches implementation authority; no file copy required.
ssh dev 'python3 - <<'"'"'PY'"'"'
from pathlib import Path
path = Path("/home/shaun/repos/athanor/services/governor/self_improve.py")
text = path.read_text(encoding="utf-8") if path.exists() else ""
tokens = ["127.0.0.1:8760", "localhost:8760", "/queue", "/dispatch-and-run", "ATHANOR_GOVERNOR_URL"]
hits = [token for token in tokens if token in text]
print(hits if hits else "clean")
PY'
```

#### services/sentinel/checks.py

- Sync order: `9`
- Sync decision: `already_synced`
- Runtime target: `/home/shaun/repos/athanor/services/sentinel/checks.py`
- Backup target: `/home/shaun/.athanor/backups/governor-facade-cutover/services/sentinel/checks.py`
- Rollback ready: `True`
- Cutover check: Sentinel integration checks use canonical task-engine stats and topology-owned service health URLs.

```bash
ssh dev 'mkdir -p "/home/shaun/.athanor/backups/governor-facade-cutover/services/sentinel"'
# services/sentinel/checks.py already matches implementation authority; no file copy required.
ssh dev 'python3 - <<'"'"'PY'"'"'
from pathlib import Path
path = Path("/home/shaun/repos/athanor/services/sentinel/checks.py")
text = path.read_text(encoding="utf-8") if path.exists() else ""
tokens = ["127.0.0.1:8760", "localhost:8760", "/queue", "/dispatch-and-run", "ATHANOR_GOVERNOR_URL"]
hits = [token for token in tokens if token in text]
print(hits if hits else "clean")
PY'
```

### Post-Cutover Verification Record

```bash
ssh dev 'grep -R "127.0.0.1:8760\|localhost:8760\|/queue\|/dispatch-and-run\|ATHANOR_GOVERNOR_URL" -n /home/shaun/repos/athanor/scripts /home/shaun/repos/athanor/services || true'
ssh dev 'journalctl -u athanor-governor.service -n 200 --no-pager'
ssh dev 'ss -ltnp | grep 8760 || true'
python scripts/collect_truth_inventory.py
python scripts/generate_truth_inventory_reports.py --report runtime_migrations --report runtime_cutover
python scripts/validate_platform_contract.py
```

### Runtime Retirement Status

The DEV runtime cutover is complete: `athanor-governor.service` is removed and no `:8760` listener remains. Use the retirement runbook only if drift reopens the seam and a rollback or re-cutover becomes necessary.
