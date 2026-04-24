# OpenClaw Sidecar Runtime Packet

Generated status source: `reports/truth-inventory/openclaw-sidecar-status.json`

## Purpose

OpenClaw is a DEV-hosted sidecar operator layer for local personal operations. It does not replace the Athanor Command Center and it must not become a broad VAULT/Unraid root agent.

## Runtime Contract

- Host: `dev`
- Service: `openclaw-gateway.service`
- Bind: `127.0.0.1:18789` only
- Operator access: DESK SSH tunnel to `127.0.0.1:18789`
- State: `/home/shaun/.openclaw`
- Status artifact: `python scripts/write_openclaw_sidecar_status.py --write`

## Current Scope

- `operator`, `coder`, `cluster`, `creative`, `research`, and `home-media` agents have isolated workspaces.
- OpenAI Codex OAuth is installed and probed through `openai-codex/gpt-5.4`.
- Exec policy is `cautious`: allowlist execution, ask on miss, deny fallback.
- DESK has an isolated `openclaw --profile dev` profile for the tunneled gateway.
- DESK is paired as the first OpenClaw node and has proved harmless `system.which` execution through the approval-gated path.
- FOUNDRY and WORKSHOP are paired through per-node restricted SSH tunnels to the DEV loopback Gateway and have proved harmless `system.which` execution.
- The first report-only cron job is installed for a daily OpenClaw model/scheduler heartbeat.
- Telegram credential installation is repeatable through `scripts/configure_openclaw_telegram.py`; no token is stored in the repo.
- VAULT is intentionally not a writable OpenClaw node.

## Widening Gates

- Telegram must be configured with a BotFather token, numeric allowlisted chats, and explicit approver IDs before mobile delivery or approvals are enabled.
- Telegram must prove one DM approval round trip before it becomes an operational approval path.
- FOUNDRY and WORKSHOP mutation must stay packet-gated; their initial proof is visibility plus harmless diagnostics only.
- VAULT node pairing or write access requires a separate runtime packet.

## Verification

```powershell
ssh dev 'export PATH="$HOME/.local/npm-global/bin:$PATH"; openclaw gateway status'
ssh dev "curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:18789/healthz"
ssh dev 'export PATH="$HOME/.local/npm-global/bin:$PATH"; openclaw security audit --json'
ssh dev 'export PATH="$HOME/.local/npm-global/bin:$PATH"; openclaw models status --check --probe --json'
ssh dev 'export PATH="$HOME/.local/npm-global/bin:$PATH"; openclaw channels status --probe --json'
python scripts/configure_openclaw_telegram.py --token-file <local-token-file> --allow-from <numeric-telegram-id>
python scripts/write_openclaw_sidecar_status.py --write
python scripts/validate_platform_contract.py
```
