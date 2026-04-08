# Local Runtime Env Surface

Source of truth: `config/automation-backbone/credential-surface-registry.json`, `config/automation-backbone/repo-roots-registry.json`, `docs/operations/OPERATOR_RUNBOOKS.md`
Validated against registry version: `credential-surface-registry.json@2026-04-02.1`, `repo-roots-registry.json@2026-04-06.1`, `program-operating-system.json@2026-03-25.1`
Mutable facts policy: the managed local env path and credential surface contract come from the registries. This runbook owns the operator sequence for populating DESK-local runtime env state without tracking secret values.

---

## Purpose

Scripts that emit Redis-backed automation records now support a managed local env surface. The preferred path is:

- override: `ATHANOR_RUNTIME_ENV_FILE`
- default: `~/.athanor/runtime.env`

The repo must never store the values that land there.

## Current Use

The following scripts honor the managed local env surface before failing closed:

- `scripts/automation_records.py`
- `scripts/mcp-redis.py`
- `scripts/mcp-smart-reader.py`
- `scripts/vault-ssh.py`
- `scripts/ssh-vault.ps1`

The current DESK runtime env surface resolves Redis auth successfully and now backs contract-healer and recovery-evidence persistence.

## Minimal Contract

For Redis-backed automation persistence on DESK:

- `ATHANOR_REDIS_PASSWORD` is required
- `ATHANOR_REDIS_URL` is optional if the default cluster URL is correct, but should be present when the runtime surface is being managed intentionally

For VAULT SSH-backed operator access on DESK:

- `ATHANOR_VAULT_KEY_PATH` is the preferred managed contract for the current key-backed helper path
- `ATHANOR_VAULT_USER` is optional and defaults to `root`
- `ATHANOR_VAULT_PASSWORD` is optional fallback only when the managed key path is unavailable

## File Format

The file accepts shell-style lines:

```bash
ATHANOR_REDIS_URL=redis://192.168.1.203:6379/0
ATHANOR_REDIS_PASSWORD=replace-me-outside-tracked-source
ATHANOR_VAULT_KEY_PATH=replace-me-with-a-host-local-private-key-path
```

`export KEY=value` is also accepted.

## Verification

Check the surface without printing values:

```bash
python scripts/runtime_env.py --check ATHANOR_REDIS_URL ATHANOR_REDIS_PASSWORD
python scripts/runtime_env.py --check ATHANOR_VAULT_KEY_PATH
python scripts/vault-ssh.py "echo CONNECTED && hostname"
python scripts/collect_truth_inventory.py
```

Success criteria:

- `scripts/runtime_env.py` reports no missing vars
- `scripts/vault-ssh.py` reaches VAULT without requiring ad hoc shell exports or the browser terminal
- `collect_truth_inventory.py` reports the local runtime env surface as present
- Redis-backed automation emitters stop failing closed for missing auth in the current shell context

## Cleanup

1. Remove ad hoc one-off shell exports once the managed local env file is in place.
2. Keep the file host-local and out of tracked source.
3. If the path changes, update the credential surface registry and rerun the truth reports.
