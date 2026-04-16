# Local Runtime Env Surface

Source of truth: `config/automation-backbone/credential-surface-registry.json`, `config/automation-backbone/repo-roots-registry.json`, `docs/operations/OPERATOR_RUNBOOKS.md`
Validated against registry version: `credential-surface-registry.json@2026-04-16.1`, `repo-roots-registry.json@2026-04-06.1`, `program-operating-system.json@2026-03-25.1`
Mutable facts policy: the managed local env path and credential surface contract come from the registries. This runbook owns the operator sequence for populating DESK-local runtime env state without tracking secret values.

---

## Purpose

Scripts that emit Redis-backed automation records now support a managed local env surface. The preferred path is:

- override: `ATHANOR_RUNTIME_ENV_FILE`
- default: `~/.athanor/runtime.env`

The repo must never store the values that land there.

## Current Use

The following scripts honor the managed local env surface before failing closed:

Current / primary use:

- `scripts/automation_records.py`
- `scripts/mcp-redis.py`
- `scripts/mcp-smart-reader.py`
- `scripts/vault-ssh.py`

Recovery-only fallback:

- `scripts/ssh-vault.ps1`

The current DESK runtime env surface resolves Redis auth successfully and now backs contract-healer and recovery-evidence persistence.

Gateway-backed DESK coding tools also resolve through the same managed runtime env surface. The canonical local contract is `ATHANOR_LITELLM_API_KEY` plus `ATHANOR_LITELLM_URL`, while `LITELLM_API_KEY` and `LITELLM_MASTER_KEY` remain accepted legacy aliases for the key. `OPENAI_API_KEY`, `OPENAI_API_BASE`, `OPENAI_HOST`, and `OPENAI_BASE_PATH` are compatibility envs derived at launcher time rather than tracked independently.

WSL is now the active Codex execution surface on DESK. The Linux-side runtime env path is the same default contract, `~/.athanor/runtime.env`, and should carry the canonical Athanor LiteLLM gateway envs so the WSL-native Aider and Goose launchers can run without ad hoc shell exports.

## Minimal Contract

For Redis-backed automation persistence on DESK:

- `ATHANOR_REDIS_PASSWORD` is required
- `ATHANOR_REDIS_URL` is optional if the default cluster URL is correct, but should be present when the runtime surface is being managed intentionally

For VAULT SSH-backed operator access on DESK:

- `ATHANOR_VAULT_KEY_PATH` is the preferred managed contract for the current key-backed helper path
- `ATHANOR_VAULT_USER` is optional and defaults to `root`
- `ATHANOR_VAULT_PASSWORD` is optional fallback only when the managed key path is unavailable

For gateway-backed DESK CLI and editor adapters:

- `ATHANOR_LITELLM_API_KEY` is the preferred managed contract for Goose, Aider, and generated adapter profiles
- `LITELLM_API_KEY` and `LITELLM_MASTER_KEY` are accepted compatibility aliases that resolve into `ATHANOR_LITELLM_API_KEY` without copying the same secret into multiple local files
- `ATHANOR_LITELLM_URL` defaults to `http://192.168.1.203:4000/v1` when the managed runtime env file omits it
- `OPENAI_API_KEY`, `OPENAI_API_BASE`, `OPENAI_HOST`, and `OPENAI_BASE_PATH` derive from the canonical Athanor contract during launcher/bootstrap resolution

For WSL-backed Codex execution on DESK:

- `~/.athanor/runtime.env` is the canonical Linux-side gateway credential surface
- `C:\Codex System Config\scripts\prepare-codex-wsl.ps1` should refresh that Linux-side file from the Windows-side managed contract and user env before `preflight-codex-wsl.ps1` runs
- the WSL surface should carry the canonical `ATHANOR_LITELLM_API_KEY` and `ATHANOR_LITELLM_URL` names even if the Windows-side source still exposes `LITELLM_API_KEY`

## File Format

The file accepts shell-style lines:

```bash
ATHANOR_REDIS_URL=redis://192.168.1.203:6379/0
ATHANOR_REDIS_PASSWORD=replace-me-outside-tracked-source
ATHANOR_VAULT_KEY_PATH=replace-me-with-a-host-local-private-key-path
LITELLM_API_KEY=replace-me-outside-tracked-source
# ATHANOR_LITELLM_URL is optional when the canonical VAULT LiteLLM URL stays unchanged.
```

`export KEY=value` is also accepted.

## Verification

Check the surface without printing values:

```bash
python scripts/runtime_env.py --check ATHANOR_REDIS_URL ATHANOR_REDIS_PASSWORD
python scripts/runtime_env.py --check ATHANOR_VAULT_KEY_PATH
python scripts/runtime_env.py --check ATHANOR_LITELLM_URL ATHANOR_LITELLM_API_KEY OPENAI_API_BASE OPENAI_API_KEY
bash scripts/run-aider-athanor-shell.sh --version
bash scripts/run-goose-athanor-shell.sh --version
powershell -ExecutionPolicy Bypass -File scripts/run-goose-athanor-shell.ps1 info
powershell -ExecutionPolicy Bypass -File scripts/run-aider-athanor-shell.ps1 --version
python scripts/vault-ssh.py "echo CONNECTED && hostname"
python scripts/collect_truth_inventory.py
```

Success criteria:

- `scripts/runtime_env.py` reports no missing vars
- `~/.athanor/runtime.env` exists on the active WSL execution surface and resolves the canonical Athanor LiteLLM gateway contract
- Goose and Aider wrappers start without ad hoc shell exports
- `scripts/vault-ssh.py` reaches VAULT without requiring ad hoc shell exports or the browser terminal
- `collect_truth_inventory.py` reports the local runtime env surface as present
- Redis-backed automation emitters stop failing closed for missing auth in the current shell context

## Cleanup

1. Remove ad hoc one-off shell exports once the managed local env file is in place.
2. Keep the file host-local and out of tracked source.
3. If the path changes, update the credential surface registry and rerun the truth reports.
