# Troubleshooting Guide

Reference truth: `config/automation-backbone/platform-topology.json`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/PROVIDER-CATALOG-REPORT.md`, `docs/RECOVERY.md`, `python scripts/session_restart_brief.py --refresh`, `reports/truth-inventory/finish-scoreboard.json`, and `reports/truth-inventory/runtime-packet-inbox.json`
Validated against registry version: `platform-topology.json@2026-04-11.2`, `provider-catalog.json@2026-04-16.3`, `credential-surface-registry.json@2026-04-14.1`
Mutable facts policy: runtime ownership, service URLs, provider execution state, and secret posture must come from registries and generated reports first. This document is a quick-reference fallback for operator triage after those canonical surfaces are checked; it is not the live recovery or queue authority surface.

---

## Before You Triage

1. Run `python scripts/session_restart_brief.py --refresh`.
2. Read the restart brief, runtime ownership report, and provider catalog report before acting on any command below.
3. Trust the generated runtime, provider, and dispatch surfaces before any older shell habit or remembered hostname.
4. Treat every command below as a quick-reference entrypoint only after the current canonical reports agree and the affected runtime lane is clearly owned.

## Command Use Boundary

If a command block below disagrees with generated runtime, provider, routing, or publication truth, stop and treat the command block as legacy quick-reference until canon is repaired. These sections are entrypoints, not authority.

## Service Down? (Reference Commands Only)
```bash
# Legacy quick health check
bash scripts/drift-check.sh

# Inspect runtime ownership before any recovery action
python scripts/collect_truth_inventory.py
ssh dev "systemctl list-units 'athanor-*' --no-pager"
ssh dev "docker ps --format '{{.Names}}\t{{.Status}}'"

# Legacy recovery examples; only use these when the generated runtime reports
# explicitly show the lane is DEV-owned or FOUNDRY-owned and restartable
ssh dev "sudo systemctl restart athanor-dashboard"
ssh dev "sudo systemctl restart athanor-quality-gate"

# Legacy inference restart examples; do not treat these as default operator actions
ssh foundry "docker restart vllm-coordinator"
ssh foundry "docker restart vllm-coder"
```

## Provider Execution Or LiteLLM Routing Looks Wrong? (Reference Commands Only)
```bash
# Check provider execution truth first
python scripts/generate_truth_inventory_reports.py --report providers
ssh foundry "curl -s http://127.0.0.1:9000/v1/subscriptions/providers" | python3 -m json.tool
ssh foundry "curl -s http://127.0.0.1:9000/v1/subscriptions/summary" | python3 -m json.tool
ssh foundry "curl -s http://127.0.0.1:9000/v1/subscriptions/execution" | python3 -m json.tool
ssh foundry "curl -s http://127.0.0.1:9000/v1/subscriptions/handoffs?limit=10" | python3 -m json.tool

# Inspect the VAULT LiteLLM/API lane only after the canonical subscription surfaces
# show that the problem is on the API side rather than the CLI or handoff plane
python scripts/vault-ssh.py "docker ps --filter name=litellm"
python scripts/vault-ssh.py "docker logs --tail 100 litellm"

# Recovery example only; restart LiteLLM only after provider catalog,
# secret-surface, and truth-inventory reports all agree the fault is runtime-side
python scripts/vault-ssh.py "docker restart litellm"

# Current config reference
cat ansible/roles/vault-litellm/templates/litellm_config.yaml.j2
```

## Model OOM?
- 4090 (24GB): Max ~13GB for weights (AWQ-4bit) + KV cache
- 5090 (32GB): Max ~18GB for weights (AWQ-4bit) + KV cache
- 5060 Ti (16GB): Use Ollama, not vLLM Docker (CUDA driver compat issue)
- TP=4 (64GB): Max ~40GB for weights + KV cache

## Retained Non-Canonical DEV Surfaces
`open-webui` and `athanor-classifier` may still exist on DEV as retained runtime surfaces, but they are not part of the current canonical service map in [SERVICES.md](/C:/Athanor/docs/SERVICES.md).

```bash
# Inspect current status after checking the generated runtime and provider reports
ssh dev "docker ps --format '{{.Names}}\t{{.Status}}' | grep -i webui"
ssh dev "sudo journalctl -u athanor-classifier -n 100 --no-pager"

# Restart only if you are explicitly debugging those retained surfaces
ssh dev "sudo systemctl restart athanor-classifier"
```

## Governor Posture Or Task Dispatch Looks Wrong? (Quick-Reference Only)
```bash
# Check canonical governor posture
ssh foundry "curl -s http://127.0.0.1:9000/v1/governor" | python3 -m json.tool

# Check canonical task stats
ssh foundry "curl -s http://127.0.0.1:9000/v1/tasks/stats" | python3 -m json.tool

# Check canonical provider catalog and summary surfaces
ssh foundry "curl -s http://127.0.0.1:9000/v1/subscriptions/providers" | python3 -m json.tool
ssh foundry "curl -s http://127.0.0.1:9000/v1/subscriptions/summary" | python3 -m json.tool

```

The standalone governor service has been retired and removed from the live DEV runtime.
The live DEV `:8760` listener has already been retired; treat it as rollback-only audit evidence, not a live control-plane dependency.
Do not include `athanor-governor` in the generic primary-service restart path unless you are explicitly performing rollback or auditing the completed cutover.
Do not use it as provider, spend, commit, or tmux-session truth; those legacy routes are retired.
Do not treat the retired governor SQLite snapshot as live task truth; any archived SQLite file is historical-only.
Use `config/automation-backbone/provider-catalog.json` and `docs/operations/PROVIDER-CATALOG-REPORT.md` as provider truth before treating runtime adapter symptoms as routing-policy defects.
If `:8760` ever reappears, use `docs/runbooks/governor-facade-retirement.md` as the rollback or re-cutover guide instead of treating it as part of the default troubleshooting path.

## SSH Aliases
```
ssh dev        # DEV (shaun@192.168.1.189)
ssh foundry    # FOUNDRY (athanor@192.168.1.244)
ssh workshop   # WORKSHOP (athanor@192.168.1.225)
python scripts/vault-ssh.py  # VAULT preferred helper
ssh root@192.168.1.203       # VAULT fallback / recovery only
```
